from croniter import croniter

from tarsq.exceptions import InvalidSchedule

# Example phrases shown in error messages and used for "did you mean" suggestions.
_EXAMPLE_PHRASES = [
    "every minute",
    "every 15 minutes",
    "every hour",
    "every day at midnight",
    "every day at noon",
    "every day at 9am",
    "every day at 9:30am",
    "every weekday",
    "every weekday at 9am",
    "every weekday at 9:30am",
    "every monday",
    "every friday at 5pm",
    "every weekend",
    "every month",
    "every month on the 1st",
    "every year",
]


def _is_valid_cron(expr: str) -> bool:
    try:
        croniter(expr)
        return True
    except (ValueError, KeyError):
        return False


def _closest_phrase(expr: str) -> str | None:
    """Return the closest example phrase by character-level edit distance, or None."""

    def _edit_distance(a: str, b: str) -> int:
        # Simple DP edit distance — O(len(a)*len(b)), phrases are short so this is fine.
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
                prev = temp
        return dp[n]

    best: str | None = None
    best_dist = len(expr) + 1  # anything is closer than this sentinel
    threshold = max(len(expr) // 2, 8)  # only surface a suggestion if reasonably close

    for phrase in _EXAMPLE_PHRASES:
        d = _edit_distance(expr, phrase)
        if d < best_dist:
            best_dist = d
            best = phrase

    return best if best_dist <= threshold else None


def _build_error_message(expr: str) -> str:
    lines = [
        f"'{expr}' is not a recognized schedule.\n",
        "Tarsq accepts either a natural-language phrase or a standard cron expression.",
        "Examples:",
        '    cron="every day at 9am"',
        '    cron="every weekday at 9:30am"',
        '    cron="every monday"',
        '    cron="every 15 minutes"',
        '    cron="0 9 * * 1-5"',
        "",
        "Full phrase list: https://tarsq.dev/docs#schedule",
    ]

    suggestion = _closest_phrase(expr.strip().lower())
    if suggestion:
        lines.insert(1, f"Did you mean: '{suggestion}'?\n")

    return "\n".join(lines)
