"""HTTP client helpers for Streamlit frontend."""

from __future__ import annotations

import os
from typing import Any

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


class APIClient:
    """Backend API wrapper with cookie forwarding."""

    def __init__(self, cookies: dict[str, str] | None = None):
        self.cookies = cookies or {}

    async def request(self, method: str, path: str, json: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> httpx.Response:
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0, cookies=self.cookies) as client:
            return await client.request(method, path, json=json, params=params)
