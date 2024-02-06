"""
Module for testing the API
"""

import logging
import time
import unittest

from winterapi.configure_tests import winter

logger = logging.getLogger(__name__)


class TestAPI(unittest.TestCase):
    """
    Class for testing API
    """

    def test_ping(self):
        """
        Test ping

        :return: None
        """
        logger.info("Testing the ping")
        assert winter.ping(), "Server not reached"
        time.sleep(10)
