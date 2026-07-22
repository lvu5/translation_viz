import json
from functools import lru_cache
from pathlib import Path
from typing import Any

AFFILIATION_LOCATIONS_PATH = Path(__file__).with_name("affiliation_locations.json")


@lru_cache(maxsize=1)
def load_affiliation_locations() -> dict[str, Any]:
    with AFFILIATION_LOCATIONS_PATH.open(encoding="utf-8") as locations_file:
        return json.load(locations_file)


def merge_affiliation_location_reviews(
    base_config: dict[str, Any],
    reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    config = {
        **base_config,
        "aliases": dict(base_config.get("aliases", {})),
        "logo_domains": dict(base_config.get("logo_domains", {})),
        "locations": dict(base_config.get("locations", {})),
        "ror_ids": dict(base_config.get("ror_ids", {})),
    }

    for review in reviews:
        if review.get("status") not in {"pending", "approved"}:
            continue
        canonical_name = str(review.get("affiliation_name", "")).strip()
        ror_id = str(review.get("ror_id", "")).strip()
        if not canonical_name or not ror_id:
            continue

        config["ror_ids"][ror_id] = canonical_name
        for alias in review.get("aliases", []):
            alias = str(alias).strip()
            if alias and alias != canonical_name:
                config["aliases"][alias] = canonical_name

        if review.get("logo_domain"):
            config["logo_domains"][canonical_name] = review["logo_domain"]

        has_static_location = canonical_name in config["locations"]
        if has_static_location and review.get("status") != "approved":
            continue
        if not isinstance(review.get("lat"), (int, float)) or not isinstance(
            review.get("lng"), (int, float)
        ):
            continue

        config["locations"][canonical_name] = {
            "lat": float(review["lat"]),
            "lng": float(review["lng"]),
            "city": str(review.get("city", "")),
            "country": str(review.get("country", "")),
            "precision": review.get("precision", "city"),
            "location_status": review.get("status", "pending"),
            "address": str(review.get("address", "")),
            "website": str(review.get("website", "")),
            "ror_id": ror_id,
        }

    return config


def build_affiliation_map(
    dashboard: dict[str, Any],
    location_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = location_config or load_affiliation_locations()
    aliases = config.get("aliases", {})
    logo_domains = config.get("logo_domains", {})
    locations = config.get("locations", {})
    ror_ids = config.get("ror_ids", {})

    search_terms_by_name: dict[str, list[str]] = {}
    for alias, canonical in aliases.items():
        search_terms_by_name.setdefault(canonical, []).append(alias)

    affiliations: dict[str, dict[str, Any]] = {}
    omitted: list[dict[str, Any]] = []

    mapped_rows: set[int] = set()
    for row_index, row in enumerate(dashboard.get("rows", [])):
        accepted = int(row.get("accepted_submissions", 0))
        row_affiliations = row.get("affiliations")
        if not isinstance(row_affiliations, list) or not row_affiliations:
            row_affiliations = [
                {
                    "name": row.get("affiliation", ""),
                    "ror_id": row.get("affiliation_ror_id"),
                    "kind": "other",
                }
            ]

        seen_canonical_names: set[str] = set()
        for row_affiliation in row_affiliations:
            if not isinstance(row_affiliation, dict):
                continue
            original_name = str(row_affiliation.get("name", "")).strip()
            row_ror_id = str(row_affiliation.get("ror_id") or "")
            kind = str(row_affiliation.get("kind", ""))
            if kind == "independent" or original_name.casefold() in {
                "independent",
                "independent researcher",
            }:
                continue
            canonical_name = ror_ids.get(
                row_ror_id,
                aliases.get(original_name, original_name),
            )
            if canonical_name in seen_canonical_names:
                continue
            seen_canonical_names.add(canonical_name)
            location = locations.get(canonical_name)

            if not canonical_name or location is None:
                omitted.append(
                    {
                        "affiliation": original_name,
                        "affiliation_ror_id": row_affiliation.get("ror_id"),
                        "author": row.get("name", ""),
                        "accepted": accepted,
                    }
                )
                continue

            mapped_rows.add(row_index)
            affiliation = affiliations.setdefault(
                canonical_name,
                {
                    "name": canonical_name,
                    "search_terms": search_terms_by_name.get(canonical_name, []),
                    "logo_domain": logo_domains.get(canonical_name, ""),
                    "location_status": location.get("location_status", "approved"),
                    "precision": location.get("precision", "exact"),
                    "address": location.get("address", ""),
                    "website": location.get("website", ""),
                    "ror_id": location.get("ror_id", row_ror_id),
                    **location,
                    "accepted": 0,
                    "authors": [],
                },
            )
            affiliation["accepted"] += accepted
            affiliation["authors"].append(
                {"name": row.get("name", ""), "accepted": accepted}
            )

    places_by_coordinate: dict[tuple[float, float], dict[str, Any]] = {}
    for affiliation in affiliations.values():
        affiliation["authors"].sort(
            key=lambda author: (-author["accepted"], author["name"])
        )
        coordinate = (affiliation["lat"], affiliation["lng"])
        place = places_by_coordinate.setdefault(
            coordinate,
            {
                "lat": affiliation["lat"],
                "lng": affiliation["lng"],
                "city": affiliation["city"],
                "country": affiliation["country"],
                "precision": affiliation.get("precision", "exact"),
                "accepted": 0,
                "affiliations": [],
            },
        )
        place["accepted"] += affiliation["accepted"]
        place["affiliations"].append(
            {
                "name": affiliation["name"],
                "search_terms": affiliation["search_terms"],
                "logo_domain": affiliation["logo_domain"],
                "location_status": affiliation["location_status"],
                "precision": affiliation["precision"],
                "address": affiliation["address"],
                "website": affiliation["website"],
                "ror_id": affiliation["ror_id"],
                "accepted": affiliation["accepted"],
                "authors": affiliation["authors"],
            }
        )

    places = list(places_by_coordinate.values())
    for place in places:
        place["affiliations"].sort(
            key=lambda affiliation: (
                -affiliation["accepted"],
                affiliation["name"],
            )
        )
    places.sort(key=lambda place: (-place["accepted"], place["city"]))

    return {
        "places": places,
        "mapped_authors": len(mapped_rows),
        "mapped_accepted": sum(place["accepted"] for place in places),
        "omitted": omitted,
    }
