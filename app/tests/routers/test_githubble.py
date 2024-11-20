import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException
from httpx import HTTPStatusError, Response
from app.schemas.githubble import StarNeigboursResponse
from app.services.github.api import GitHubAPI


MOCK_USER = "testuser"
MOCK_REPO = "testrepo"
MOCK_STARGAZERS = [{"login": "user1"}, {"login": "user2"}, {"login": "user3"}]
MOCK_STARRED_REPOS = {
    "user1": ["repo1", "repo2", MOCK_REPO],
    "user2": ["repo2", MOCK_REPO],
    "user3": ["repo3", MOCK_REPO],
}


@pytest.fixture
def mock_github_api():
    api = Mock(spec=GitHubAPI)
    api.get_stargazers_by_repo = AsyncMock()
    api.get_starred_repos_by_username = AsyncMock()
    return api


@pytest.mark.asyncio
async def test_get_repo_star_neighbours_success(mock_github_api):
    mock_github_api.get_stargazers_by_repo.return_value = MOCK_STARGAZERS

    async def mock_get_starred_repos(username):
        return username, MOCK_STARRED_REPOS[username]

    mock_github_api.get_starred_repos_by_username.side_effect = mock_get_starred_repos

    from app.routers.githubble import get_repo_star_neighbours

    result = await get_repo_star_neighbours(
        user=MOCK_USER,
        repo=MOCK_REPO,
        github_api=mock_github_api,
        max_stargazers=20,
        page=1,
        per_page=10,
    )

    assert isinstance(result, list)
    assert all(isinstance(item, StarNeigboursResponse) for item in result)

    repos = {item.repo for item in result}
    assert MOCK_REPO in repos
    assert "repo1" in repos
    assert "repo2" in repos
    assert "repo3" in repos

    assert len(result) > 0
    for i in range(len(result) - 1):
        assert len(result[i].stargazers) >= len(result[i + 1].stargazers)


@pytest.mark.asyncio
async def test_get_repo_star_neighbours_empty_stargazers(mock_github_api):
    mock_github_api.get_stargazers_by_repo.return_value = []

    from app.routers.githubble import get_repo_star_neighbours

    result = await get_repo_star_neighbours(
        user=MOCK_USER,
        repo=MOCK_REPO,
        github_api=mock_github_api,
        max_stargazers=20,
        page=1,
        per_page=10,
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_repo_star_neighbours_api_error(mock_github_api):
    mock_response = Mock(spec=Response)
    mock_response.status_code = 404
    mock_response.json.return_value = {"message": "Not Found"}
    mock_error = HTTPStatusError("Not Found", request=Mock(), response=mock_response)

    mock_github_api.get_stargazers_by_repo.side_effect = mock_error

    from app.routers.githubble import get_repo_star_neighbours

    with pytest.raises(HTTPException) as exc_info:
        await get_repo_star_neighbours(
            user=MOCK_USER,
            repo=MOCK_REPO,
            github_api=mock_github_api,
            max_stargazers=20,
            page=1,
            per_page=10,
        )

    assert exc_info.value.status_code == 404
    assert "API Error" in exc_info.value.detail["error"]


@pytest.mark.asyncio
async def test_get_repo_star_neighbours_pagination(mock_github_api):
    mock_github_api.get_stargazers_by_repo.return_value = MOCK_STARGAZERS

    async def mock_get_starred_repos(username):
        return username, MOCK_STARRED_REPOS[username]

    mock_github_api.get_starred_repos_by_username.side_effect = mock_get_starred_repos

    from app.routers.githubble import get_repo_star_neighbours

    result_page_1 = await get_repo_star_neighbours(
        user=MOCK_USER,
        repo=MOCK_REPO,
        github_api=mock_github_api,
        max_stargazers=20,
        page=1,
        per_page=2,
    )

    result_page_2 = await get_repo_star_neighbours(
        user=MOCK_USER,
        repo=MOCK_REPO,
        github_api=mock_github_api,
        max_stargazers=20,
        page=2,
        per_page=2,
    )

    assert len(result_page_1) == 2
    assert len(result_page_2) > 0
    assert result_page_1 != result_page_2


@pytest.mark.asyncio
async def test_get_repo_star_neighbours_failed_starred_repos(mock_github_api):
    mock_github_api.get_stargazers_by_repo.return_value = MOCK_STARGAZERS

    async def mock_get_starred_repos(username):
        if username == "user2":
            mock_response = Mock(spec=Response)
            mock_response.status_code = 403
            raise HTTPStatusError(
                "Rate limited", request=Mock(), response=mock_response
            )
        return username, MOCK_STARRED_REPOS[username]

    mock_github_api.get_starred_repos_by_username.side_effect = mock_get_starred_repos

    from app.routers.githubble import get_repo_star_neighbours

    result = await get_repo_star_neighbours(
        user=MOCK_USER,
        repo=MOCK_REPO,
        github_api=mock_github_api,
        max_stargazers=20,
        page=1,
        per_page=10,
    )

    assert len(result) > 0
