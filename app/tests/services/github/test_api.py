import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException
from app.services.github.api import GitHubAPI
from app.redis.engine import RedisClient
from httpx import Response


class TestGitHubAPI:
    @pytest.fixture
    def mock_redis_client(self):
        mock_client = Mock(spec=RedisClient)
        mock_client.get_cached_value_by_key = AsyncMock(return_value=None)
        mock_client.set_cache_value = AsyncMock()
        mock_client.key_exists = AsyncMock(return_value=False)
        return mock_client

    @pytest.fixture
    def github_api_service(self, mock_redis_client):
        return GitHubAPI(
            base_url="https://api.github.com/",
            redis_client=mock_redis_client,
            token="test-token",
        )

    @pytest.fixture
    def mock_httpx_response(self):
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.links = {}
        mock_response.headers = {
            "X-RateLimit-remaining": "10",
            "X-RateLimit-Reset": "1234567890",
        }
        return mock_response

    @pytest.mark.asyncio
    async def test_request_fails_when_rate_limited(
        self, github_api_service, mock_redis_client
    ):
        mock_redis_client.key_exists.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await github_api_service.make_request("https://api.github.com/test")

        assert exc_info.value.status_code == 403
        assert "GitHub rate limit reached" in str(exc_info.value.detail["error"])
