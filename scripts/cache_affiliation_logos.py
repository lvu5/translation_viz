#!/usr/bin/env python3
"""Cache affiliation favicons as stable, version-controlled map assets."""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "data" / "affiliation_locations.json"
DEFAULT_CACHE_DIR = ROOT / "src" / "assets" / "logos" / "cache"
DEFAULT_MANIFEST = DEFAULT_CACHE_DIR / "manifest.json"
FAVICON_ENDPOINT = "https://www.google.com/s2/favicons"
MAX_LOGO_BYTES = 2 * 1024 * 1024
CONTENT_TYPE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/vnd.microsoft.icon": ".ico",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download configured affiliation favicons once and record stable local "
            "paths for the map build."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--affiliation",
        action="append",
        default=[],
        help="Cache only this canonical affiliation or alias; may be repeated.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace existing automatic cache entries for selected affiliations.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with an error if any requested logo cannot be downloaded.",
    )
    return parser.parse_args()


def load_object(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    if missing_ok and not path.exists():
        return {}
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:64] or "affiliation"


def cache_filename(affiliation: str, extension: str) -> str:
    digest = hashlib.sha256(affiliation.encode("utf-8")).hexdigest()[:10]
    return f"{slugify(affiliation)}-{digest}{extension}"


def site_asset_path(filename: str) -> str:
    return f"assets/logos/cache/{filename}"


def source_asset_path(site_path: str, cache_dir: Path) -> Path:
    prefix = "assets/logos/cache/"
    if not site_path.startswith(prefix):
        raise ValueError(f"Unexpected cached logo path: {site_path}")
    return cache_dir / Path(site_path).name


def extension_for(content_type: str) -> str:
    media_type = content_type.partition(";")[0].strip().lower()
    extension = CONTENT_TYPE_EXTENSIONS.get(media_type)
    if extension is None:
        raise ValueError(f"Unsupported logo content type: {content_type or 'missing'}")
    return extension


def fetch_logo(client: httpx.Client, domain: str) -> tuple[bytes, str]:
    website = f"https://{domain.strip().rstrip('/')}"
    response = client.get(
        FAVICON_ENDPOINT,
        params={"domain_url": website, "sz": "128"},
    )
    response.raise_for_status()
    if not response.content:
        raise ValueError("The favicon service returned an empty response.")
    if len(response.content) > MAX_LOGO_BYTES:
        raise ValueError("The favicon response exceeded the 2 MB safety limit.")
    return response.content, extension_for(response.headers.get("content-type", ""))


def write_manifest(path: Path, manifest: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    config = load_object(args.config)
    domains = config.get("logo_domains", {})
    manual_files = config.get("logo_files", {})
    aliases = config.get("aliases", {})
    if not isinstance(domains, dict) or not isinstance(manual_files, dict):
        raise ValueError("logo_domains and logo_files must be JSON objects.")

    manifest_data = load_object(args.manifest, missing_ok=True)
    manifest = {
        str(name): str(path)
        for name, path in manifest_data.items()
        if isinstance(name, str) and isinstance(path, str)
    }

    if args.affiliation:
        selected = [str(aliases.get(name, name)) for name in args.affiliation]
        unknown = sorted({name for name in selected if name not in domains})
        if unknown:
            raise ValueError(
                "No logo domain is configured for: " + ", ".join(unknown)
            )
    else:
        selected = list(domains)

    targets = list(dict.fromkeys(selected))
    downloaded = 0
    cached = 0
    manual = 0
    errors: list[str] = []
    manifest_changed = False
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(
        headers={"User-Agent": "translation-viz-logo-cache/1.0"},
        follow_redirects=True,
        timeout=30,
    ) as client:
        for affiliation in targets:
            if affiliation in manual_files:
                manual += 1
                continue

            existing_site_path = manifest.get(affiliation)
            existing_source_path = (
                source_asset_path(existing_site_path, args.cache_dir)
                if existing_site_path
                else None
            )
            if (
                not args.refresh
                and existing_source_path is not None
                and existing_source_path.is_file()
            ):
                cached += 1
                continue

            try:
                content, extension = fetch_logo(client, str(domains[affiliation]))
                filename = cache_filename(affiliation, extension)
                destination = args.cache_dir / filename
                destination.write_bytes(content)
                new_site_path = site_asset_path(filename)

                if (
                    existing_source_path is not None
                    and existing_source_path != destination
                    and existing_source_path.is_file()
                ):
                    existing_source_path.unlink()

                if manifest.get(affiliation) != new_site_path:
                    manifest[affiliation] = new_site_path
                    manifest_changed = True
                downloaded += 1
            except (httpx.HTTPError, OSError, ValueError) as error:
                errors.append(f"{affiliation}: {error}")

    if manifest_changed or (downloaded and not args.manifest.exists()):
        write_manifest(args.manifest, manifest)

    print(
        f"Logo cache: {downloaded} downloaded, {cached} already cached, "
        f"{manual} manual, {len(errors)} failed."
    )
    for error in errors:
        print(f"warning: {error}")
    if args.strict and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
