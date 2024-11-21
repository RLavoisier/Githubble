import asyncio
import logging
from collections import defaultdict
from typing import Annotated, DefaultDict, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.params import Query, Depends
from httpx import HTTPStatusError

from app.models import User
from app.redis.engine import get_redis_client
from app.routers.user import validate_api_key
from app.schemas.githubble import StarNeighboursResponse, StarNeighbours
from app.services.github.api import GitHubAPI, settings

router = APIRouter(prefix="/githubble", tags=["githubble"])
logger = logging.getLogger(__name__)


def get_github_api():
    return GitHubAPI(
        base_url=settings.github_api_base_url,
        redis_client=get_redis_client(),
        token=settings.github_token,
    )


@router.get(
    "/repos/{user}/{repo}/starneighbours",
    summary="Retrieve the neighbour repositories based on the stargazers.",
    description=(
        """
        You can fetch the neighbour repositories of a given repository based on its stargazers. 
        The result will be ordered by common stargarzers amount.
        """
    ),
)
async def get_repo_star_neighbours(
    user: str,
    repo: str,
    req: Request,
    github_api: Annotated[GitHubAPI, Depends(get_github_api)],
    auth_user: User = Depends(validate_api_key),
    max_stargazers: int = Query(20, ge=1, le=1000),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
) -> StarNeighboursResponse:
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
        return StarNeighboursResponse(star_neighbours=[], next=None)

    base_repo_stargazers_set = {stargazer["login"] for stargazer in repo_stargazers}

    neighbours_repos[repo] = base_repo_stargazers_set

    starred_repos_results: Any = await asyncio.gather(
        *[
            github_api.get_starred_repos_by_username(username)
            for username in base_repo_stargazers_set
        ],
        return_exceptions=True,
    )

    for result in starred_repos_results:
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch starred repos: {result}")
            continue
        username, starred_repos = result
        for starred_repo in starred_repos:
            neighbours_repos[starred_repo].add(username)

    neighbours_repos_list = sorted(
        [
            StarNeighbours.model_validate({"repo": repo_name, "stargazers": stargazers})
            for repo_name, stargazers in neighbours_repos.items()
        ],
        key=lambda r: len(r.stargazers),
        reverse=True,
    )
    pagination_start = (page - 1) * per_page
    pagination_end = pagination_start + per_page
    paginated_response = neighbours_repos_list[pagination_start:pagination_end]

    next_url = None
    if pagination_end < len(neighbours_repos_list):
        next_url = str(req.url.include_query_params(page=page + 1, per_page=per_page))

    return StarNeighboursResponse(star_neighbours=paginated_response, next=next_url)
