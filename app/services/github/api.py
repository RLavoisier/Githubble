import asyncio
import logging
from datetime import datetime
from time import time
from typing import Any, Optional, Tuple

from fastapi import HTTPException
import httpx

from app.config import get_settings
from app.redis.engine import RedisClient, get_redis_client
from app.schemas.github import GitHubAPIResponseSchema
from app.services.github.formaters import (
    GithubResponseFormatter,
    StargazersFormater,
    StarredRepositoryFormater,
)

logger = logging.getLogger(__name__)

settings = get_settings()


class GitHubAPI:
    GITHUB_PER_PAGE = 100
    AIO_SEMAPHORE_LIMIT = 200
    MAX_REPO_PER_STARGAZERS = 100

    def __init__(
        self, base_url: str, redis_client: RedisClient, token: Optional[str] = None
    ):
        """
        This class encapsulates the GitHub api calls
        """
        self.base_url = base_url
        self.token = token
        self.semaphore = asyncio.Semaphore(self.AIO_SEMAPHORE_LIMIT)
        self.client = httpx.AsyncClient(headers=self.get_headers())
        self.redis_client = redis_client
        self.reset_lock_key = f"github_request_lock_{self.token or 'null'}"
        self.reset_time_key = "github_request_time"

    def get_headers(self) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        else:
            logger.warning("No GitHub token set, requests will be limited.")
        return headers

    def get_endpoint_url(self, endpoint: str, per_page: int | None = None) -> str:
        return f"{self.base_url}{endpoint}?per_page={per_page or self.GITHUB_PER_PAGE}"

    async def handle_rate_limit(self, response: httpx.Response):
        """
        We Handle the github rate limit by addding a flag to our redis cache and avoid useless requests
        """
        if int(response.headers.get("X-RateLimit-remaining", 1)) < 1:
            reset_timestamp = int(response.headers["X-RateLimit-Reset"])
            lock_duration = reset_timestamp - int(time())
            reset_time = datetime.fromtimestamp(reset_timestamp)
            await self.redis_client.set_cache_value(
                self.reset_lock_key, 1, ex=lock_duration
            )
            await self.redis_client.set_cache_value(
                self.reset_time_key,
                reset_time.strftime("%Y-%m-%d %H:%M:%S"),
                ex=lock_duration,
            )

    async def rate_limit_reached(self) -> bool:
        return await self.redis_client.key_exists(self.reset_lock_key)

    async def make_request(self, url: str) -> GitHubAPIResponseSchema:
        cached_response = await self.redis_client.get_cached_value_by_key(url)

        if cached_response:
            return GitHubAPIResponseSchema.model_validate(cached_response)

        if await self.rate_limit_reached():
            reset_time = await self.redis_client.get_cached_value_by_key(
                self.reset_time_key
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": f"GitHub rate limit reached. The limit will be restored at {reset_time or 'unknown'}"
                },
            )
        async with self.semaphore:
            response = await self.client.get(url)
            await self.handle_rate_limit(response)
            response.raise_for_status()
            response = {"links": response.links, "content": response.text}
            await self.redis_client.set_cache_value(url, response)
            return GitHubAPIResponseSchema.model_validate(response)

    async def get_nb_pages(self, response: GitHubAPIResponseSchema) -> int:
        """
        Extracting the last page from the links header, formatted like so :
        <https://api.github.com/repositories/160919119/stargazers?per_page=100&page=2>; rel="next",
        <https://api.github.com/repositories/160919119/stargazers?per_page=100&page=400>; rel="last"
        """
        if "last" not in response.links:
            return 1
        last_link = response.links["last"]["url"]
        return int(last_link.split("&page=")[-1])

    async def get_paginated_data(
        self,
        endpoint: str,
        formatter: GithubResponseFormatter,
        limit: int | None = None,
    ) -> list[Any]:
        if limit and limit < self.GITHUB_PER_PAGE:
            per_page = limit
        else:
            per_page = self.GITHUB_PER_PAGE
        url = self.get_endpoint_url(endpoint, per_page=per_page)

        data = []
        try:
            # Fetch the first page
            first_page_response = await self.make_request(url)
            data.extend(await formatter(first_page_response))
            # Determine number of pages
            nb_pages = await self.get_nb_pages(first_page_response)
            if limit is None:
                limit = nb_pages * per_page
            # Fetch remaining pages concurrently
            if nb_pages > 1 and limit > self.GITHUB_PER_PAGE:
                # We are computing the remaining pages based on the limit
                needed_pages = limit // self.GITHUB_PER_PAGE

                responses = await asyncio.gather(
                    *[
                        self.make_request(f"{url}&page={i}")
                        for i in range(2, needed_pages + 1)
                    ],
                    return_exceptions=True,
                )

                # If there is remaining records, we add an extra page with those
                remaining_records = limit % self.GITHUB_PER_PAGE
                if remaining_records != 0:
                    url = self.get_endpoint_url(endpoint, per_page=remaining_records)
                    responses.append(
                        await self.make_request(f"{url}&page={needed_pages + 1}")
                    )

                for response in responses:
                    if not isinstance(response, GitHubAPIResponseSchema):
                        continue
                    data.extend(await formatter(response))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
        return data

    async def get_stargazers_by_repo(
        self, owner: str, repo: str, max_stargazers: int
    ) -> list[dict[str, Any]]:
        endpoint = f"repos/{owner}/{repo}/stargazers"
        formatter = StargazersFormater()
        stargazers = await self.get_paginated_data(
            endpoint, formatter, limit=max_stargazers
        )
        return stargazers

    async def get_starred_repos_by_username(
        self, username: str, max_repo: int = MAX_REPO_PER_STARGAZERS
    ) -> Tuple[str, list[str]]:
        endpoint = f"users/{username}/starred"
        formatter = StarredRepositoryFormater()
        starred_repos = await self.get_paginated_data(endpoint, formatter, max_repo)
        return username, starred_repos

    async def close(self):
        await self.client.aclose()


def get_github_api():
    return GitHubAPI(
        base_url=str(settings.github_api_base_url),
        redis_client=get_redis_client(),
        token=settings.github_token,
    )
