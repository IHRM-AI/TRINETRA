from __future__ import annotations

from dataclasses import dataclass

import httpx

from trinetra.config import settings


@dataclass(frozen=True)
class NewsItem:
    url: str
    title: str
    content: str


class FirecrawlClient:
    """Self-hosted Firecrawl client for adverse-media acquisition."""

    def __init__(self, base_url: str | None = None, timeout: int = 30):
        self._base = (base_url if base_url is not None else settings.firecrawl_base_url).rstrip("/")
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self._base)

    def search(self, query: str, limit: int = 5) -> list[NewsItem]:
        if not self.available:
            raise RuntimeError("Firecrawl endpoint is not configured (set FIRECRAWL_BASE_URL).")
        response = httpx.post(
            f"{self._base}/v1/search",
            json={"query": query, "limit": limit},
            timeout=self._timeout,
        )
        response.raise_for_status()
        results = response.json().get("data", [])
        return [
            NewsItem(
                url=item.get("url", ""),
                title=item.get("title", ""),
                content=item.get("markdown") or item.get("description", ""),
            )
            for item in results
        ]
