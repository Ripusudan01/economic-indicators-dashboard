"""Shared async HTTP client with bounded timeouts and no automatic retries.

Scheduled collectors provide the next bounded retry opportunity after failures.
"""
import httpx
from typing import Any

# Default timeout: 10 s connect, 20 s read.
# Collectors should handle TimeoutError gracefully and set is_stale=True.
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=20.0, write=5.0, pool=5.0)

# One shared client for the process lifetime.
# Initialized at startup; closed at shutdown.
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared async HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={
                "User-Agent": (
                    "EconomicIndicatorsDashboard/1.0 "
                    "(academic project; contact: see README)"
                )
            },
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    """Close the shared client (call at app shutdown)."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def safe_get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
) -> httpx.Response | None:
    """
    Perform a GET request. Returns the Response or None on error.
    Collectors check for None and mark data as stale.
    Logs errors but does not raise — upstream failures must not crash the app.
    """
    client = get_client()
    try:
        response = await client.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout or DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response
    except httpx.TimeoutException as exc:
        print(f"[HTTP] Timeout fetching {url}: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        print(f"[HTTP] HTTP {exc.response.status_code} from {url}")
        return None
    except httpx.RequestError as exc:
        print(f"[HTTP] Request error for {url}: {exc}")
        return None
