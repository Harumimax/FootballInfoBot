from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str
    status_code: int


class HttpPageClient:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._headers = {"User-Agent": user_agent}
        self._timeout = httpx.Timeout(timeout_seconds)

    async def fetch(self, url: str) -> FetchedPage:
        async with httpx.AsyncClient(headers=self._headers, timeout=self._timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return FetchedPage(url=str(response.url), html=response.text, status_code=response.status_code)
