from typing import Optional

from pydantic import BaseModel, Field


class StarNeighbours(BaseModel):
    repo: str = Field(examples=["Mergify"])
    stargazers: list[str] = Field(examples=[["Pierre", "Paul", "Jacques"]])


class StarNeighboursResponse(BaseModel):
    star_neighbours: list[StarNeighbours]
    next: Optional[str] = Field(
        examples=[
            "/githubble/repos/myuser/myrepo/starneighbours?max_stargazers=100&page=2&per_page=10"
        ]
    )
