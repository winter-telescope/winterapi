"""
This script is used to configure the environment variables for the tests.
"""

import os
import time

from dotenv import load_dotenv

from winterapi import WinterAPI

load_dotenv()

winter = WinterAPI()


try:
    print(f"User is {winter.get_user()}")
except KeyError:
    print("No user credentials found. Please add these first!")
    winter.add_user_details(
        user=os.getenv("WINTER_API_USER"),
        password=os.getenv("WINTER_API_PASSWORD"),
        overwrite=True,
    )

TEST_PROGRAM_NAME = os.getenv("WINTER_API_PROGRAM")

winter.add_program(
    program_name=TEST_PROGRAM_NAME,
    program_api_key=os.getenv("WINTER_API_KEY"),
    overwrite=True,
)

# A fixed, expired program with a stable set of real images on the server,
# used for testing image queries/downloads. Locally, this can instead be
# configured once with `winter.add_program()` and stored in the keyring.
IMAGE_TEST_PROGRAM_NAME = "2023A002"

_image_program_key = os.getenv("WINTER_API_IMAGE_KEY")
if _image_program_key is not None:
    winter.add_program(
        program_name=IMAGE_TEST_PROGRAM_NAME,
        program_api_key=_image_program_key,
        overwrite=True,
    )

# CI runs this suite across CI_PARALLEL_JOBS parallel matrix jobs (see
# .github/workflows/continuous_integration.yml), all hitting the same
# production server at once. Every test that makes an API call should pause
# afterward, to keep the combined request rate from all jobs low enough to
# avoid tripping server-side rate limits/timeouts.
CI_PARALLEL_JOBS = 2
API_CALL_PAUSE_SECONDS = 2 * CI_PARALLEL_JOBS


def pause_for_rate_limit():
    """
    Pause after a test API call, to avoid tripping server-side rate limits
    given CI_PARALLEL_JOBS concurrent CI jobs hitting the server at once.

    :return: None
    """
    time.sleep(API_CALL_PAUSE_SECONDS)
