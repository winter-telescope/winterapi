"""
This script is used to configure the environment variables for the tests.
"""

import os

from winterapi import WinterAPI

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
