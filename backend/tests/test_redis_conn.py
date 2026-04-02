import pytest
from unittest.mock import MagicMock

from app.core.redis_conn import get_redis, redis_available
from app.config import settings


def test_redis_available_success(monkeypatch):
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    mock_get_redis = MagicMock(return_value=mock_redis)
    monkeypatch.setattr("app.core.redis_conn.get_redis", mock_get_redis)

    assert redis_available() is True
    mock_get_redis.assert_called_once()


def test_redis_available_exception(monkeypatch):
    mock_redis = MagicMock()
    mock_redis.ping.side_effect = Exception("Connection error")

    mock_get_redis = MagicMock(return_value=mock_redis)
    monkeypatch.setattr("app.core.redis_conn.get_redis", mock_get_redis)

    assert redis_available() is False
    mock_get_redis.assert_called_once()


def test_get_redis_for_api(monkeypatch):
    mock_from_url = MagicMock()
    monkeypatch.setattr("app.core.redis_conn.Redis.from_url", mock_from_url)

    get_redis(for_worker=False)

    mock_from_url.assert_called_once_with(
        settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=2
    )


def test_get_redis_for_worker(monkeypatch):
    mock_from_url = MagicMock()
    monkeypatch.setattr("app.core.redis_conn.Redis.from_url", mock_from_url)

    get_redis(for_worker=True)

    mock_from_url.assert_called_once_with(
        settings.REDIS_URL, socket_connect_timeout=3, socket_timeout=None
    )
