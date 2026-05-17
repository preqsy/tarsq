"""Tests for _normalize_schedule — natural-language and cron-expression parsing.

Phase 1: cron pass-through and invalid input.
Phase 2: all phrase patterns.
Phase 3: end-to-end integration with @schedule decorator.
"""

import pytest

from tarsq.exceptions import InvalidSchedule
from tarsq.scheduling import _normalize_schedule
from tarsq.core.decorator import cron_registry, schedule


# ---------------------------------------------------------------------------
# Phase 1 — cron pass-through
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    [
        "0 9 * * *",
        "*/5 * * * *",
        "0 9 * * 1-5",
        "0 0 1,15 * *",
        "30 6 * * 0",
        "0 0 * * *",
    ],
)
def test_valid_cron_passes_through(expr: str) -> None:
    assert _normalize_schedule(expr) == expr


def test_cron_strips_surrounding_whitespace() -> None:
    assert _normalize_schedule("  0 9 * * *  ") == "0 9 * * *"


# ---------------------------------------------------------------------------
# Phase 1 — invalid input raises InvalidSchedule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_input",
    [
        "every other tuesday",
        "last friday of the month",
        "every day at 25am",
        "every day at 9",
        "every day at 9:75am",
        "every 0 minutes",
        "every 60 minutes",
        "every month on the 32nd",
        "complete garbage",
        "",
        "   ",
    ],
)
def test_invalid_input_raises(bad_input: str) -> None:
    with pytest.raises(InvalidSchedule):
        _normalize_schedule(bad_input)


# ---------------------------------------------------------------------------
# Phase 1 — error message quality
# ---------------------------------------------------------------------------


def test_error_message_names_the_bad_input() -> None:
    with pytest.raises(InvalidSchedule, match="every other tuesday"):
        _normalize_schedule("every other tuesday")


def test_error_message_lists_examples() -> None:
    with pytest.raises(InvalidSchedule, match="every day at 9am"):
        _normalize_schedule("nope")


# ---------------------------------------------------------------------------
# Phase 2 — interval patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every minute", "* * * * *"),
        ("Every Minute", "* * * * *"),
        ("  every minute  ", "* * * * *"),
    ],
)
def test_every_minute(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every 1 minute", "*/1 * * * *"),
        ("every 5 minutes", "*/5 * * * *"),
        ("every 15 minutes", "*/15 * * * *"),
        ("every 30 minutes", "*/30 * * * *"),
        ("every 59 minutes", "*/59 * * * *"),
    ],
)
def test_every_n_minutes(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "every 0 minutes",
        "every 60 minutes",
        "every 100 minutes",
    ],
)
def test_every_n_minutes_out_of_range(bad: str) -> None:
    with pytest.raises(InvalidSchedule):
        _normalize_schedule(bad)


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every hour", "0 * * * *"),
        ("Every Hour", "0 * * * *"),
        ("  every hour  ", "0 * * * *"),
    ],
)
def test_every_hour(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every 1 hour", "0 */1 * * *"),
        ("every 2 hours", "0 */2 * * *"),
        ("every 6 hours", "0 */6 * * *"),
        ("every 12 hours", "0 */12 * * *"),
        ("every 23 hours", "0 */23 * * *"),
    ],
)
def test_every_n_hours(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "every 0 hours",
        "every 24 hours",
        "every 100 hours",
    ],
)
def test_every_n_hours_out_of_range(bad: str) -> None:
    with pytest.raises(InvalidSchedule):
        _normalize_schedule(bad)


# ---------------------------------------------------------------------------
# Phase 2 — daily patterns
# ---------------------------------------------------------------------------


def test_every_day_at_midnight() -> None:
    assert _normalize_schedule("every day at midnight") == "0 0 * * *"


def test_every_day_at_noon() -> None:
    assert _normalize_schedule("every day at noon") == "0 12 * * *"


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every day at 9am", "0 9 * * *"),
        ("every day at 12am", "0 0 * * *"),
        ("every day at 12pm", "0 12 * * *"),
        ("every day at 11pm", "0 23 * * *"),
        ("every day at 1am", "0 1 * * *"),
        ("every day at 1pm", "0 13 * * *"),
    ],
)
def test_every_day_at_hour(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "every day at 0am",
        "every day at 13am",
        "every day at 25am",
    ],
)
def test_every_day_at_hour_invalid(bad: str) -> None:
    with pytest.raises(InvalidSchedule):
        _normalize_schedule(bad)


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every day at 9:30am", "30 9 * * *"),
        ("every day at 9:00am", "0 9 * * *"),
        ("every day at 12:00am", "0 0 * * *"),
        ("every day at 12:00pm", "0 12 * * *"),
        ("every day at 11:59pm", "59 23 * * *"),
    ],
)
def test_every_day_at_hour_minute(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "every day at 9:60am",
        "every day at 9:75am",
        "every day at 13:00am",
    ],
)
def test_every_day_at_hour_minute_invalid(bad: str) -> None:
    with pytest.raises(InvalidSchedule):
        _normalize_schedule(bad)


