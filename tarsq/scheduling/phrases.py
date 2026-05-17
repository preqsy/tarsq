"""Natural-language schedule phrases and their cron-expression handlers.

Each entry in PATTERNS is a (compiled_regex, handler) pair.
The handler receives a re.Match and returns a validated 5-field cron string,
or raises InvalidSchedule if captured values are out of range.

Patterns are tried in order; the first match wins.
"""

import re
from typing import Callable

from tarsq.exceptions import InvalidSchedule

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOW_MAP = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}

_WEEKDAY_PATTERN = "|".join(_DOW_MAP)  # monday|tuesday|...


def _to_hour24(hour: int, meridiem: str) -> int:
    """Convert 12-hour clock + am/pm to 24-hour integer.

    Raises InvalidSchedule if hour is outside 1-12.
    """
    if not (1 <= hour <= 12):
        raise InvalidSchedule(
            f"Hour {hour} is out of range for 12-hour clock (must be 1-12)."
        )
    if meridiem == "am":
        return 0 if hour == 12 else hour
    else:  # pm
        return 12 if hour == 12 else hour + 12


def _validate_minute(minute: int) -> None:
    if not (0 <= minute <= 59):
        raise InvalidSchedule(
            f"Minute {minute} is out of range (must be 0-59)."
        )


def _validate_day(day: int) -> None:
    if not (1 <= day <= 31):
        raise InvalidSchedule(
            f"Day {day} is out of range (must be 1-31)."
        )


# ---------------------------------------------------------------------------
# Handlers — intervals
# ---------------------------------------------------------------------------

def _h_every_minute(_m: re.Match) -> str:  # every minute
    return "* * * * *"


def _h_every_n_minutes(m: re.Match) -> str:  # every (\d+) minutes?
    n = int(m.group(1))
    if not (1 <= n <= 59):
        raise InvalidSchedule(
            f"Interval {n} is out of range for 'every N minutes' (must be 1-59)."
        )
    return f"*/{n} * * * *"


def _h_every_hour(_m: re.Match) -> str:  # every hour
    return "0 * * * *"


def _h_every_n_hours(m: re.Match) -> str:  # every (\d+) hours?
    n = int(m.group(1))
    if not (1 <= n <= 23):
        raise InvalidSchedule(
            f"Interval {n} is out of range for 'every N hours' (must be 1-23)."
        )
    return f"0 */{n} * * *"


# ---------------------------------------------------------------------------
# Handlers — daily
# ---------------------------------------------------------------------------

def _h_every_day_midnight(_m: re.Match) -> str:  # every day at midnight
    return "0 0 * * *"


def _h_every_day_noon(_m: re.Match) -> str:  # every day at noon
    return "0 12 * * *"


def _h_every_day_at_hour(m: re.Match) -> str:  # every day at (\d{1,2})(am|pm)
    hour24 = _to_hour24(int(m.group(1)), m.group(2))
    return f"0 {hour24} * * *"


def _h_every_day_at_hour_minute(m: re.Match) -> str:  # every day at (\d{1,2}):(\d{2})\s?(am|pm)
    hour24 = _to_hour24(int(m.group(1)), m.group(3))
    minute = int(m.group(2))
    _validate_minute(minute)
    return f"{minute} {hour24} * * *"


# ---------------------------------------------------------------------------
# Handlers — weekly (single weekday)
# ---------------------------------------------------------------------------

def _h_every_weekday_name(m: re.Match) -> str:  # every (monday|...|sunday)
    dow = _DOW_MAP[m.group(1)]
    return f"0 0 * * {dow}"


def _h_every_weekday_name_at_hour(m: re.Match) -> str:  # every <day> at (\d{1,2})(am|pm)
    dow = _DOW_MAP[m.group(1)]
    hour24 = _to_hour24(int(m.group(2)), m.group(3))
    return f"0 {hour24} * * {dow}"


def _h_every_weekday_name_at_hour_minute(m: re.Match) -> str:  # every <day> at (\d{1,2}):(\d{2})\s?(am|pm)
    dow = _DOW_MAP[m.group(1)]
    hour24 = _to_hour24(int(m.group(2)), m.group(4))
    minute = int(m.group(3))
    _validate_minute(minute)
    return f"{minute} {hour24} * * {dow}"


# ---------------------------------------------------------------------------
# Handlers — weekly (groups)
# ---------------------------------------------------------------------------

def _h_every_weekday(_m: re.Match) -> str:  # every weekday
    return "0 0 * * 1-5"


def _h_every_weekday_at_hour(m: re.Match) -> str:  # every weekday at (\d{1,2})(am|pm)
    hour24 = _to_hour24(int(m.group(1)), m.group(2))
    return f"0 {hour24} * * 1-5"


