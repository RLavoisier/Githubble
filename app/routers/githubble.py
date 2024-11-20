import asyncio
import logging
from collections import defaultdict
from typing import Annotated, DefaultDict

from fastapi import APIRouter, HTTPException
from fastapi.params import Query, Depends
from httpx import HTTPStatusError

from app.redis.engine import get_redis_client
from app.schemas.githubble import StarNeigboursResponse
from app.services.github.api import GitHubAPI, settings

router = APIRouter(prefix="/githubble", tags=["githubble"])
logger = logging.getLogger(__name__)


def get_github_api():
    return GitHubAPI(
        base_url=settings.github_api_base_url,
        redis_client=get_redis_client(),
        token=settings.github_token,
    )


@router.get("/repos/{user}/{repo}/starneighbours")
async def get_repo_star_neighbours(
    user: str,
    repo: str,
    github_api: Annotated[GitHubAPI, Depends(get_github_api)],
    max_stargazers: int = Query(20, ge=1, le=1000),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
) -> list[StarNeigboursResponse]:
    neighbours_repos: DefaultDict[str, set[str]] = defaultdict(set)
    try:
        repo_stargazers = await github_api.get_stargazers_by_repo(
            user, repo, max_stargazers
        )
    except HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail={"error": "API Error", "response": e.response.json()},
        )

    if not repo_stargazers:
        return []

    base_repo_stargazers_set = {stargazer["login"] for stargazer in repo_stargazers}

    neighbours_repos[repo] = base_repo_stargazers_set

    starred_tasks = [
        asyncio.create_task(github_api.get_starred_repos_by_username(username))
        for username in base_repo_stargazers_set
    ]

    for starred_task in asyncio.as_completed(starred_tasks):
        try:
            username, starred_repos = await starred_task
            for starred_repo in starred_repos:
                neighbours_repos[starred_repo].add(username)
        except HTTPStatusError as e:
            logger.warning(f"Failed to fetch starred repos for a user: {e}")

    neighbours_repos_list = sorted(
        [
            StarNeigboursResponse.model_validate(
                {"repo": repo_name, "stargazers": stargazers}
            )
            for repo_name, stargazers in neighbours_repos.items()
        ],
        key=lambda r: len(r.stargazers),
        reverse=True,
    )
    pagination_start = (page - 1) * per_page
    pagination_end = pagination_start + per_page
    return neighbours_repos_list[pagination_start:pagination_end]
