from datetime import datetime
from unittest.mock import patch, MagicMock
from croniter import croniter


def match(expr: str, dt: datetime) -> bool:
    return croniter.match(expr, dt)


def test_every_minute():
    assert match("* * * * *", datetime(2025, 1, 1, 9, 0))
    assert match("* * * * *", datetime(2025, 1, 1, 9, 37))


def test_every_5_minutes():
    assert match("*/5 * * * *", datetime(2025, 1, 1, 9, 0))
    assert match("*/5 * * * *", datetime(2025, 1, 1, 9, 15))
    assert match("*/5 * * * *", datetime(2025, 1, 1, 9, 55))
    assert not match("*/5 * * * *", datetime(2025, 1, 1, 9, 7))


def test_every_hour():
    assert match("0 * * * *", datetime(2025, 1, 1, 9, 0))
    assert match("0 * * * *", datetime(2025, 1, 1, 14, 0))
    assert not match("0 * * * *", datetime(2025, 1, 1, 9, 1))


def test_every_2_hours():
    assert match("0 */2 * * *", datetime(2025, 1, 1, 0, 0))
    assert match("0 */2 * * *", datetime(2025, 1, 1, 2, 0))
    assert match("0 */2 * * *", datetime(2025, 1, 1, 14, 0))
    assert not match("0 */2 * * *", datetime(2025, 1, 1, 3, 0))
    assert not match("0 */2 * * *", datetime(2025, 1, 1, 14, 1))


def test_every_day_at_midnight():
    assert match("0 0 * * *", datetime(2025, 1, 1, 0, 0))
    assert not match("0 0 * * *", datetime(2025, 1, 1, 0, 1))
    assert not match("0 0 * * *", datetime(2025, 1, 1, 1, 0))


def test_every_day_at_9am():
    assert match("0 9 * * *", datetime(2025, 1, 1, 9, 0))
    assert not match("0 9 * * *", datetime(2025, 1, 1, 9, 1))
    assert not match("0 9 * * *", datetime(2025, 1, 1, 10, 0))


def test_every_monday():
    assert match("0 0 * * 1", datetime(2025, 1, 6, 0, 0))  # Monday
    assert not match("0 0 * * 1", datetime(2025, 1, 7, 0, 0))  # Tuesday
    assert not match("0 0 * * 1", datetime(2025, 1, 5, 0, 0))  # Sunday


def test_scheduler_dispatches_when_due():
    fake_registry = {"send_email": {"func": MagicMock(), "cron": "* * * * *"}}
    due_time = datetime(2025, 1, 1, 9, 0, 0)
    mock_event = MagicMock()
    # False → enter while; True → break sleep loop; True → exit while
    mock_event.is_set.side_effect = [False, True, True]

    with (
        patch("tarsq.cron.cron_registry", fake_registry),
        patch("tarsq.cron.dispatch") as mock_dispatch,
        patch("tarsq.cron.datetime") as mock_dt,
    ):

        mock_dt.now.return_value = due_time

        from tarsq.cron import scheduler

        scheduler(mock_event)

        mock_dispatch.assert_called_once_with("send_email")


def test_scheduler_does_not_dispatch_when_not_due():
    fake_registry = {"send_email": {"func": MagicMock(), "cron": "0 9 * * *"}}
    not_due_time = datetime(2025, 1, 1, 9, 1, 0)
    mock_event = MagicMock()
    mock_event.is_set.side_effect = [False, True, True]

    with (
        patch("tarsq.cron.cron_registry", fake_registry),
        patch("tarsq.cron.dispatch") as mock_dispatch,
        patch("tarsq.cron.datetime") as mock_dt,
    ):

        mock_dt.now.return_value = not_due_time

        from tarsq.cron import scheduler

        scheduler(mock_event)

        mock_dispatch.assert_not_called()
