"""
Module for storing the endpoints for the API.
"""

import os

run_local = os.getenv("WINTER_API_LOCAL", "0") in ["True", "true", "1"]
BASE_URL = "http://127.0.0.1:7000" if run_local else "http://winter.caltech.edu:82"
PING_URL = BASE_URL + "/ping"
VERSION_URL = BASE_URL + "/validation/version"
USER_URL = BASE_URL + "/validation/user"
PROGRAM_URL = BASE_URL + "/validation/program"
WINTER_TOO_URL = BASE_URL + "/too/winter"
SUMMER_TOO_URL = BASE_URL + "/too/summer"
SCHEDULE_SUMMARY_URL = BASE_URL + "/too/summary"
SCHEDULE_DETAILS_URL = BASE_URL + "/too/details"
SCHEDULE_DELETE_URL = BASE_URL + "/too/delete"
IMAGE_QUERY_URL = BASE_URL + "/images/query"
DOWNLOAD_LIST_URL = BASE_URL + "/images/download_list"
