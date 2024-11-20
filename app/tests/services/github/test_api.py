from time import time

import pytest
from unittest.mock import AsyncMock, Mock, ANY
from app.services.github.api import GitHubAPI
from app.redis.engine import RedisClient
from httpx import Response


@pytest.fixture
def redis_client_mock():
    redis_mock = Mock(spec=RedisClient)
    redis_mock.get_cached_value_by_key = AsyncMock(return_value=None)
    redis_mock.set_cache_value = AsyncMock()
    redis_mock.key_exists = AsyncMock(return_value=False)
    return redis_mock


@pytest.fixture
def github_api(redis_client_mock):
    return GitHubAPI(
        base_url="https://api.github.com/",
        redis_client=redis_client_mock,
        token="test-token",
    )


@pytest.fixture
def httpx_response_mock():
    response = Mock(spec=Response)
    response.status_code = 200
    response.json = AsyncMock(return_value={"key": "value"})
    response.headers = {
        "X-RateLimit-remaining": "10",
        "X-RateLimit-Reset": "1234567890",
    }
    response.links = {}
    return response


@pytest.mark.asyncio
async def test_get_stargazers_by_repo_with_cache(github_api, redis_client_mock):
    redis_client_mock.get_cached_value_by_key.return_value = [{"login": "user1"}]

    stargazers = await github_api.get_stargazers_by_repo("owner", "repo", 100)

    assert stargazers == [{"login": "user1"}]
    redis_client_mock.get_cached_value_by_key.assert_called_once_with(
        "owner_repo_stargazers_100"
    )


@pytest.mark.asyncio
async def test_get_stargazers_by_repo_without_cache(github_api, redis_client_mock):
    github_api.get_paginated_data = AsyncMock(return_value=[{"login": "user1"}])

    stargazers = await github_api.get_stargazers_by_repo("owner", "repo", 100)

    assert stargazers == [{"login": "user1"}]
    redis_client_mock.set_cache_value.assert_called_once_with(
        "owner_repo_stargazers_100", [{"login": "user1"}]
    )


@pytest.mark.asyncio
async def test_handle_rate_limit(github_api, redis_client_mock):
    response = Mock(spec=Response)
    response.headers = {
        "X-RateLimit-remaining": "0",
        "X-RateLimit-Reset": str(int(time()) + 100),
    }

    await github_api.handle_rate_limit(response)

    redis_client_mock.set_cache_value.assert_any_call(
        github_api.reset_lock_key, 1, ex=100
    )
    redis_client_mock.set_cache_value.assert_any_call(
        github_api.reset_time_key, ANY, ex=100
    )


@pytest.mark.asyncio
async def test_make_request_rate_limit_reached(github_api, redis_client_mock):
    redis_client_mock.key_exists.return_value = True
    redis_client_mock.get_cached_value_by_key.return_value = "2023-01-01 12:00:00"

    with pytest.raises(Exception) as exc_info:
        await github_api.make_request("https://api.github.com/test")

    assert "GitHub rate limit reached" in str(exc_info.value)


@pytest.mark.asyncio
async def test_make_request_successful(github_api, httpx_response_mock):
    github_api.client.get = AsyncMock(return_value=httpx_response_mock)

    response = await github_api.make_request("https://api.github.com/test")

    assert response.status_code == 200
    assert await response.json() == {"key": "value"}


@pytest.mark.asyncio
async def test_get_paginated_data(github_api, httpx_response_mock):
    github_api.make_request = AsyncMock(return_value=httpx_response_mock)
    github_api.get_nb_pages = AsyncMock(return_value=3)

    formatter_mock = AsyncMock(return_value=[{"key": "value"}])
    data = await github_api.get_paginated_data(
        "test/endpoint", formatter_mock, limit=300
    )

    assert len(data) == 3
    github_api.make_request.assert_any_call(
        "https://api.github.com/test/endpoint?per_page=100&page=2"
    )


@pytest.mark.asyncio
async def test_get_starred_repos_by_username_with_cache(github_api, redis_client_mock):
    redis_client_mock.get_cached_value_by_key.return_value = ["repo1", "repo2"]

    username, repos = await github_api.get_starred_repos_by_username("user1")

    assert username == "user1"
    assert repos == ["repo1", "repo2"]
    redis_client_mock.get_cached_value_by_key.assert_called_once_with(
        "user1_starred_repos"
    )
