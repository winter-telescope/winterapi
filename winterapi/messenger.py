"""
This module contains the messenger, which is used to communicate with the API
"""
import getpass
import json
import logging
from typing import Optional

import backoff
import pandas as pd
import requests
from pydantic import BaseModel
from wintertoo.models import Program
from wintertoo.models.too import (
    AllTooClasses,
    Summer,
    SummerFieldToO,
    SummerRaDecToO,
    Winter,
    WinterFieldToO,
    WinterRaDecToO,
)
from wintertoo.schedule import concat_toos

from winterapi.endpoints import (
    PING_URL,
    PROGRAM_URL,
    SUMMER_TOO_URL,
    USER_URL,
    WINTER_TOO_URL,
)
from winterapi.fidelius import Fidelius

logger = logging.getLogger(__name__)

MAX_TIMEOUT = 30


class WinterAPI:
    """
    Class to communicate with the Winter API
    """

    def __init__(self):
        self.fidelius = Fidelius()
        logger.info(f"API ping success is {self.ping()}")
        self.auth = (None, None)

    @staticmethod
    def clear_cache():
        """
        Clear the cache.

        :return: None
        """
        Fidelius.clear_cache()

    def get_auth(self):
        """
        Get the authentication details.

        :return: user, password
        """
        if self.auth == (None, None):
            self.auth = (self.fidelius.get_user(), self.fidelius.get_password())
        return self.auth

    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=MAX_TIMEOUT
    )
    def get(self, url, auth=None, **kwargs) -> requests.Response:
        """
        Run a get request.

        :param url: URL to get.
        :param auth: Authentication details.
        :param kwargs: additional arguments for API.
        :return: API response.
        """
        if auth is None:
            auth = self.get_auth()
        res = requests.get(url, auth=auth, params=kwargs, timeout=MAX_TIMEOUT)

        if res.status_code != 200:
            err = f"API call failed with '{res}: {res.text}'"
            logger.error(err)
            raise ValueError(err)
        return res

    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=MAX_TIMEOUT
    )
    def post(
        self, url, data: BaseModel | list[BaseModel], auth=None, **kwargs
    ) -> requests.Response:
        """
        Run a post request.

        :param url: URL to post to.
        :param data: Data to post.
        :param auth: Authentication details.
        :param kwargs: additional arguments for API.
        :return: Response.
        """
        if auth is None:
            auth = self.get_auth()

        if isinstance(data, list):
            convert = json.dumps([x.dict() for x in data])
        elif isinstance(data, BaseModel):
            convert = json.dumps(data.dict())
        else:
            err = f"Unrecognised data type {type(data)}"
            logger.error(err)
            raise TypeError(err)

        res = requests.post(
            url, data=convert, auth=auth, params=kwargs, timeout=MAX_TIMEOUT
        )

        if res.status_code != 200:
            err = f"API call failed with '{res}: {res.text}'"
            logger.error(err)
            raise ValueError(err)
        return res

    @staticmethod
    def ping():
        """
        Ping the API.

        :return: boolean for success
        """
        try:
            res = requests.get(PING_URL, timeout=MAX_TIMEOUT)
            res.raise_for_status()
            return res.status_code == 200
        except ConnectionError:
            return False

    def add_user_details(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        overwrite: bool = False,
    ):
        """
        Add user details for the API

        :param user: Username
        :param password: Password
        :param overwrite: bool to overwrite existing details
        :return: None
        """
        if user is None:
            user = input("Enter user: ")
        if password is None:
            password = getpass.getpass(f"Enter password for user {user}: ")

        self.check_user_details(user=user, password=password)

        self.fidelius.set_user(user=user, password=password, overwrite=overwrite)

    def check_user_details(self, user: str, password: str) -> requests.Response:
        """
        Check the user details are correct.

        :param user: Username
        :param password: Password
        :return: API response
        """
        return self.get(url=USER_URL, auth=(user, password))

    def get_user(self) -> str:
        """
        Get the user name

        :return: User name
        """
        return self.fidelius.get_user()

    def add_program(
        self,
        program_name: Optional[str] = None,
        program_api_key: Optional[str] = None,
        overwrite: bool = False,
    ):
        """
        Add a new program for the API

        :param program_name: Name of the program
        :param program_api_key: API key for the program
        :param overwrite: bool to overwrite existing details
        :return: None
        """
        if program_name is None:
            program_name = input("Enter program: ")
        if program_api_key is None:
            program_api_key = getpass.getpass(
                f"Enter password for program {program_name}: "
            )

        res = self.check_program_details(
            program_name=program_name,
            program_api_key=program_api_key,
        )

        program_dict = res.json()["body"]
        program_dict["prog_key"] = program_api_key

        self.fidelius.add_program(program_details=program_dict, overwrite=overwrite)

    def check_program_details(
        self, program_name: str, program_api_key: str
    ) -> requests.Response:
        """
        Check program details are correct.

        :param program_name: Name of the program
        :param program_api_key: Program API key
        :return: API response
        """
        return self.get(
            PROGRAM_URL, program_name=program_name, program_api_key=program_api_key
        )

    def get_programs(self):
        """
        Get all local programs

        :return: List of programs
        """
        return self.fidelius.get_programs()

    def get_program_details(self, program_name: str) -> Program:
        """
        Get the details for a program

        :param program_name: Name of the program
        :return:
        """
        return self.fidelius.get_program_details(program_name=program_name)

    def _submit_too(
        self,
        program_name: str,
        url: str,
        data: list[AllTooClasses],
        submit_trigger: bool = False,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Protected method to submit TOO requests

        :param program_name: Name of the program under which to submit the TOO
        :param url: URL to submit to
        :param data: List of TOO requests
        :param submit_trigger: Boolean whether to really submit the TOO
        :return: API response and TOO schedule
        """
        program = self.get_program_details(program_name=program_name)

        res = self.post(
            url=url,
            data=data,
            program_name=program_name,
            program_api_key=program.prog_key,
            submit_trigger=submit_trigger,
        )

        logger.info(res.json()["msg"])

        schedule = pd.DataFrame(res.json()["body"])

        return res, schedule

    def submit_too(
        self,
        program_name: str,
        data: list[WinterFieldToO | WinterRaDecToO] | WinterFieldToO | WinterRaDecToO,
        submit_trigger: bool = False,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to submit TOO requests for WINTER

        :param program_name: Name of the program under which to submit the TOO
        :param data: List of WINTER TOO requests
        :param submit_trigger: Boolean whether to really submit the TOO
        :return: API response and TOO schedule
        """
        if not isinstance(data, list):
            data = [data]
        for entry in data:
            assert isinstance(entry, Winter)
        return self._submit_too(
            program_name=program_name,
            url=WINTER_TOO_URL,
            data=data,
            submit_trigger=submit_trigger,
        )

    def submit_too_summer(
        self,
        program_name: str,
        data: list[SummerFieldToO | SummerRaDecToO] | SummerFieldToO | SummerRaDecToO,
        submit_trigger: bool = False,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to submit TOO requests for SUMMER

        :param program_name: Name of the program under which to submit the TOO
        :param data: List of SUMMER TOO requests
        :param submit_trigger: boolean whether to really submit the TOO
        :return: API response and TOO schedule
        """
        if not isinstance(data, list):
            data = [data]
        for entry in data:
            assert isinstance(entry, Summer)
        return self._submit_too(
            program_name=program_name,
            url=SUMMER_TOO_URL,
            data=data,
            submit_trigger=submit_trigger,
        )

    def build_schedule_locally(
        self, data: list[AllTooClasses], program_name: str
    ) -> pd.DataFrame:
        """
        Build a ToO Schedule locally

        :param data: List of TOO requests
        :param program_name: Name of the program under which to submit the TOO
        :return: Schedule dataframe
        """
        program = self.get_program_details(program_name=program_name)
        return concat_toos(data, program=program)
