"""Extract Xiaohongshu cookies from a running Chromium browser via CDP."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)


async def _fetch_cookies(host: str, port: int) -> dict[str, str] | None:
    try:
        async with httpx.AsyncClient() as http:
            response = await http.get(f"http://{host}:{port}/json/version", timeout=5)
            response.raise_for_status()
            websocket_url = response.json()["webSocketDebuggerUrl"]
            if host not in {"127.0.0.1", "localhost"}:
                websocket_url = websocket_url.replace("127.0.0.1", host).replace("localhost", host)

        async with websockets.connect(websocket_url, open_timeout=5, close_timeout=5) as websocket:
            await websocket.send(json.dumps({"id": 1, "method": "Network.getCookies"}))
            raw = await asyncio.wait_for(websocket.recv(), timeout=10)
            message = json.loads(raw)
    except (httpx.HTTPError, WebSocketException, OSError, KeyError, ValueError, asyncio.TimeoutError) as exc:
        logger.debug("CDP cookie extraction failed on %s:%d: %s", host, port, exc)
        return None

    cookies = {
        cookie["name"]: cookie["value"]
        for cookie in message.get("result", {}).get("cookies", [])
        if "xiaohongshu.com" in cookie.get("domain", "")
    }
    return cookies if cookies.get("a1") else None


def extract_cdp_cookies(port: int, host: str = "127.0.0.1") -> dict[str, str] | None:
    """Return XHS cookies exposed by a browser debugging endpoint."""
    if not 1 <= port <= 65535:
        raise ValueError("CDP port must be between 1 and 65535")
    return asyncio.run(_fetch_cookies(host, port))
