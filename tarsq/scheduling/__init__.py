"""tarsq.scheduling — natural-language and cron schedule normalisation."""

from tarsq.scheduling.phrases import PATTERNS
from tarsq.scheduling.validation import _build_error_message, _is_valid_cron

from tarsq.exceptions import InvalidSchedule


def _normalize_schedule(expr: str) -> str:
    """Convert a phrase or cron expression to a validated cron string.

    Tries each pattern in PATTERNS in order.  If a pattern matches its handler
    is called and the resulting cron string is returned immediately.

    If no pattern matches the input is tested as a raw cron expression via
    croniter.  Valid cron expressions are returned unchanged.

    Raises:
        InvalidSchedule: If the input is neither a recognised phrase nor a
            valid cron expression.
    """
    normalized = expr.strip().lower()

    for pattern, handler in PATTERNS:
        m = pattern.match(normalized)
        if m:
            return handler(m)

    # Not a phrase — try as a raw cron expression (preserve original spacing/case).
    if _is_valid_cron(expr.strip()):
        return expr.strip()

    raise InvalidSchedule(_build_error_message(expr))


__all__ = ["_normalize_schedule", "InvalidSchedule"]
