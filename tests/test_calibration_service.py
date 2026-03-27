import unittest
from unittest import mock

from services.calibration_flow import run_calibration_test_flow


class CalibrationServiceSplitTests(unittest.TestCase):
    def test_run_calibration_test_flow_requires_pause_and_confirm(self):
        with self.assertRaises(ValueError):
            run_calibration_test_flow(
                mode="desktop",
                move_to=lambda *_args: None,
                click=lambda *_args, **_kwargs: None,
                scroll=lambda *_args: None,
                pause=None,
                confirm=None,
            )
