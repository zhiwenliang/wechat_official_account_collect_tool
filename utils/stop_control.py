"""
Stop-aware polling helpers shared by interactive workflows.
"""
import time


def should_stop(stop_checker) -> bool:
    """Return whether a stop callback has been triggered."""
    return bool(stop_checker and stop_checker())


def sleep_with_stop(stop_checker, duration: float) -> bool:
    """Sleep in short intervals until duration elapses or stop is requested."""
    deadline = time.time() + duration

    while time.time() < deadline:
        if should_stop(stop_checker):
            return False
        time.sleep(max(0, min(0.1, deadline - time.time())))

    return not should_stop(stop_checker)
