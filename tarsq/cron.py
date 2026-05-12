import signal
import time
from datetime import datetime

from croniter import croniter

from tarsq.client import dispatch
from tarsq.core.decorator import cron_registry
from tarsq.logger import sys_log


def scheduler(shutdown_event):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    sys_log("CRON", "scheduler started")

    while not shutdown_event.is_set():
        now = datetime.now()

        for name, entry in cron_registry.items():
            if croniter.match(entry["cron"], now):
                sys_log("CRON", f"triggered  {name}  [{entry['cron']}]")
                dispatch(name)

        # sleep until the top of the next minute, checking shutdown every second
        seconds_remaining = 60 - now.second
        for _ in range(seconds_remaining):
            if shutdown_event.is_set():
                break
            time.sleep(1)

    sys_log("CRON", "scheduler stopped")

