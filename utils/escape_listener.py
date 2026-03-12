"""
Esc key listener utilities for CLI tasks.
"""
import select
import sys
import threading
import time


class EscapeListener:
    """Listen for the Esc key in a background thread."""

    def __init__(self, on_escape=None, poll_interval=0.1):
        self.on_escape = on_escape
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._triggered = threading.Event()
        self._thread = None
        self._enabled = False

    def start(self):
        """Start listening in the background when stdin is interactive."""
        if self._thread is not None or not sys.stdin.isatty():
            return False

        self._enabled = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop listening and wait briefly for the watcher thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)

    def is_triggered(self):
        """Return whether Esc has been pressed."""
        return self._triggered.is_set()

    def _fire(self):
        if self._triggered.is_set():
            return

        self._triggered.set()
        if callable(self.on_escape):
            self.on_escape()

    def _listen(self):
        if sys.platform == "win32":
            self._listen_windows()
        else:
            self._listen_posix()

    def _listen_windows(self):
        import msvcrt

        while not self._stop_event.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key == "\x1b":
                    self._fire()
                    return
            time.sleep(self.poll_interval)

    def _listen_posix(self):
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setcbreak(fd)

            while not self._stop_event.is_set():
                readable, _, _ = select.select([fd], [], [], self.poll_interval)
                if fd in readable:
                    key = sys.stdin.read(1)
                    if key == "\x1b":
                        self._fire()
                        return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
