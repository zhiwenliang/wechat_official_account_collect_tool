import unittest

import services.calibration_config as calibration_config
import services.calibration_service as calibration_service
from services.calibration_flow import run_calibration_test_flow


class CalibrationServiceSplitTests(unittest.TestCase):
    def test_resolve_runtime_path_reexported_via_config_facade(self) -> None:
        self.assertIs(
            calibration_service.resolve_runtime_path,
            calibration_config.resolve_runtime_path,
        )

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
