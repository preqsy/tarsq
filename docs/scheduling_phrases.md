# Tarsq Scheduling Phrases

The `cron` parameter of `@schedule` accepts either a **natural-language phrase** from the table below or a **standard 5-field cron expression**.

```python
@schedule("report", cron="every weekday at 9am")
@schedule("cleanup", cron="0 2 * * *")
```

Invalid input raises `InvalidSchedule` at decoration time (import time), never silently.

---

## Supported Phrases

### Intervals

| Phrase | Cron | Notes |
|--------|------|-------|
| `every minute` | `* * * * *` | |
| `every N minutes` | `*/N * * * *` | N: 1–59 |
| `every hour` | `0 * * * *` | |
| `every N hours` | `0 */N * * *` | N: 1–23 |

### Daily

| Phrase | Cron | Notes |
|--------|------|-------|
| `every day at midnight` | `0 0 * * *` | |
| `every day at noon` | `0 12 * * *` | |
| `every day at 9am` | `0 9 * * *` | hour: 1–12 |
| `every day at 11pm` | `0 23 * * *` | |
| `every day at 9:30am` | `30 9 * * *` | hour: 1–12, minute: 0–59 |
| `every day at 11:59pm` | `59 23 * * *` | |

### Weekly — Named Weekday

| Phrase | Cron | Notes |
|--------|------|-------|
| `every monday` | `0 0 * * 1` | sunday=0 … saturday=6 |
| `every friday` | `0 0 * * 5` | |
| `every sunday` | `0 0 * * 0` | |
| `every monday at 9am` | `0 9 * * 1` | |
| `every friday at 5pm` | `0 17 * * 5` | |
| `every monday at 9:30am` | `30 9 * * 1` | |
| `every friday at 5:15pm` | `15 17 * * 5` | |

### Weekly — Groups

| Phrase | Cron | Notes |
|--------|------|-------|
| `every weekday` | `0 0 * * 1-5` | Mon–Fri |
| `every weekday at 9am` | `0 9 * * 1-5` | |
| `every weekday at 9:30am` | `30 9 * * 1-5` | |
| `every weekend` | `0 0 * * 0,6` | Sat + Sun |
| `every weekend at 10am` | `0 10 * * 0,6` | |

### Monthly

| Phrase | Cron | Notes |
|--------|------|-------|
| `every month` | `0 0 1 * *` | |
| `every month on the 1st` | `0 0 1 * *` | day: 1–31; any ordinal suffix accepted |
| `every month on the 15th` | `0 0 15 * *` | |
| `every month on the 1st at 9am` | `0 9 1 * *` | |
| `every month on the 15th at 6pm` | `0 18 15 * *` | |

### Yearly

| Phrase | Cron | Notes |
|--------|------|-------|
| `every year` | `0 0 1 1 *` | 1 Jan at midnight |

---

## Raw Cron Expressions

Any valid 5-field cron expression is accepted unchanged:

```
┌─ minute  (0–59)
│ ┌─ hour   (0–23)
│ │ ┌─ day of month (1–31)
│ │ │ ┌─ month (1–12)
│ │ │ │ ┌─ day of week (0–6, 0=Sunday)
* * * * *
```

Examples: `0 9 * * 1-5`, `*/15 * * * *`, `0 0 1,15 * *`

---

## Error Messages

When an unrecognised phrase is passed, `InvalidSchedule` names the bad input, suggests the closest known phrase, and lists examples:

```
'every other tuesday' is not a recognized schedule.

Did you mean: 'every tuesday'?

Tarsq accepts either a natural-language phrase or a standard cron expression.
Examples:
    cron="every day at 9am"
    cron="every weekday at 9:30am"
    cron="every monday"
    cron="every 15 minutes"
    cron="0 9 * * 1-5"

See docs/scheduling_phrases.md for the full list of supported phrases.
```
