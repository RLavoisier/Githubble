from abc import ABC, abstractmethod
from typing import Any

import orjson
from httpx import Response


class GithubResponseFormatter(ABC):
    async def __call__(self, response: Response) -> Any:
        return await self._format_json_resonse(orjson.loads(response.content))

    @abstractmethod
    async def _format_json_resonse(self, response_json: list[dict[str, Any]]) -> Any:
        raise NotImplementedError()


class StargazersFormater(GithubResponseFormatter):
    async def _format_json_resonse(
        self, response_json: list[dict[str, Any]]
    ) -> list[Any]:
        return [{"login": r["login"], "html_url": r["html_url"]} for r in response_json]


class StarredRepositoryFormater(GithubResponseFormatter):
    async def _format_json_resonse(
        self, response_json: list[dict[str, Any]]
    ) -> list[str]:
        return [r["full_name"] for r in response_json]
