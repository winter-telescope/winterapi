"""
This module contains the messenger, which is used to communicate with the API
"""

import getpass
import logging
from importlib import metadata
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from astropy import units as u
from astropy.time import Time
from packaging import version
from wintertoo.data import DEFAULT_IMAGE_TYPE, WinterImageTypes
from wintertoo.models import (
    ConeImageQuery,
    ImagePath,
    Program,
    ProgramImageQuery,
    RectangleImageQuery,
    TargetImageQuery,
)
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
from wintertoo.utils import get_date

from winterapi.base_api import MAX_TIMEOUT, BaseAPI
from winterapi.endpoints import (
    DOWNLOAD_LIST_URL,
    IMAGE_QUERY_URL,
    PING_URL,
    PROGRAM_URL,
    SCHEDULE_DELETE_URL,
    SCHEDULE_DETAILS_URL,
    SCHEDULE_SUMMARY_URL,
    SUMMER_TOO_URL,
    USER_URL,
    VERSION_URL,
    WINTER_TOO_URL,
)
from winterapi.fidelius import Fidelius

logger = logging.getLogger(__name__)


class WinterAPI(BaseAPI):  # pylint: disable=too-many-public-methods
    """
    Class to communicate with the Winter API
    """

    def __init__(self):
        self.fidelius = Fidelius()
        ping = self.ping()
        if not ping:
            logger.warning("Could not successfully ping server")
        logger.info(f"API ping success is {ping}")
        self.auth = (None, None)
        self.check_version()

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
        except requests.exceptions.ConnectionError:
            return False

    @staticmethod
    def check_version():
        """
        Check the version of the API.

        :return: API response
        """
        res = requests.get(VERSION_URL, timeout=MAX_TIMEOUT)
        if res.status_code == 200:
            server_version = version.parse(res.json()["body"])
            local_version = version.parse(metadata.version("winterapi"))
            logger.info(f"Server requires minimum winterapi version: {server_version}")
            logger.info(f"Local winterapi version: {local_version}")
            if server_version > local_version:
                logger.warning(
                    f"Local winterapi version ({local_version}) is out of date! "
                    f"Server requires a minimum of {server_version}. "
                    f"Please update winterapi."
                )
        else:
            logger.warning("Could not check minimum version of winterapi for server")

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
            assert isinstance(entry, Winter), f"Entry {entry} is not a Winter ToO"
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

    def get_observatory_queue(
        self,
        program_name: str,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the observatory queue

        :param program_name: Name of the program under which to check ToOs
        :return: API response and TOO schedule
        """

        program = self.get_program_details(program_name=program_name)

        res = self.get(
            SCHEDULE_SUMMARY_URL,
            program_name=program_name,
            program_api_key=program.prog_key,
        )

        observatory_queue = pd.DataFrame(res.json()["body"])
        return res, observatory_queue

    def get_too_details(
        self,
        program_name: str,
        too_schedule_name: str,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the details of a single queued TOO schedule

        :param program_name: Name of the program under which TOO was submitted
        :param too_schedule_name: Name of the TOO schedule
        :return: API response and TOO schedule
        """

        program = self.get_program_details(program_name=program_name)

        res = self.get(
            SCHEDULE_DETAILS_URL,
            program_name=program_name,
            program_api_key=program.prog_key,
            schedule_name=too_schedule_name,
        )

        too_schedule = pd.DataFrame(res.json()["body"])
        return res, too_schedule

    def delete_too_request(
        self,
        program_name: str,
        too_schedule_name: str,
    ) -> requests.Response:
        """
        Function to delete a queued TOO schedule

        :param program_name: Name of the program under which TOO was submitted
        :param too_schedule_name: Name of the TOO schedule
        :return: API response
        """

        program = self.get_program_details(program_name=program_name)

        res = self.delete(
            SCHEDULE_DELETE_URL,
            program_name=program_name,
            program_api_key=program.prog_key,
            schedule_name=too_schedule_name,
        )

        return res

    def query_images(
        self,
        query: (
            TargetImageQuery | RectangleImageQuery | ConeImageQuery | ProgramImageQuery
        ),
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the observatory queue

        :param query: Query Request
        :return: API response and TOO schedule
        """

        program = self.get_program_details(program_name=query.program_name)

        res = self.get(
            IMAGE_QUERY_URL,
            program_name=query.program_name,
            program_api_key=program.prog_key,
            data=[query],
        )

        image_summary = pd.DataFrame(res.json()["body"])
        return res, image_summary

    @staticmethod
    def check_query_dates(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[str, str]:
        """
        Function to check the dates

        :param start_date: Start date
        :param end_date: End date
        :return: Start and end date, in ISO format
        """
        if start_date is None:
            start_date = get_date(Time.now() - 30.0 * u.day)

        if end_date is None:
            end_date = get_date(Time.now())

        return start_date, end_date

    def query_images_by_program(
        self,
        program_name: str,
        start_date: str | None = None,
        end_date: str | None = None,
        image_type: WinterImageTypes = DEFAULT_IMAGE_TYPE,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the observatory queue

        :param program_name: Name of the program under which to check ToOs
        :param start_date: Start date for images
        :param end_date: End date for images
        :param image_type: Type of image to query
        :return: API response and TOO schedule
        """

        start_date, end_date = self.check_query_dates(
            start_date=start_date, end_date=end_date
        )

        print(
            f"Querying images for {program_name} between "
            f"{start_date} and {end_date} of type '{image_type}'"
        )

        query = ProgramImageQuery(
            program_name=program_name,
            start_date=start_date,
            end_date=end_date,
            kind=image_type,
        )

        return self.query_images(query=query)

    def query_images_by_target_name(  # pylint: disable=too-many-arguments
        self,
        program_name: str,
        target_name: str | None,
        start_date: str | None = None,
        end_date: str | None = None,
        image_type: WinterImageTypes = DEFAULT_IMAGE_TYPE,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the observatory queue

        :param program_name: Name of the program under which to check ToOs
        :param target_name: Name of the target
        :param start_date: Start date for images
        :param end_date: End date for images
        :param image_type: Type of image to query
        :return: API response and TOO schedule
        """

        start_date, end_date = self.check_query_dates(
            start_date=start_date, end_date=end_date
        )

        print(
            f"Querying images for {program_name} between "
            f"{start_date} and {end_date} of type '{image_type}', "
            f"with name {target_name}"
        )

        query = TargetImageQuery(
            program_name=program_name,
            target_name=target_name,
            start_date=start_date,
            end_date=end_date,
            kind=image_type,
        )

        return self.query_images(query=query)

    def query_images_by_cone(  # pylint: disable=too-many-arguments
        self,
        program_name: str,
        ra_deg: float,
        dec_deg: float,
        radius_deg: float = 1.0,
        start_date: str | None = None,
        end_date: str | None = None,
        image_type: WinterImageTypes = DEFAULT_IMAGE_TYPE,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the observatory queue

        :param program_name: Name of the program under which to check ToOs
        :param ra_deg: Right Ascension in degrees
        :param dec_deg: Declination in degrees
        :param radius_deg: Radius in degrees
        :param start_date: Start date for images
        :param end_date: End date for images
        :param image_type: Type of image to query
        :return: API response and TOO schedule
        """

        start_date, end_date = self.check_query_dates(
            start_date=start_date, end_date=end_date
        )

        print(
            f"Querying images for {program_name} between "
            f"{start_date} and {end_date} of type '{image_type}', "
            f"with a radius of {radius_deg} degrees around {ra_deg}, {dec_deg}"
        )

        query = ConeImageQuery(
            program_name=program_name,
            ra=ra_deg,
            dec=dec_deg,
            radius_deg=radius_deg,
            start_date=start_date,
            end_date=end_date,
            kind=image_type,
        )

        return self.query_images(query=query)

    def query_images_by_rectangle(  # pylint: disable=too-many-arguments
        self,
        program_name: str,
        ra_min_deg: float,
        ra_max_deg: float,
        dec_min_deg: float,
        dec_max_deg: float,
        start_date: str | None = None,
        end_date: str | None = None,
        image_type: WinterImageTypes = DEFAULT_IMAGE_TYPE,
    ) -> tuple[requests.Response, pd.DataFrame]:
        """
        Function to get the observatory queue

        :param program_name: Name of the program under which to check ToOs
        :param ra_min_deg: Minimum Right Ascension in degrees
        :param ra_max_deg: Maximum Right Ascension in degrees
        :param dec_min_deg: Minimum Declination in degrees
        :param dec_max_deg: Maximum Declination in degrees
        :param start_date: Start date for images
        :param end_date: End date for images
        :param image_type: Type of image to query
        :return: API response and TOO schedule
        """

        start_date, end_date = self.check_query_dates(
            start_date=start_date, end_date=end_date
        )

        print(
            f"Querying images for {program_name} between "
            f"{start_date} and {end_date} of type '{image_type}', "
            f"with RA between {ra_min_deg} and {ra_max_deg} and "
            f"Dec between {dec_min_deg} and {dec_max_deg}"
        )

        query = RectangleImageQuery(
            program_name=program_name,
            ra_min=ra_min_deg,
            ra_max=ra_max_deg,
            dec_min=dec_min_deg,
            dec_max=dec_max_deg,
            start_date=start_date,
            end_date=end_date,
            kind=image_type,
        )

        return self.query_images(query=query)

    def download_image_list(
        self,
        program_name: str,
        paths: list[str] | str,
        image_type: WinterImageTypes,
        output_dir: str | None | Path = None,
    ) -> tuple[requests.Response, Path]:
        """
        Download images as a zip file.

        :param program_name: Name of the program under which to check ToOs
        :param image_type: Type of image to query
        :param output_dir: Directory to save the zip to
        :param paths: List of paths to download
        :return: API response
        """

        if not isinstance(paths, list):
            paths = [paths]

        program = self.get_program_details(program_name=program_name)

        res, output_path = self.get_stream(
            DOWNLOAD_LIST_URL,
            savepath=output_dir,
            program_name=program_name,
            program_api_key=program.prog_key,
            data=[ImagePath(path=x) for x in paths],
            kind=image_type,
        )

        return res, output_path
