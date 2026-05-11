from datetime import datetime

WORKER_COLORS = ["\033[94m", "\033[92m", "\033[93m", "\033[95m", "\033[96m"]
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

LEVEL_COLORS = {
    "INFO":  "\033[32m",
    "WARN":  "\033[33m",
    "ERROR": "\033[91m",
    "RETRY": "\033[36m",
    "CRON":  "\033[35m",
}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(worker_id: int, level: str, msg: str):
    worker_color = WORKER_COLORS[worker_id % len(WORKER_COLORS)]
    level_color = LEVEL_COLORS.get(level, "")
    print(
        f"{DIM}{_ts()}{RESET}  "
        f"{worker_color}{BOLD}worker-{worker_id}{RESET}  "
        f"{level_color}{level:<5}{RESET}  "
        f"{msg}"
    )


def sys_log(level: str, msg: str):
    level_color = LEVEL_COLORS.get(level, "")
    print(
        f"{DIM}{_ts()}{RESET}  "
        f"{BOLD}system   {RESET}  "
        f"{level_color}{level:<5}{RESET}  "
        f"{msg}"
    )
