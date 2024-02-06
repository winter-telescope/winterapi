"""
Module with the base class for generic API interactions
"""

import json
import logging
import re
from pathlib import Path

import backoff
import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MAX_TIMEOUT = 30.0


class BaseAPI:
    """
    Base class for interacting with the API
    """

    def get_auth(self):
        """
        Get the authentication details.

        :return: Authentication details.
        """
        raise NotImplementedError

    @staticmethod
    def clean_data(data):
        """
        Clean the data for the API.

        :param data: Data to clean.
        :return: Cleaned data.
        """

        if isinstance(data, list):
            convert = json.dumps([x.model_dump() for x in data])
        elif isinstance(data, BaseModel):
            convert = json.dumps([data.model_dump()])
        else:
            err = f"Unrecognised data type {type(data)}"
            logger.error(err)
            raise TypeError(err)

        return convert

    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=MAX_TIMEOUT
    )
    def get(self, url, auth=None, data=None, **kwargs) -> requests.Response:
        """
        Run a get request.

        :param url: URL to get.
        :param auth: Authentication details.
        :param data: Data to get.
        :param kwargs: additional arguments for API.
        :return: API response.
        """
        if auth is None:
            auth = self.get_auth()

        if data is not None:
            data = self.clean_data(data)

        res = requests.get(
            url, data=data, auth=auth, params=kwargs, timeout=MAX_TIMEOUT
        )

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

        convert = self.clean_data(data)

        res = requests.post(
            url, data=convert, auth=auth, params=kwargs, timeout=MAX_TIMEOUT
        )

        if res.status_code != 200:
            err = f"API call failed with '{res}: {res.text}'"
            logger.error(err)
            raise ValueError(err)
        return res

    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=MAX_TIMEOUT
    )
    def delete(self, url, auth=None, **kwargs) -> requests.Response:
        """
        Run a delete request.

        :param url: URL to post to.
        :param auth: Authentication details.
        :param kwargs: additional arguments for API.
        :return: Response.
        """
        if auth is None:
            auth = self.get_auth()

        res = requests.delete(url, auth=auth, params=kwargs, timeout=MAX_TIMEOUT)

        if res.status_code != 200:
            err = f"API call failed with '{res}: {res.text}'"
            logger.error(err)
            raise ValueError(err)
        return res

    @backoff.on_exception(
        backoff.expo, requests.exceptions.RequestException, max_time=MAX_TIMEOUT
    )
    def get_stream(
        self, url, output_dir: str | Path | None = None, auth=None, data=None, **kwargs
    ) -> tuple[requests.Response, Path]:
        """
        Run a get request.

        :param url: URL to get.
        :param output_dir: Directory to save the output.
        :param auth: Authentication details.
        :param kwargs: additional arguments for API.
        :return: API response.
        """
        if auth is None:
            auth = self.get_auth()

        if data is not None:
            data = self.clean_data(data)

        if output_dir is None:
            output_dir = Path.home()
            logger.warning(f"No output directory specified, using {output_dir}")

        if not isinstance(output_dir, Path):
            output_dir = Path(output_dir)

        if not output_dir.parent.exists():
            output_dir.parent.mkdir(parents=True)

        fname = "winterapi_output.zip"

        with requests.Session() as session:

            with session.get(
                url,
                data=data,
                auth=auth,
                params=kwargs,
                timeout=MAX_TIMEOUT,
                stream=True,
            ) as resp:
                header = resp.headers

                if "Content-Disposition" in header.keys():
                    fname = re.findall("filename=(.+)", header["Content-Disposition"])[
                        0
                    ]

                output_path = output_dir.joinpath(fname)

                with open(output_path, "wb") as output_f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        output_f.write(chunk)

        logger.info(f"Downloaded file to {output_path}")

        return resp, output_path
