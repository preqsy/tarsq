import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock, call


# ── _check_ctx_picklable ──────────────────────────────────────────────────────

def test_check_ctx_picklable_warns_on_unpicklable_value():
    from tarsq.worker import _check_ctx_picklable

    class Unpicklable:
        def __reduce__(self):
            raise TypeError("cannot pickle")

    with patch("tarsq.worker.log") as mock_log:
        _check_ctx_picklable(0, {"db": Unpicklable()})
        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        assert args[1] == "WARN"
        assert "db" in args[2]


def test_check_ctx_picklable_silent_on_picklable_values():
    from tarsq.worker import _check_ctx_picklable

    with patch("tarsq.worker.log") as mock_log:
        _check_ctx_picklable(0, {"key": "value", "count": 42, "flag": True})
        mock_log.assert_not_called()


def test_check_ctx_picklable_warns_per_bad_key():
    from tarsq.worker import _check_ctx_picklable
    import threading

    # threading.Lock is not picklable
    with patch("tarsq.worker.log") as mock_log:
        _check_ctx_picklable(0, {"lock1": threading.Lock(), "lock2": threading.Lock()})
        assert mock_log.call_count == 2


def test_check_ctx_picklable_empty_ctx():
    from tarsq.worker import _check_ctx_picklable

    with patch("tarsq.worker.log") as mock_log:
        _check_ctx_picklable(0, {})
        mock_log.assert_not_called()


# ── get_task_from_registry ────────────────────────────────────────────────────

def test_get_task_from_registry_raises_for_unknown_task():
    from tarsq.worker import get_task_from_registry
    with pytest.raises(ValueError, match="unknown task"):
        get_task_from_registry("nonexistent_task")


def test_get_task_from_registry_returns_task():
    from tarsq.worker import get_task_from_registry
    from tarsq.core.decorator import registry, task

    @task("test_registry_lookup")
    def my_task(ctx, payload): pass

    result = get_task_from_registry("test_registry_lookup")
    assert result.func is my_task


# ── _run_task ─────────────────────────────────────────────────────────────────

def test_run_task_calls_sync_function():
    from tarsq.worker import _run_task

    called_with = {}

    def my_func(ctx, payload):
        called_with["ctx"] = ctx
        called_with["payload"] = payload

    _run_task({"db": "mock"}, my_func, {"key": "value"})

    assert called_with["ctx"] == {"db": "mock"}
    assert called_with["payload"] == {"key": "value"}


def test_run_task_calls_async_function():
    from tarsq.worker import _run_task

    called_with = {}

    async def my_func(ctx, payload):
        called_with["ctx"] = ctx
        called_with["payload"] = payload

    _run_task({"x": 1}, my_func, {"key": "value"})

    assert called_with["ctx"] == {"x": 1}
    assert called_with["payload"] == {"key": "value"}


def test_run_task_passes_empty_ctx():
    from tarsq.worker import _run_task

    called_with = {}

    def my_func(ctx, payload):
        called_with["ctx"] = ctx

    _run_task({}, my_func, {})

    assert called_with["ctx"] == {}


# ── handle_retry ──────────────────────────────────────────────────────────────

def test_handle_retry_requeues_job():
    from tarsq.worker import handle_retry
    from tarsq.core.schemas import Job

    job = Job(job_id="abc-123", task="send_email", payload={"to": "x"}, retries=0)

    with patch("tarsq.worker.redis.Redis") as mock_redis_cls, \
         patch("tarsq.worker.time.sleep"):
        mock_r = MagicMock()
        mock_redis_cls.return_value = mock_r

        handle_retry(job, retries=1, worker_id=0, value="raw_value", job_id="abc-123", max_retries=3)

        mock_r.lpush.assert_called_once()
        queued = json.loads(mock_r.lpush.call_args[0][1])
        assert queued["task"] == "send_email"
        assert queued["retries"] == 1


def test_handle_retry_removes_from_processing():
    from tarsq.worker import handle_retry
    from tarsq.core.schemas import Job

    job = Job(job_id="abc-123", task="send_email", payload={}, retries=0)

    with patch("tarsq.worker.redis.Redis") as mock_redis_cls, \
         patch("tarsq.worker.time.sleep"):
        mock_r = MagicMock()
        mock_redis_cls.return_value = mock_r

        handle_retry(job, retries=1, worker_id=0, value="raw_value", job_id="abc-123", max_retries=3)

        mock_r.lrem.assert_called_once_with("tarsq:processing", 1, "raw_value")


