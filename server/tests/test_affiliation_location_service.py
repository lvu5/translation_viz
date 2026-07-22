import asyncio

import last_translation_benchmark.affiliation_location_service as service


def test_discovery_saves_geocoded_candidate_for_admin_review(monkeypatch):
    saved = []

    async def no_existing(ror_id):
        return None

    async def fake_ror(ror_id):
        return {
            "ror_id": ror_id,
            "name": "Example University",
            "name_variants": ["Example U"],
            "locations": [
                {
                    "city": "Example City",
                    "country": "Example Country",
                    "lat": 10.0,
                    "lng": 20.0,
                }
            ],
            "domains": ["example.edu"],
            "website": "https://example.edu",
        }

    async def fake_geocode(query):
        return {
            "lat": 10.25,
            "lng": 20.25,
            "address": "1 Example Street, Example City",
        }

    async def save(record):
        saved.append(record)

    monkeypatch.setattr(service, "get_affiliation_location_review", no_existing)
    monkeypatch.setattr(service, "get_ror_organization", fake_ror)
    monkeypatch.setattr(service, "geocode_location", fake_geocode)
    monkeypatch.setattr(service, "save_affiliation_location_review", save)

    result = asyncio.run(
        service.discover_affiliation_location(
            "Example U",
            "https://ror.org/012345678",
        )
    )

    assert result is not None
    assert result["status"] == "pending"
    assert result["source"] == "nominatim"
    assert result["precision"] == "exact"
    assert result["address"] == "1 Example Street, Example City"
    assert result["aliases"] == ["Example U"]
    assert saved == [result]
