"""Tests for WorkerSettings attribute handling and app=None edge cases."""
import pytest
from unittest.mock import patch, MagicMock


# ── WorkerSettings defaults ───────────────────────────────────────────────────

def test_default_worker_settings_has_none_app():
    from tarsq.worker import WorkerSettings
    ws = WorkerSettings()
    assert ws.app is None


def test_default_worker_settings_has_five_workers():
    from tarsq.worker import WorkerSettings
    ws = WorkerSettings()
    assert ws.workers == 5


def test_default_worker_settings_has_no_on_startup():
    from tarsq.worker import WorkerSettings
    ws = WorkerSettings()
    assert ws.on_startup is None


def test_default_worker_settings_has_no_on_shutdown():
    from tarsq.worker import WorkerSettings
    ws = WorkerSettings()
    assert ws.on_shutdown is None


def test_default_worker_settings_has_empty_ctx():
    from tarsq.worker import WorkerSettings
    ws = WorkerSettings()
    assert ws.ctx == {}


# ── User-defined WorkerSettings without inheriting tarsq's ───────────────────

def test_user_settings_without_app_still_works_via_getattr():
    """getattr(ws, 'app', None) must return None for plain class with no app attr."""
    class UserSettings:
        workers = 3

    ws = UserSettings()
    app = getattr(ws, "app", None)
    assert app is None


def test_user_settings_with_app_returns_correct_value():
    class UserSettings:
        app = "myapp.tasks"

    ws = UserSettings()
    app = getattr(ws, "app", None)
    assert app == "myapp.tasks"


def test_user_settings_missing_workers_falls_back_to_default():
    class UserSettings:
        app = "myapp.tasks"

    ws = UserSettings()
    workers = getattr(ws, "workers", 5)
    assert workers == 5


def test_user_settings_missing_on_startup_falls_back_to_none():
    class UserSettings:
        app = "myapp.tasks"

    ws = UserSettings()
    on_startup = getattr(ws, "on_startup", None)
    assert on_startup is None


# ── worker() handles app=None without crashing ───────────────────────────────

def test_worker_skips_import_when_app_is_none():
    """worker() must not call importlib.import_module(None) when app is None."""
    from tarsq.worker import worker

    shutdown_event = MagicMock()
    shutdown_event.is_set.return_value = True  # exit immediately

    with patch("tarsq.worker.importlib.import_module") as mock_import:
        with patch("tarsq.worker.redis.Redis"):
            worker(0, None, shutdown_event)
            # None should never be passed to import_module
            called_args = [c.args[0] for c in mock_import.call_args_list]
            assert None not in called_args


def test_worker_imports_app_when_provided():
    """worker() must call importlib.import_module with the given app."""
    from tarsq.worker import worker

    shutdown_event = MagicMock()
    shutdown_event.is_set.return_value = True  # exit immediately

    with patch("tarsq.worker.importlib.import_module") as mock_import:
        with patch("tarsq.worker.redis.Redis"):
            worker(0, "myapp.tasks", shutdown_event)
            called_args = [c.args[0] for c in mock_import.call_args_list]
            assert "myapp.tasks" in called_args


# ── watch() handles app=None without crashing ────────────────────────────────

def test_watch_skips_import_when_app_is_none():
    from tarsq.worker import watch

    shutdown_event = MagicMock()
    shutdown_event.is_set.return_value = True  # exit immediately

    with patch("tarsq.worker.importlib.import_module") as mock_import:
        watch(None, shutdown_event)
        mock_import.assert_not_called()


def test_watch_imports_app_when_provided():
    from tarsq.worker import watch

    shutdown_event = MagicMock()
    shutdown_event.is_set.return_value = True

    with patch("tarsq.worker.importlib.import_module") as mock_import:
        watch("myapp.tasks", shutdown_event)
        mock_import.assert_called_once_with("myapp.tasks")
