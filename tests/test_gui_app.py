import queue
import unittest
from unittest.mock import patch

from gui.app import WeChatScraperGUI


class FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.destroyed = False

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return len(self.after_calls)

    def destroy(self):
        self.destroyed = True


class FakeWorker:
    def __init__(self, alive=False, signals=None):
        self._alive = alive
        self.signals = signals or type("Signals", (), {"queue": queue.Queue(), "get": lambda self, timeout=0.1: None})()

    def is_alive(self):
        return self._alive


class GuiAppTests(unittest.TestCase):
    def test_worker_error_clears_current_worker_and_resets_controls(self):
        app = WeChatScraperGUI.__new__(WeChatScraperGUI)
        app.current_worker = FakeWorker()
        app.worker_timer = None
        app.is_stopping = False
        app.close_requested = False
        app.root = FakeRoot()
        app._reset_start_buttons = lambda: setattr(app, "reset_called", True)
        app._set_calibration_buttons_state = lambda _value: None
        app._update_statistics = lambda: setattr(app, "stats_updated", True)
        app.worker_status_label = type("Label", (), {"config": lambda self, **kwargs: setattr(app, "status_text", kwargs["text"])})()

        with patch("gui.app.messagebox.showerror") as showerror:
            app._handle_worker_error("boom")

        showerror.assert_called_once()
        self.assertIsNone(app.current_worker)
        self.assertTrue(app.reset_called)
        self.assertEqual(app.status_text, "错误")

    def test_check_worker_signals_continues_polling_until_queue_drained(self):
        app = WeChatScraperGUI.__new__(WeChatScraperGUI)
        app.root = FakeRoot()
        app.worker_timer = None
        app.is_stopping = False
        app.collect_log = type("Log", (), {"insert": lambda self, *_args, **_kwargs: None, "see": lambda self, *_args, **_kwargs: None})()
        app.scrape_log = app.collect_log
        app.collect_progress = {}
        app.scrape_progress = {}
        app.collect_status_label = type("Label", (), {"config": lambda self, **kwargs: None})()
        app.scrape_status_label = type("Label", (), {"config": lambda self, **kwargs: None})()
        app.worker_status_label = type("Label", (), {"config": lambda self, **kwargs: None})()
        app._update_scrape_result_labels = lambda **_kwargs: None
        app._handle_worker_error = lambda _message: None
        app._worker_complete = lambda data: setattr(app, "completed_data", data)

        signals = queue.Queue()
        for index in range(21):
            signals.put(("log", {"message": f"log {index}"}))
        signals.put(("complete", {"count": 1}))

        class SignalAdapter:
            def __init__(self, signal_queue):
                self.queue = signal_queue

            def get(self, timeout=0.1):
                try:
                    return self.queue.get_nowait()
                except queue.Empty:
                    return None

        app.current_worker = FakeWorker(alive=False, signals=SignalAdapter(signals))

        app._check_worker_signals()

        self.assertEqual(len(app.root.after_calls), 1)
        _delay, callback = app.root.after_calls[0]
        callback()
        self.assertEqual(app.completed_data, {"count": 1})
