"""
Test for schedule
"""

import logging
import os
import unittest

import pandas as pd
from wintertoo.fields import get_best_field
from wintertoo.models import WinterFieldToO, WinterRaDecToO

from winterapi.configure_tests import TEST_PROGRAM_NAME, winter

logger = logging.getLogger(__name__)

test_data_dir = os.path.join(os.path.dirname(__file__), "testdata")
test_schedule_path = os.path.join(test_data_dir, "test_schedule.csv")
test_df = pd.read_csv(test_schedule_path)


class TestSchedule(unittest.TestCase):
    """
    Class for testing API
    """

    def test_ra_dec(self):
        """
        Test ra/dec

        :return: None
        """
        logger.info("Testing the ra dec")

        ra_deg = 210.910674637
        dec_deg = 54.3116510708

        winter_field = get_best_field(ra_deg, dec_deg)
        assert int(winter_field["ID"]) == 3944, "Wrong field"

        too_field = WinterFieldToO(
            field_id=winter_field["ID"],
            n_dither=9,
            start_time_mjd=62721.1894969287,
            end_time_mjd=62722.1894969452,
            target_name="test_field",
        )

        too_radec = WinterRaDecToO(
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            start_time_mjd=62721.1894969287,
            end_time_mjd=62722.1894969452,
            use_field_grid=False,
            target_name="test_radec",
        )

        too_list = [too_field, too_radec]

        local_schedule = winter.build_schedule_locally(
            program_name=TEST_PROGRAM_NAME, data=too_list
        )

        # Uncomment to update the schedule
        # local_schedule.to_csv(test_schedule_path, index=False)

        pd.testing.assert_frame_equal(test_df, local_schedule, check_like=True)

        api_res, api_schedule = winter.submit_too(
            program_name=TEST_PROGRAM_NAME, data=too_list, submit_trigger=False
        )

        assert api_res.status_code == 200, "API call failed"

        api_schedule.reset_index(inplace=True)
        api_schedule.drop(columns=["index"], inplace=True)

        pd.testing.assert_frame_equal(
            api_schedule,
            local_schedule,
            check_like=True,
            check_dtype=False,
            check_column_type=False,
            check_index_type=False,
        )
