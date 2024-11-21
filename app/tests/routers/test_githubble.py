import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException
from httpx import HTTPStatusError, Response
from app.schemas.githubble import StarNeighboursResponse, StarNeighbours
from app.services.github.api import GitHubAPI

MOCK_USER = "testuser"
MOCK_REPO = "testrepo"
MOCK_STARGAZERS = [{"login": "user1"}, {"login": "user2"}, {"login": "user3"}]
MOCK_STARRED_REPOS = {
    "user1": ["repo1", "repo2", MOCK_REPO],
    "user2": ["repo2", MOCK_REPO],
    "user3": ["repo3", MOCK_REPO],
}


class TestGetRepoStarNeighbours:
    @pytest.fixture
    def mock_github_api(self):
        api = Mock(spec=GitHubAPI)
        api.get_stargazers_by_repo = AsyncMock()
        api.get_starred_repos_by_username = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_successful_retrieval(self, mock_github_api):
        mock_github_api.get_stargazers_by_repo.return_value = MOCK_STARGAZERS

        async def mock_fetch_starred_repos(username):
            return username, MOCK_STARRED_REPOS[username]

        mock_github_api.get_starred_repos_by_username.side_effect = (
            mock_fetch_starred_repos
        )

        req_mock = Mock()
        req_mock.url.include_query_params.return_value = None

        from app.routers.githubble import get_repo_star_neighbours

        result = await get_repo_star_neighbours(
            user=MOCK_USER,
            repo=MOCK_REPO,
            req=req_mock,
            github_api=mock_github_api,
            max_stargazers=20,
            page=1,
            per_page=10,
        )

        assert isinstance(result, StarNeighboursResponse)
        assert isinstance(result.star_neighbours, list)
        assert all(isinstance(item, StarNeighbours) for item in result.star_neighbours)

        repos = {item.repo for item in result.star_neighbours}
        assert MOCK_REPO in repos
        assert "repo1" in repos
        assert "repo2" in repos
        assert "repo3" in repos

        assert len(result.star_neighbours) > 0
        for i in range(len(result.star_neighbours) - 1):
            assert len(result.star_neighbours[i].stargazers) >= len(
                result.star_neighbours[i + 1].stargazers
            )

    @pytest.mark.asyncio
    async def test_empty_stargazers(self, mock_github_api):
        mock_github_api.get_stargazers_by_repo.return_value = []

        req_mock = Mock()
        req_mock.url.include_query_params.return_value = None

        from app.routers.githubble import get_repo_star_neighbours

        result = await get_repo_star_neighbours(
            user=MOCK_USER,
            repo=MOCK_REPO,
            req=req_mock,
            github_api=mock_github_api,
            max_stargazers=20,
            page=1,
            per_page=10,
        )

        assert isinstance(result, StarNeighboursResponse)
        assert result.star_neighbours == []
        assert result.next is None

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_github_api):
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_error = HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        mock_github_api.get_stargazers_by_repo.side_effect = mock_error

        from app.routers.githubble import get_repo_star_neighbours

        req_mock = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await get_repo_star_neighbours(
                user=MOCK_USER,
                repo=MOCK_REPO,
                req=req_mock,
                github_api=mock_github_api,
                max_stargazers=20,
                page=1,
                per_page=10,
            )

        assert exc_info.value.status_code == 404
        assert "API Error" in exc_info.value.detail["error"]

    @pytest.mark.asyncio
    async def test_pagination_handling(self, mock_github_api):
        mock_github_api.get_stargazers_by_repo.return_value = MOCK_STARGAZERS

        async def mock_fetch_starred_repos(username):
            return username, MOCK_STARRED_REPOS[username]

        mock_github_api.get_starred_repos_by_username.side_effect = (
            mock_fetch_starred_repos
        )

        req_mock = Mock()
        req_mock.url.include_query_params.side_effect = lambda **kwargs: (
            f"http://testserver/repos/{MOCK_USER}/{MOCK_REPO}/starneighbours?"
            f"page={kwargs['page']}&per_page={kwargs['per_page']}"
        )

        from app.routers.githubble import get_repo_star_neighbours

        result_page_1 = await get_repo_star_neighbours(
            user=MOCK_USER,
            repo=MOCK_REPO,
            req=req_mock,
            github_api=mock_github_api,
            max_stargazers=20,
            page=1,
            per_page=2,
        )

        result_page_2 = await get_repo_star_neighbours(
            user=MOCK_USER,
            repo=MOCK_REPO,
            req=req_mock,
            github_api=mock_github_api,
            max_stargazers=20,
            page=2,
            per_page=2,
        )

        assert len(result_page_1.star_neighbours) == 2
        assert len(result_page_2.star_neighbours) > 0
        assert (
            result_page_1.next
            == "http://testserver/repos/testuser/testrepo/starneighbours?page=2&per_page=2"
        )

    @pytest.mark.asyncio
    async def test_failed_starred_repos_fetch(self, mock_github_api):
        mock_github_api.get_stargazers_by_repo.return_value = MOCK_STARGAZERS

        async def mock_fetch_starred_repos(username):
            if username == "user2":
                mock_response = Mock(spec=Response)
                mock_response.status_code = 403
                raise HTTPStatusError(
                    "Rate limited", request=Mock(), response=mock_response
                )
            return username, MOCK_STARRED_REPOS[username]

        mock_github_api.get_starred_repos_by_username.side_effect = (
            mock_fetch_starred_repos
        )

        req_mock = Mock()
        req_mock.url.include_query_params.return_value = None

        from app.routers.githubble import get_repo_star_neighbours

        result = await get_repo_star_neighbours(
            user=MOCK_USER,
            repo=MOCK_REPO,
            req=req_mock,
            github_api=mock_github_api,
            max_stargazers=20,
            page=1,
            per_page=10,
        )

        assert len(result.star_neighbours) > 0
        repos = {item.repo for item in result.star_neighbours}
        assert MOCK_REPO in repos
        assert "repo1" in repos