def _h_every_weekday_at_hour_minute(m: re.Match) -> str:  # every weekday at (\d{1,2}):(\d{2})\s?(am|pm)
    hour24 = _to_hour24(int(m.group(1)), m.group(3))
    minute = int(m.group(2))
    _validate_minute(minute)
    return f"{minute} {hour24} * * 1-5"


def _h_every_weekend(_m: re.Match) -> str:  # every weekend
    return "0 0 * * 0,6"


def _h_every_weekend_at_hour(m: re.Match) -> str:  # every weekend at (\d{1,2})(am|pm)
    hour24 = _to_hour24(int(m.group(1)), m.group(2))
    return f"0 {hour24} * * 0,6"


# ---------------------------------------------------------------------------
# Handlers — monthly
# ---------------------------------------------------------------------------

def _h_every_month(_m: re.Match) -> str:  # every month
    return "0 0 1 * *"


def _h_every_month_on_day(m: re.Match) -> str:  # every month on the (\d{1,2})(st|nd|rd|th)
    day = int(m.group(1))
    _validate_day(day)
    return f"0 0 {day} * *"


def _h_every_month_on_day_at_hour(m: re.Match) -> str:  # every month on the (\d{1,2})(st|nd|rd|th) at (\d{1,2})(am|pm)
    day = int(m.group(1))
    _validate_day(day)
    hour24 = _to_hour24(int(m.group(3)), m.group(4))
    return f"0 {hour24} {day} * *"


# ---------------------------------------------------------------------------
# Handlers — yearly
# ---------------------------------------------------------------------------

def _h_every_year(_m: re.Match) -> str:  # every year
    return "0 0 1 1 *"


# ---------------------------------------------------------------------------
# Pattern table — order matters; first match wins
# ---------------------------------------------------------------------------

PATTERNS: list[tuple[re.Pattern, Callable[[re.Match], str]]] = [
    # --- intervals ---
    # "every minute"
    (re.compile(r"^every minute$"), _h_every_minute),
    # "every 5 minutes" / "every 1 minute"
    (re.compile(r"^every (\d+) minutes?$"), _h_every_n_minutes),
    # "every hour"
    (re.compile(r"^every hour$"), _h_every_hour),
    # "every 2 hours" / "every 12 hours"
    (re.compile(r"^every (\d+) hours?$"), _h_every_n_hours),

    # --- daily (specific literals first to avoid shadowing by generic patterns) ---
    # "every day at midnight"
    (re.compile(r"^every day at midnight$"), _h_every_day_midnight),
    # "every day at noon"
    (re.compile(r"^every day at noon$"), _h_every_day_noon),
    # "every day at 9:30am"
    (re.compile(r"^every day at (\d{1,2}):(\d{2})\s?(am|pm)$"), _h_every_day_at_hour_minute),
    # "every day at 9am"
    (re.compile(r"^every day at (\d{1,2})(am|pm)$"), _h_every_day_at_hour),

    # --- weekly: named weekday with time (must come before plain weekday) ---
    # "every monday at 9:30am"
    (
        re.compile(rf"^every ({_WEEKDAY_PATTERN}) at (\d{{1,2}}):(\d{{2}})\s?(am|pm)$"),
        _h_every_weekday_name_at_hour_minute,
    ),
    # "every monday at 9am"
    (
        re.compile(rf"^every ({_WEEKDAY_PATTERN}) at (\d{{1,2}})(am|pm)$"),
        _h_every_weekday_name_at_hour,
    ),
    # "every monday"
    (re.compile(rf"^every ({_WEEKDAY_PATTERN})$"), _h_every_weekday_name),

    # --- weekly: weekday/weekend groups (literals before generic) ---
    # "every weekday at 9:30am"
    (re.compile(r"^every weekday at (\d{1,2}):(\d{2})\s?(am|pm)$"), _h_every_weekday_at_hour_minute),
    # "every weekday at 9am"
    (re.compile(r"^every weekday at (\d{1,2})(am|pm)$"), _h_every_weekday_at_hour),
    # "every weekday"
    (re.compile(r"^every weekday$"), _h_every_weekday),
    # "every weekend at 9am"
    (re.compile(r"^every weekend at (\d{1,2})(am|pm)$"), _h_every_weekend_at_hour),
    # "every weekend"
    (re.compile(r"^every weekend$"), _h_every_weekend),

    # --- monthly ---
    # "every month on the 15th at 9am"
    (
        re.compile(r"^every month on the (\d{1,2})(st|nd|rd|th) at (\d{1,2})(am|pm)$"),
        _h_every_month_on_day_at_hour,
    ),
    # "every month on the 1st"
    (re.compile(r"^every month on the (\d{1,2})(st|nd|rd|th)$"), _h_every_month_on_day),
    # "every month"
    (re.compile(r"^every month$"), _h_every_month),

    # --- yearly ---
    # "every year"
    (re.compile(r"^every year$"), _h_every_year),
]
