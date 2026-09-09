"""
Test for image queries and downloads
"""

import logging
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from configure_tests import IMAGE_TEST_PROGRAM_NAME, pause_for_rate_limit, winter

logger = logging.getLogger(__name__)

IMAGE_TYPE = "stack"

# IMAGE_TEST_PROGRAM_NAME (2023A002) is expired, so its set of images on the
# server will never change. This lets us assert exact expected counts.
EXPECTED_IMAGE_COUNTS = {
    "exposure": 241,
    "raw": 2339,
    "science": 1198,
    "stack": 174,
    "diff": 49,
    "avro": 44,
}

# The only stack image tagged with a target name, used to test target name,
# cone, and rectangle queries.
TARGET_NAME = "SN2023ixf"
TARGET_RA_DEG = 210.94190
TARGET_DEC_DEG = 54.262352


class TestImages(unittest.TestCase):
    """
    Class for testing image query/download endpoints

    Uses IMAGE_TEST_PROGRAM_NAME (an expired program with a stable set of
    real images on the server), rather than the general TEST_PROGRAM_NAME
    used for schedule tests, which has no images associated with it.
    """

    def test_query_images_by_program(self):
        """
        Test querying images for the test program, for every image type

        :return: None
        """
        for image_type, expected_count in EXPECTED_IMAGE_COUNTS.items():
            with self.subTest(image_type=image_type):
                logger.info(f"Testing image query by program for type '{image_type}'")

                res, images = winter.query_images_by_program(
                    IMAGE_TEST_PROGRAM_NAME,
                    image_type=image_type,
                    start_date="20200101",
                )

                assert res.status_code == 200, "API call failed"
                assert isinstance(
                    images, pd.DataFrame
                ), "Expected a DataFrame of images"
                assert len(images) == expected_count, (
                    f"Expected {expected_count} '{image_type}' images for program "
                    f"{IMAGE_TEST_PROGRAM_NAME}, found {len(images)}"
                )

                pause_for_rate_limit()

    def test_query_images_by_target_name(self):
        """
        Test querying images by target name

        :return: None
        """
        logger.info("Testing image query by target name")

        res, images = winter.query_images_by_target_name(
            IMAGE_TEST_PROGRAM_NAME,
            target_name=TARGET_NAME,
            image_type=IMAGE_TYPE,
            start_date="20200101",
        )

        assert res.status_code == 200, "API call failed"
        assert (
            len(images) == 1
        ), f"Expected 1 image for target {TARGET_NAME}, found {len(images)}"

        pause_for_rate_limit()

    def test_query_images_by_cone(self):
        """
        Test querying images by cone search

        :return: None
        """
        logger.info("Testing image query by cone")

        res, images = winter.query_images_by_cone(
            IMAGE_TEST_PROGRAM_NAME,
            ra_deg=TARGET_RA_DEG,
            dec_deg=TARGET_DEC_DEG,
            radius_deg=0.05,
            image_type=IMAGE_TYPE,
            start_date="20200101",
        )

        assert res.status_code == 200, "API call failed"
        assert len(images) == 1, f"Expected 1 image in cone, found {len(images)}"

        pause_for_rate_limit()

    def test_query_images_by_rectangle(self):
        """
        Test querying images by rectangle search

        :return: None
        """
        logger.info("Testing image query by rectangle")

        res, images = winter.query_images_by_rectangle(
            IMAGE_TEST_PROGRAM_NAME,
            ra_min_deg=210.9,
            ra_max_deg=211.0,
            dec_min_deg=54.2,
            dec_max_deg=54.3,
            image_type=IMAGE_TYPE,
            start_date="20200101",
        )

        assert res.status_code == 200, "API call failed"
        assert len(images) == 1, f"Expected 1 image in rectangle, found {len(images)}"

        pause_for_rate_limit()

    def test_query_and_download_image(self):
        """
        Test querying images for the test program, then downloading one of them

        :return: None
        """
        logger.info("Testing image query and download")

        res, images = winter.query_images_by_program(
            IMAGE_TEST_PROGRAM_NAME,
            image_type=IMAGE_TYPE,
            start_date="20200101",
        )

        assert res.status_code == 200, "API call failed"
        assert len(images) == EXPECTED_IMAGE_COUNTS[IMAGE_TYPE], (
            f"Expected {EXPECTED_IMAGE_COUNTS[IMAGE_TYPE]} images for program "
            f"{IMAGE_TEST_PROGRAM_NAME}, found {len(images)}"
        )

        pause_for_rate_limit()

        savepath = images["savepath"].iloc[0]

        with tempfile.TemporaryDirectory() as tmp_dir:
            download_res, output_path = winter.download_image_list(
                IMAGE_TEST_PROGRAM_NAME,
                image_type=IMAGE_TYPE,
                paths=[savepath],
                output_dir=tmp_dir,
            )

            assert download_res.status_code == 200, "Download failed"

            output_path = Path(output_path)
            assert output_path.exists(), "Downloaded file does not exist"
            assert output_path.stat().st_size > 0, "Downloaded file is empty"

        pause_for_rate_limit()

    def test_query_images_by_program_spring(self):
        """
        Test querying SPRING images for the test program

        The test program predates the SPRING instrument, so it should have
        no SPRING images, only the WINTER ones checked in
        test_query_images_by_program.

        :return: None
        """
        logger.info("Testing SPRING image query by program")

        res, images = winter.query_images_by_program(
            IMAGE_TEST_PROGRAM_NAME,
            image_type=IMAGE_TYPE,
            instrument="spring",
            start_date="20200101",
        )

        assert res.status_code == 200, "API call failed"
        assert len(images) == 0, f"Expected zero SPRING images, found {len(images)}"

        pause_for_rate_limit()
