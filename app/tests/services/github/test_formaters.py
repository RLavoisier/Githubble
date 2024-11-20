from unittest.mock import Mock

import httpx
import pytest

from app.services.github.formaters import StargazersFormater, StarredRepositoryFormater


class TestStargazersFormater:
    @pytest.mark.asyncio
    async def test_format_response(self):
        json_response = [
            {"login": "test_login", "html_url": "http://test.com", "useless_key": 0},
            {"login": "test_login2", "html_url": "http://test2.com", "useless_key": 0},
            {"login": "test_login3", "html_url": "http://test3.com", "useless_key": 0},
        ]
        response = Mock(spec=httpx.Response)
        response.json = Mock(return_value=json_response)
        formater = StargazersFormater()

        result = await formater(response)

        assert result == [
            {"login": "test_login", "html_url": "http://test.com"},
            {"login": "test_login2", "html_url": "http://test2.com"},
            {"login": "test_login3", "html_url": "http://test3.com"},
        ]


class TestStarredRepositoryFormater:
    @pytest.mark.asyncio
    async def test_format_response(self):
        json_response = [
            {"full_name": "test_repo", "html_url": "http://test.com", "useless_key": 0},
            {
                "full_name": "test_repo2",
                "html_url": "http://test2.com",
                "useless_key": 0,
            },
            {
                "full_name": "test_repo3",
                "html_url": "http://test3.com",
                "useless_key": 0,
            },
        ]
        response = Mock(spec=httpx.Response)
        response.json = Mock(return_value=json_response)
        formater = StarredRepositoryFormater()

        result = await formater(response)

        assert result == [
            "test_repo",
            "test_repo2",
            "test_repo3",
        ]
