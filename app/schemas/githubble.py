from pydantic import BaseModel, Field


class StarNeigboursResponse(BaseModel):
    repo: str = Field(examples=["Mergify"])
    stargazers: list[str] = Field(examples=[["Pierre", "Paul", "Jacques"]])
