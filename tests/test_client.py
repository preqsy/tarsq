import pytest
from unittest.mock import patch, MagicMock
import redis

from tarsq.core.schemas import TaskStatusEnum


def test_dispatch_returns_job_id():
    with patch("tarsq.client.r") as mock_r:
        from tarsq.client import dispatch
        job_id = dispatch("send_email", payload={"to": "test@example.com"})
        assert isinstance(job_id, str)
        assert len(job_id) == 36  # UUID format


def test_dispatch_pushes_to_queue():
    with patch("tarsq.client.r") as mock_r:
        from tarsq.client import dispatch
        dispatch("send_email", payload={"to": "test@example.com"})
        mock_r.lpush.assert_called_once()
        mock_r.hset.assert_called_once()


def test_dispatch_empty_payload():
    with patch("tarsq.client.r") as mock_r:
        from tarsq.client import dispatch
        job_id = dispatch("send_email")
        assert job_id is not None
        args = mock_r.lpush.call_args[0]
        import json
        job = json.loads(args[1])
        assert job["payload"] == {}


def test_dispatch_redis_unreachable():
    with patch("tarsq.client.r") as mock_r:
        mock_r.lpush.side_effect = redis.RedisError("connection refused")
        from tarsq.client import dispatch
        with pytest.raises(ConnectionError):
            dispatch("send_email")


def test_status_returns_job():
    with patch("tarsq.client.r") as mock_r:
        mock_r.hgetall.return_value = {
            "job_id": "abc-123",
            "task": "send_email",
            "status": TaskStatusEnum.COMPLETED,
            "retries": "0",
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "",
        }
        from tarsq.client import status
        job = status("abc-123")
        assert job.job_id == "abc-123"
        assert job.status == TaskStatusEnum.COMPLETED


def test_status_returns_none_for_missing_job():
    with patch("tarsq.client.r") as mock_r:
        mock_r.hgetall.return_value = {}
        from tarsq.client import status
        assert status("nonexistent-id") is None


def test_status_redis_unreachable():
    with patch("tarsq.client.r") as mock_r:
        mock_r.hgetall.side_effect = redis.RedisError("connection refused")
        from tarsq.client import status
        with pytest.raises(ConnectionError):
            status("abc-123")
