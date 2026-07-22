"""Unit tests for Chrome DevTools Protocol cookie extraction."""

import json

import pytest

from xhs_cli.cdp_cookies import _fetch_cookies, extract_cdp_cookies


class _AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *args):
        return None


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/test"}


class _HttpClient:
    async def get(self, url, timeout):
        assert url == "http://127.0.0.1:9222/json/version"
        assert timeout == 5
        return _Response()


class _WebSocket:
    async def send(self, payload):
        assert json.loads(payload) == {"id": 1, "method": "Network.getCookies"}

    async def recv(self):
        return json.dumps(
            {
                "result": {
                    "cookies": [
                        {"name": "a1", "value": "secret", "domain": ".xiaohongshu.com"},
                        {"name": "other", "value": "ignored", "domain": ".example.com"},
                    ]
                }
            }
        )


@pytest.mark.asyncio
async def test_fetches_only_xiaohongshu_cookies(monkeypatch):
    monkeypatch.setattr("xhs_cli.cdp_cookies.httpx.AsyncClient", lambda: _AsyncContext(_HttpClient()))
    monkeypatch.setattr("xhs_cli.cdp_cookies.websockets.connect", lambda *args, **kwargs: _AsyncContext(_WebSocket()))

    assert await _fetch_cookies("127.0.0.1", 9222) == {"a1": "secret"}


def test_rejects_invalid_port():
    with pytest.raises(ValueError, match="between 1 and 65535"):
        extract_cdp_cookies(0)