# ---------------------------------------------------------------------------
# Phase 2 — weekly: named weekdays
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every monday", "0 0 * * 1"),
        ("every tuesday", "0 0 * * 2"),
        ("every wednesday", "0 0 * * 3"),
        ("every thursday", "0 0 * * 4"),
        ("every friday", "0 0 * * 5"),
        ("every saturday", "0 0 * * 6"),
        ("every sunday", "0 0 * * 0"),
    ],
)
def test_every_weekday_name(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every monday at 9am", "0 9 * * 1"),
        ("every friday at 5pm", "0 17 * * 5"),
        ("every sunday at 12pm", "0 12 * * 0"),
    ],
)
def test_every_weekday_name_at_hour(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every monday at 9:30am", "30 9 * * 1"),
        ("every friday at 5:15pm", "15 17 * * 5"),
        ("every sunday at 12:00pm", "0 12 * * 0"),
    ],
)
def test_every_weekday_name_at_hour_minute(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


# ---------------------------------------------------------------------------
# Phase 2 — weekly: groups (weekday / weekend)
# ---------------------------------------------------------------------------


def test_every_weekday() -> None:
    assert _normalize_schedule("every weekday") == "0 0 * * 1-5"


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every weekday at 9am", "0 9 * * 1-5"),
        ("every weekday at 12pm", "0 12 * * 1-5"),
        ("every weekday at 6am", "0 6 * * 1-5"),
    ],
)
def test_every_weekday_at_hour(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every weekday at 9:30am", "30 9 * * 1-5"),
        ("every weekday at 8:00am", "0 8 * * 1-5"),
        ("every weekday at 5:45pm", "45 17 * * 1-5"),
    ],
)
def test_every_weekday_at_hour_minute(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


def test_every_weekend() -> None:
    assert _normalize_schedule("every weekend") == "0 0 * * 0,6"


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every weekend at 10am", "0 10 * * 0,6"),
        ("every weekend at 12pm", "0 12 * * 0,6"),
        ("every weekend at 8am", "0 8 * * 0,6"),
    ],
)
def test_every_weekend_at_hour(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


# ---------------------------------------------------------------------------
# Phase 2 — monthly
# ---------------------------------------------------------------------------


def test_every_month() -> None:
    assert _normalize_schedule("every month") == "0 0 1 * *"


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every month on the 1st", "0 0 1 * *"),
        ("every month on the 2nd", "0 0 2 * *"),
        ("every month on the 15th", "0 0 15 * *"),
        ("every month on the 31st", "0 0 31 * *"),
        # Grammatically wrong suffix — should still work per spec
        ("every month on the 2st", "0 0 2 * *"),
    ],
)
def test_every_month_on_day(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


def test_every_month_on_day_out_of_range() -> None:
    with pytest.raises(InvalidSchedule):
        _normalize_schedule("every month on the 32nd")


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("every month on the 1st at 9am", "0 9 1 * *"),
        ("every month on the 15th at 6pm", "0 18 15 * *"),
        ("every month on the 31st at 12am", "0 0 31 * *"),
    ],
)
def test_every_month_on_day_at_hour(phrase: str, expected: str) -> None:
    assert _normalize_schedule(phrase) == expected


# ---------------------------------------------------------------------------
# Phase 2 — yearly
# ---------------------------------------------------------------------------


def test_every_year() -> None:
    assert _normalize_schedule("every year") == "0 0 1 1 *"


# ---------------------------------------------------------------------------
# Phase 2 — case / whitespace insensitivity
# ---------------------------------------------------------------------------


def test_phrases_are_case_insensitive() -> None:
    assert _normalize_schedule("Every Day At 9am") == "0 9 * * *"


def test_phrases_strip_whitespace() -> None:
    assert _normalize_schedule("  every day at 9am  ") == "0 9 * * *"


# ---------------------------------------------------------------------------
# Phase 3 — end-to-end: @schedule stores the resolved cron expression
# ---------------------------------------------------------------------------


def test_schedule_decorator_resolves_phrase() -> None:
    """@schedule with a natural-language phrase stores the cron string."""

    @schedule("_test_phrase_job", cron="every weekday at 9:30am")
    def _dummy(_ctx):
        pass

    assert cron_registry["_test_phrase_job"]["cron"] == "30 9 * * 1-5"
    assert cron_registry["_test_phrase_job"]["func"] is _dummy


def test_schedule_decorator_accepts_raw_cron() -> None:
    """@schedule with a raw cron expression stores it unchanged."""

    @schedule("_test_raw_cron_job", cron="0 2 * * *")
    def _dummy2(_ctx):
        pass

    assert cron_registry["_test_raw_cron_job"]["cron"] == "0 2 * * *"


def test_schedule_decorator_rejects_invalid_phrase() -> None:
    """@schedule raises InvalidSchedule for unrecognised input at decoration time."""
    with pytest.raises(InvalidSchedule):

        @schedule("_test_bad_job", cron="every other tuesday")
        def _dummy3(_ctx):
            pass


@pytest.mark.parametrize(
    "phrase,expected_cron",
    [
        ("every minute", "* * * * *"),
        ("every hour", "0 * * * *"),
        ("every day at midnight", "0 0 * * *"),
        ("every day at 9am", "0 9 * * *"),
        ("every monday", "0 0 * * 1"),
        ("every weekday", "0 0 * * 1-5"),
        ("every month", "0 0 1 * *"),
        ("every year", "0 0 1 1 *"),
    ],
)
def test_schedule_decorator_phrase_table(phrase: str, expected_cron: str) -> None:
    """Each built-in phrase resolves to the correct cron via @schedule."""
    job_name = f"_test_e2e_{phrase.replace(' ', '_')}"

    @schedule(job_name, cron=phrase)
    def _fn(_ctx):
        pass

    assert cron_registry[job_name]["cron"] == expected_cron