def test_handle_retry_updates_status_to_queued():
    from tarsq.worker import handle_retry
    from tarsq.core.schemas import Job, TaskStatusEnum

    job = Job(job_id="abc-123", task="send_email", payload={}, retries=0)

    with patch("tarsq.worker.redis.Redis") as mock_redis_cls, \
         patch("tarsq.worker.time.sleep"):
        mock_r = MagicMock()
        mock_redis_cls.return_value = mock_r

        handle_retry(job, retries=1, worker_id=0, value="raw_value", job_id="abc-123", max_retries=3)

        hset_call = mock_r.hset.call_args
        assert hset_call[1]["mapping"]["status"] == TaskStatusEnum.QUEUED
        assert hset_call[1]["mapping"]["retries"] == 1


def test_handle_retry_exponential_backoff():
    from tarsq.worker import handle_retry
    from tarsq.core.schemas import Job

    job = Job(job_id="abc-123", task="send_email", payload={}, retries=0)

    with patch("tarsq.worker.redis.Redis") as mock_redis_cls, \
         patch("tarsq.worker.time.sleep") as mock_sleep:
        mock_redis_cls.return_value = MagicMock()

        handle_retry(job, retries=3, worker_id=0, value="raw", job_id="abc-123", max_retries=5)

        # delay = 2^retries = 2^3 = 8
        mock_sleep.assert_called_once_with(8)


# ── recover_stuck_tasks ───────────────────────────────────────────────────────

def test_recover_stuck_tasks_requeues_items():
    with patch("tarsq.cli.redis.Redis") as mock_redis_cls:
        mock_r = MagicMock()
        mock_r.lrange.return_value = ["job1", "job2"]
        mock_redis_cls.return_value = mock_r

        from tarsq.cli import recover_stuck_tasks
        recover_stuck_tasks()

        assert mock_r.lpush.call_count == 2
        mock_r.delete.assert_called_once_with("tarsq:processing")


def test_recover_stuck_tasks_does_nothing_when_queue_clean():
    with patch("tarsq.cli.redis.Redis") as mock_redis_cls:
        mock_r = MagicMock()
        mock_r.lrange.return_value = []
        mock_redis_cls.return_value = mock_r

        from tarsq.cli import recover_stuck_tasks
        recover_stuck_tasks()

        mock_r.lpush.assert_not_called()
        mock_r.delete.assert_not_called()


# ── worker Redis reconnect ────────────────────────────────────────────────────

def test_worker_retries_on_redis_connection_error():
    import redis as redis_lib
    from tarsq.worker import worker

    shutdown_event = MagicMock()
    # First is_set: enter loop; after connection error: exit
    shutdown_event.is_set.side_effect = [False, False, True]

    mock_r = MagicMock()
    mock_r.blmove.side_effect = [
        redis_lib.ConnectionError("connection refused"),
        None,  # second attempt returns None (no job), loop exits
    ]

    with patch("tarsq.worker.redis.Redis", return_value=mock_r), \
         patch("tarsq.worker.importlib.import_module"), \
         patch("tarsq.worker.time.sleep"):

        worker(0, None, shutdown_event)

    assert mock_r.blmove.call_count == 2


def test_worker_continues_after_redis_reconnects():
    import redis as redis_lib
    from tarsq.worker import worker

    shutdown_event = MagicMock()
    # False → enter; False → retry after error; False → enter again; True → exit
    shutdown_event.is_set.side_effect = [False, False, False, True]

    mock_r = MagicMock()
    mock_r.blmove.side_effect = [
        redis_lib.ConnectionError("down"),
        None,  # reconnected successfully, no job
        None,
    ]

    with patch("tarsq.worker.redis.Redis", return_value=mock_r), \
         patch("tarsq.worker.importlib.import_module"):

        worker(0, None, shutdown_event)

    # blmove was called again after the error — worker recovered
    assert mock_r.blmove.call_count == 3
