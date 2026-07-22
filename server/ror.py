import re
import time
from typing import Any

import httpx

from .utils import get_config

ROR_API_URL = "https://api.ror.org/v2/organizations"
ROR_CACHE_SECONDS = 60 * 60
ROR_RESULT_LIMIT = 10

_HTTP_CLIENT: httpx.AsyncClient | None = None
_SEARCH_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_RECORD_CACHE: dict[str, dict[str, Any]] = {}


class RorUnavailableError(RuntimeError):
    pass


def _display_name(names: list[dict[str, Any]]) -> str:
    for preferred_type in ("ror_display", "label"):
        for name in names:
            if preferred_type in name.get("types", []):
                return str(name.get("value", "")).strip()
    return str(names[0].get("value", "")).strip() if names else ""


def _name_variants(names: list[dict[str, Any]], display_name: str) -> list[str]:
    variants: list[str] = []
    prioritized_names = sorted(
        names,
        key=lambda name: (
            0 if "acronym" in name.get("types", []) else 1,
            0 if "alias" in name.get("types", []) else 1,
        ),
    )
    for name in prioritized_names:
        value = str(name.get("value", "")).strip()
        if value and value != display_name and value not in variants:
            variants.append(value)
    return variants


def _format_organization(record: dict[str, Any]) -> dict[str, Any] | None:
    names = record.get("names", [])
    display_name = _display_name(names)
    ror_id = str(record.get("id", ""))
    if not display_name or not ror_id.startswith("https://ror.org/"):
        return None

    locations = []
    for location in record.get("locations", []):
        details = location.get("geonames_details") or {}
        city = str(details.get("name", "")).strip()
        country = str(details.get("country_name", "")).strip()
        if city or country:
            formatted_location: dict[str, Any] = {
                "city": city,
                "country": country,
            }
            if isinstance(details.get("lat"), (int, float)):
                formatted_location["lat"] = float(details["lat"])
            if isinstance(details.get("lng"), (int, float)):
                formatted_location["lng"] = float(details["lng"])
            locations.append(formatted_location)

    website = next(
        (
            str(link.get("value", ""))
            for link in record.get("links", [])
            if link.get("type") == "website" and link.get("value")
        ),
        "",
    )

    return {
        "ror_id": ror_id,
        "name": display_name,
        "name_variants": _name_variants(names, display_name),
        "locations": locations,
        "organization_types": [str(value) for value in record.get("types", [])],
        "domains": [str(value) for value in record.get("domains", [])],
        "website": website,
    }


async def search_ror_organizations(query: str) -> list[dict[str, Any]]:
    global _HTTP_CLIENT

    normalized_query = " ".join(query.split())
    cache_key = normalized_query.casefold()
    cached = _SEARCH_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < ROR_CACHE_SECONDS:
        return cached[1]

    headers = {}
    client_id = get_config("ROR_CLIENT_ID", "")
    if client_id:
        headers["Client-Id"] = str(client_id)

    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=8,
            headers={"User-Agent": "last-translation-benchmark/0.0.1"},
        )

    try:
        response = await _HTTP_CLIENT.get(
            ROR_API_URL,
            params={"query": normalized_query},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RorUnavailableError("ROR organization search is unavailable") from exc

    organizations = []
    for item in payload.get("items", []):
        organization = _format_organization(item)
        if organization is not None:
            organizations.append(organization)
        if len(organizations) == ROR_RESULT_LIMIT:
            break

    _SEARCH_CACHE[cache_key] = (time.monotonic(), organizations)
    return organizations


async def get_ror_organization(ror_id: str) -> dict[str, Any]:
    global _HTTP_CLIENT

    if not re.fullmatch(r"https://ror\.org/0[0-9a-z]{8}", ror_id):
        raise RorUnavailableError("Invalid ROR organization ID")
    cached = _RECORD_CACHE.get(ror_id)
    if cached is not None:
        return cached

    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=8,
            headers={"User-Agent": "last-translation-benchmark/0.0.1"},
        )

    record_id = ror_id.rsplit("/", 1)[-1]
    try:
        response = await _HTTP_CLIENT.get(f"{ROR_API_URL}/{record_id}")
        response.raise_for_status()
        organization = _format_organization(response.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise RorUnavailableError("ROR organization lookup is unavailable") from exc

    if organization is None:
        raise RorUnavailableError("ROR returned an invalid organization record")
    _RECORD_CACHE[ror_id] = organization
    return organization


async def close_ror_client() -> None:
    global _HTTP_CLIENT

    if _HTTP_CLIENT is not None and not _HTTP_CLIENT.is_closed:
        await _HTTP_CLIENT.aclose()
    _HTTP_CLIENT = None
