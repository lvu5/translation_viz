#!/usr/bin/env python3
"""Build the static dashboard snapshot consumed by the GitHub Pages map."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    "https://last-translation-benchmark.vilda.net/api/public-dashboard"
)
DEFAULT_LOCATIONS = ROOT / "data" / "affiliation_locations.json"
DEFAULT_LOGO_CACHE_MANIFEST = (
    ROOT / "src" / "assets" / "logos" / "cache" / "manifest.json"
)
DEFAULT_OUTPUT = ROOT / "site" / "data" / "dashboard.json"

from affiliation_map import build_affiliation_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch public dashboard data and build a static map snapshot."
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--locations", type=Path, default=DEFAULT_LOCATIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def fetch_dashboard(source: str) -> dict[str, Any]:
    response = httpx.get(
        source,
        headers={"User-Agent": "translation-viz-pages-builder/1.0"},
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()
    dashboard = response.json()
    if not isinstance(dashboard, dict) or not isinstance(dashboard.get("rows"), list):
        raise ValueError("The public dashboard response does not contain a rows list.")
    return dashboard


def build_snapshot(
    dashboard: dict[str, Any],
    locations_path: Path,
    source: str,
) -> dict[str, Any]:
    with locations_path.open(encoding="utf-8") as locations_file:
        location_config = json.load(locations_file)

    if DEFAULT_LOGO_CACHE_MANIFEST.exists():
        with DEFAULT_LOGO_CACHE_MANIFEST.open(encoding="utf-8") as cache_file:
            cached_logo_files = json.load(cache_file)
        if not isinstance(cached_logo_files, dict):
            raise ValueError("The affiliation logo cache manifest must be an object.")
        manual_logo_files = location_config.get("logo_files", {})
        location_config["logo_files"] = {
            **cached_logo_files,
            **manual_logo_files,
        }

    affiliation_map = build_affiliation_map(dashboard, location_config)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": source,
        "total_submissions": int(dashboard.get("total_submissions", 0)),
        "total_authors": int(dashboard.get("total_authors", 0)),
        "affiliation_places": affiliation_map["places"],
        "affiliation_map_meta": {
            "mapped_authors": affiliation_map["mapped_authors"],
            "mapped_accepted": affiliation_map["mapped_accepted"],
            "omitted": affiliation_map["omitted"],
        },
    }


def main() -> None:
    args = parse_args()
    dashboard = fetch_dashboard(args.source)
    snapshot = build_snapshot(dashboard, args.locations, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(snapshot['affiliation_places'])} map locations "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
