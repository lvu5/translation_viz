import asyncio
import time
from typing import Any

import httpx

from .utils import get_config

NOMINATIM_SEARCH_URL = str(
    get_config(
        "NOMINATIM_SEARCH_URL",
        "https://nominatim.openstreetmap.org/search",
    )
)
NOMINATIM_USER_AGENT = str(
    get_config(
        "NOMINATIM_USER_AGENT",
        "last-translation-benchmark/0.0.1 "
        "(last-translation-benchmark@vilda.net)",
    )
)
GEOCODING_CACHE_SECONDS = 24 * 60 * 60
NOMINATIM_MIN_REQUEST_INTERVAL_SECONDS = 1.0

_HTTP_CLIENT: httpx.AsyncClient | None = None
_GEOCODING_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_GEOCODING_LOCK = asyncio.Lock()
_LAST_GEOCODING_REQUEST_AT = 0.0


class GeocodingUnavailableError(RuntimeError):
    pass


async def geocode_location(
    query: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any] | None:
    global _HTTP_CLIENT, _LAST_GEOCODING_REQUEST_AT

    normalized_query = " ".join(query.split())
    if not normalized_query:
        return None
    cache_key = normalized_query.casefold()
    cached = _GEOCODING_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < GEOCODING_CACHE_SECONDS:
        return cached[1]

    uses_public_client = client is None
    if uses_public_client:
        if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
            _HTTP_CLIENT = httpx.AsyncClient(
                timeout=10,
                follow_redirects=True,
                headers={"User-Agent": NOMINATIM_USER_AGENT},
            )
        client = _HTTP_CLIENT

    async def fetch_candidate() -> Any:
        response = await client.get(
            NOMINATIM_SEARCH_URL,
            params={
                "q": normalized_query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 1,
            },
        )
        response.raise_for_status()
        return response.json()

    try:
        if uses_public_client:
            async with _GEOCODING_LOCK:
                elapsed = time.monotonic() - _LAST_GEOCODING_REQUEST_AT
                if elapsed < NOMINATIM_MIN_REQUEST_INTERVAL_SECONDS:
                    await asyncio.sleep(
                        NOMINATIM_MIN_REQUEST_INTERVAL_SECONDS - elapsed
                    )
                try:
                    payload = await fetch_candidate()
                finally:
                    _LAST_GEOCODING_REQUEST_AT = time.monotonic()
        else:
            payload = await fetch_candidate()
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocodingUnavailableError("Address geocoding is unavailable") from exc

    result = None
    if isinstance(payload, list) and payload:
        first = payload[0]
        try:
            result = {
                "lat": float(first["lat"]),
                "lng": float(first["lon"]),
                "address": str(first.get("display_name", "")),
            }
        except (KeyError, TypeError, ValueError):
            result = None

    _GEOCODING_CACHE[cache_key] = (time.monotonic(), result)
    return result


async def close_geocoding_client() -> None:
    global _HTTP_CLIENT

    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None
