import asyncio
from datetime import datetime, timezone
from typing import Any

from .affiliation_map import (
    build_affiliation_map,
    load_affiliation_locations,
    merge_affiliation_location_reviews,
)
from .db import (
    get_affiliation_location_review,
    get_affiliation_location_reviews,
    save_affiliation_location_review,
)
from .geocoding import GeocodingUnavailableError, geocode_location
from .ror import RorUnavailableError, get_ror_organization


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _first_ror_location(organization: dict[str, Any]) -> dict[str, Any]:
    locations = organization.get("locations", [])
    return locations[0] if locations else {}


async def discover_affiliation_location(
    affiliation_name: str,
    ror_id: str,
) -> dict[str, Any] | None:
    base_config = load_affiliation_locations()
    submitted_canonical_name = base_config.get("aliases", {}).get(
        affiliation_name,
        affiliation_name,
    )
    if submitted_canonical_name in base_config.get("locations", {}):
        return None

    existing = await get_affiliation_location_review(ror_id)
    if existing is not None:
        aliases = list(existing.get("aliases", []))
        if affiliation_name and affiliation_name not in aliases:
            aliases.append(affiliation_name)
            existing["aliases"] = aliases
            existing["updated_at"] = _now()
            await save_affiliation_location_review(existing)
        return existing

    try:
        organization = await get_ror_organization(ror_id)
    except RorUnavailableError:
        return None

    organization_canonical_name = base_config.get("aliases", {}).get(
        organization["name"],
        organization["name"],
    )
    static_location = base_config.get("locations", {}).get(organization_canonical_name)
    if static_location is not None:
        aliases = [
            value
            for value in [
                affiliation_name,
                organization["name"],
                *organization.get("name_variants", []),
            ]
            if value and value != organization_canonical_name
        ]
        record = {
            "ror_id": ror_id,
            "affiliation_name": organization_canonical_name,
            "aliases": list(dict.fromkeys(aliases)),
            "address": static_location.get("address", ""),
            "city": static_location["city"],
            "country": static_location["country"],
            "lat": static_location["lat"],
            "lng": static_location["lng"],
            "logo_domain": base_config.get("logo_domains", {}).get(
                organization_canonical_name,
                next(iter(organization.get("domains", [])), ""),
            ),
            "website": organization.get("website", ""),
            "precision": static_location.get("precision", "exact"),
            "status": "approved",
            "source": "reviewed_registry",
            "created_at": _now(),
            "updated_at": _now(),
            "reviewed_by": "registry",
        }
        await save_affiliation_location_review(record)
        return record

    ror_location = _first_ror_location(organization)
    city = str(ror_location.get("city", ""))
    country = str(ror_location.get("country", ""))
    lat = ror_location.get("lat")
    lng = ror_location.get("lng")
    address = ""
    precision = "city"
    source = "ror"

    geocode_query = ", ".join(
        value for value in [organization.get("name", ""), city, country] if value
    )
    try:
        candidate = await geocode_location(geocode_query)
    except GeocodingUnavailableError:
        candidate = None
    if candidate is not None:
        lat = candidate["lat"]
        lng = candidate["lng"]
        address = candidate["address"]
        precision = "exact"
        source = "nominatim"

    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return None

    aliases = [
        value
        for value in [affiliation_name, *organization.get("name_variants", [])]
        if value and value != organization["name"]
    ]
    record = {
        "ror_id": ror_id,
        "affiliation_name": organization["name"],
        "aliases": list(dict.fromkeys(aliases)),
        "address": address,
        "city": city,
        "country": country,
        "lat": float(lat),
        "lng": float(lng),
        "logo_domain": next(iter(organization.get("domains", [])), ""),
        "website": organization.get("website", ""),
        "precision": precision,
        "status": "pending",
        "source": source,
        "created_at": _now(),
        "updated_at": _now(),
        "reviewed_by": "",
    }
    await save_affiliation_location_review(record)
    return record


async def build_dashboard_affiliation_map(
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    reviews = await get_affiliation_location_reviews()
    config = merge_affiliation_location_reviews(load_affiliation_locations(), reviews)
    affiliation_map = build_affiliation_map(dashboard, config)

    missing_ror_affiliations = {
        (str(item["affiliation"]), str(item["affiliation_ror_id"]))
        for item in affiliation_map["omitted"]
        if item.get("affiliation_ror_id")
    }
    if missing_ror_affiliations:
        await asyncio.gather(
            *(
                discover_affiliation_location(affiliation, ror_id)
                for affiliation, ror_id in missing_ror_affiliations
            )
        )
        reviews = await get_affiliation_location_reviews()
        config = merge_affiliation_location_reviews(
            load_affiliation_locations(),
            reviews,
        )
        affiliation_map = build_affiliation_map(dashboard, config)

    return affiliation_map


async def geocode_affiliation_review(
    review: dict[str, Any],
    address: str,
    city: str,
    country: str,
) -> dict[str, Any]:
    query = ", ".join(
        value
        for value in [address, review.get("affiliation_name", ""), city, country]
        if value
    )
    candidate = await geocode_location(query)
    if candidate is None:
        raise GeocodingUnavailableError("No location matched that address")

    review.update(
        {
            "address": address or candidate["address"],
            "city": city or review.get("city", ""),
            "country": country or review.get("country", ""),
            "lat": candidate["lat"],
            "lng": candidate["lng"],
            "precision": "exact" if address else "city",
            "status": "pending",
            "source": "nominatim",
            "updated_at": _now(),
        }
    )
    await save_affiliation_location_review(review)
    return review
