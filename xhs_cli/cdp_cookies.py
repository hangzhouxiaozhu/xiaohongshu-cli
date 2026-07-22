"""Read Xiaohongshu cookies from a locally debug-enabled Chromium browser."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _is_xhs_domain(domain: object) -> bool:
    if not isinstance(domain, str):
        return False
    normalized = domain.lstrip(".").lower()
    return normalized == "xiaohongshu.com" or normalized.endswith(".xiaohongshu.com")


def extract_cdp_cookies(port: int, host: str = "127.0.0.1") -> dict[str, str] | None:
    """Read one coherent XHS session over CDP from localhost."""
    if not 1 <= port <= 65535:
        raise ValueError("CDP port must be between 1 and 65535")
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("CDP host must be localhost or 127.0.0.1")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}",
                timeout=5_000,
            )
            for context in browser.contexts:
                cookies = {
                    entry["name"]: entry["value"]
                    for entry in context.cookies(["https://www.xiaohongshu.com/"])
                    if isinstance(entry.get("name"), str)
                    and isinstance(entry.get("value"), str)
                    and _is_xhs_domain(entry.get("domain"))
                }
                if cookies.get("a1"):
                    return cookies
            # Do not close the connection: this is the user's existing browser.
    except Exception as exc:
        logger.debug("Local CDP cookie extraction failed on port %d: %s", port, exc)

    return None
