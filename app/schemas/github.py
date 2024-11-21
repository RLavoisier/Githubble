from typing import Any

from pydantic import BaseModel


class GitHubAPIResponseSchema(BaseModel):
    content: str
    links: dict[str, Any]
