import signal
import time
import importlib
from datetime import datetime

from croniter import croniter
import redis
from tarsq.config import settings
from tarsq.client import dispatch
from tarsq.core.decorator import cron_registry
from tarsq.logger import sys_log


def scheduler(shutdown_event, app):

    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        password=settings.REDIS_PASSWORD,
    )

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    sys_log("CRON", "scheduler started")
    importlib.import_module(app)

    for k, v in cron_registry.items():

        r.hset(
            f"tarsq:cron:{k}",
            mapping={
                "func": k,
                "cron": v["cron"],
                "registered_at": datetime.now().isoformat(),
            },
        )
    while not shutdown_event.is_set():
        now = datetime.now()

        for k, v in cron_registry.items():
            if croniter.match(v["cron"], now):
                sys_log("CRON", f"dispatching  {k}  [{v['cron']}]")
                dispatch(k)

        # sleep until the top of the next minute, checking shutdown every second
        seconds_remaining = 60 - now.second
        for _ in range(seconds_remaining):
            if shutdown_event.is_set():
                break
            time.sleep(1)

    sys_log("CRON", "scheduler stopped")
