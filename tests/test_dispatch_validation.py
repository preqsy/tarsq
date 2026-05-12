import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel


# ── dispatch() payload validation ────────────────────────────────────────────

def test_dispatch_rejects_string_payload():
    with patch("tarsq.client.r"):
        from tarsq.client import dispatch
        with pytest.raises(ValueError):
            dispatch("send_email", payload="not a dict")


def test_dispatch_rejects_int_payload():
    with patch("tarsq.client.r"):
        from tarsq.client import dispatch
        with pytest.raises(ValueError):
            dispatch("send_email", payload=123)


def test_dispatch_rejects_list_payload():
    with patch("tarsq.client.r"):
        from tarsq.client import dispatch
        with pytest.raises(ValueError):
            dispatch("send_email", payload=["a", "b"])


def test_dispatch_accepts_pydantic_model():
    class EmailPayload(BaseModel):
        to: str

    with patch("tarsq.client.r") as mock_r:
        from tarsq.client import dispatch
        job_id = dispatch("send_email", payload=EmailPayload(to="test@example.com"))
        assert job_id is not None
        # verify it was serialized as a dict, not the model object
        import json
        queued = json.loads(mock_r.lpush.call_args[0][1])
        assert queued["payload"] == {"to": "test@example.com"}


def test_dispatch_accepts_none_payload():
    with patch("tarsq.client.r") as mock_r:
        from tarsq.client import dispatch
        dispatch("send_email", payload=None)
        import json
        queued = json.loads(mock_r.lpush.call_args[0][1])
        assert queued["payload"] == {}


def test_dispatch_accepts_empty_dict():
    with patch("tarsq.client.r") as mock_r:
        from tarsq.client import dispatch
        dispatch("send_email", payload={})
        import json
        queued = json.loads(mock_r.lpush.call_args[0][1])
        assert queued["payload"] == {}


# ── task decorator validation ─────────────────────────────────────────────────

def test_task_registers_correctly():
    from tarsq.core.decorator import task, registry
    @task("test_task_reg", timeout=10, max_retries=2)
    def my_task(ctx, payload):
        pass
    assert "test_task_reg" in registry
    assert registry["test_task_reg"].timeout == 10
    assert registry["test_task_reg"].max_retries == 2


def test_task_duplicate_name_overwrites():
    from tarsq.core.decorator import task, registry
    @task("duplicate_task")
    def first(ctx, payload): pass

    @task("duplicate_task")
    def second(ctx, payload): pass

    assert registry["duplicate_task"].func is second


def test_task_rejects_negative_timeout():
    from tarsq.core.decorator import task
    with pytest.raises((ValueError, Exception)):
        @task("bad_timeout", timeout=-1)
        def my_task(ctx, payload): pass


def test_task_rejects_zero_timeout():
    from tarsq.core.decorator import task
    with pytest.raises((ValueError, Exception)):
        @task("zero_timeout", timeout=0)
        def my_task(ctx, payload): pass


def test_task_rejects_negative_max_retries():
    from tarsq.core.decorator import task
    with pytest.raises((ValueError, Exception)):
        @task("bad_retries", max_retries=-1)
        def my_task(ctx, payload): pass


# ── schedule decorator validation ────────────────────────────────────────────

def test_schedule_rejects_invalid_cron():
    from tarsq.core.decorator import schedule
    with pytest.raises((ValueError, Exception)):
        @schedule("bad_cron", cron="not a cron")
        def my_task(ctx, payload): pass


def test_schedule_accepts_valid_cron():
    from tarsq.core.decorator import schedule, cron_registry
    @schedule("valid_cron_task", cron="0 9 * * *")
    def my_task(ctx, payload): pass
    assert cron_registry["valid_cron_task"]["cron"] == "0 9 * * *"


def test_schedule_accepts_preset():
    from tarsq.core.decorator import schedule, cron_registry
    @schedule("preset_task", cron="every hour")
    def my_task(ctx, payload): pass
    assert cron_registry["preset_task"]["cron"] == "0 * * * *"
