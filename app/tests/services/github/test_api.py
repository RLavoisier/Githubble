from time import time
import pytest
from unittest.mock import AsyncMock, Mock, ANY
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
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_response.headers = {
            "X-RateLimit-remaining": "10",
            "X-RateLimit-Reset": "1234567890",
        }
        mock_response.links = {}
        return mock_response

    @pytest.mark.asyncio
    async def test_stargazers_retrieved_from_cache(
        self, github_api_service, mock_redis_client
    ):
        mock_redis_client.get_cached_value_by_key.return_value = [
            {"login": "cached_user"}
        ]

        stargazers = await github_api_service.get_stargazers_by_repo(
            "test_owner", "test_repo", 100
        )

        assert stargazers == [{"login": "cached_user"}]
        mock_redis_client.get_cached_value_by_key.assert_called_once_with(
            "test_owner_test_repo_stargazers_100"
        )

    @pytest.mark.asyncio
    async def test_stargazers_fetched_and_cached(
        self, github_api_service, mock_redis_client
    ):
        github_api_service.get_paginated_data = AsyncMock(
            return_value=[{"login": "new_user"}]
        )

        stargazers = await github_api_service.get_stargazers_by_repo(
            "test_owner", "test_repo", 100
        )

        assert stargazers == [{"login": "new_user"}]
        mock_redis_client.set_cache_value.assert_called_once_with(
            "test_owner_test_repo_stargazers_100", [{"login": "new_user"}]
        )

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, github_api_service, mock_redis_client):
        mock_response = Mock(spec=Response)
        mock_response.headers = {
            "X-RateLimit-remaining": "0",
            "X-RateLimit-Reset": str(int(time()) + 100),
        }

        await github_api_service.handle_rate_limit(mock_response)

        mock_redis_client.set_cache_value.assert_any_call(
            github_api_service.reset_lock_key, 1, ex=100
        )
        mock_redis_client.set_cache_value.assert_any_call(
            github_api_service.reset_time_key, ANY, ex=100
        )

    @pytest.mark.asyncio
    async def test_request_fails_when_rate_limited(
        self, github_api_service, mock_redis_client
    ):
        mock_redis_client.key_exists.return_value = True
        mock_redis_client.get_cached_value_by_key.return_value = "2023-01-01 12:00:00"

        with pytest.raises(Exception) as exc_info:
            await github_api_service.make_request("https://api.github.com/test")

        assert "GitHub rate limit reached" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_successful_request(self, github_api_service, mock_httpx_response):
        github_api_service.client.get = AsyncMock(return_value=mock_httpx_response)

        response = await github_api_service.make_request("https://api.github.com/test")

        assert response.status_code == 200
        assert await response.json() == {"key": "value"}

    @pytest.mark.asyncio
    async def test_paginated_data_retrieval(
        self, github_api_service, mock_httpx_response
    ):
        github_api_service.make_request = AsyncMock(return_value=mock_httpx_response)
        github_api_service.get_nb_pages = AsyncMock(return_value=3)

        formatter = AsyncMock(return_value=[{"key": "value"}])
        data = await github_api_service.get_paginated_data(
            "test/endpoint", formatter, limit=300
        )

        assert len(data) == 3
        github_api_service.make_request.assert_any_call(
            "https://api.github.com/test/endpoint?per_page=100&page=2"
        )

    @pytest.mark.asyncio
    async def test_starred_repos_retrieved_from_cache(
        self, github_api_service, mock_redis_client
    ):
        mock_redis_client.get_cached_value_by_key.return_value = ["repo1", "repo2"]

        username, repos = await github_api_service.get_starred_repos_by_username(
            "test_user"
        )

        assert username == "test_user"
        assert repos == ["repo1", "repo2"]
        mock_redis_client.get_cached_value_by_key.assert_called_once_with(
            "test_user_starred_repos"
        )
