"""Compatibility re-export; prefer ``desktop_backend.tasks.calibration.worker``."""

from .calibration.worker import CalibrationTaskWorker

__all__ = ["CalibrationTaskWorker"]
