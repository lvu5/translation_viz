from last_translation_benchmark.affiliation_map import (
    build_affiliation_map,
    load_affiliation_locations,
    merge_affiliation_location_reviews,
)


def test_build_affiliation_map_canonicalizes_and_groups_rows():
    dashboard = {
        "rows": [
            {
                "name": "Ada",
                "affiliation": "UIC",
                "affiliation_ror_id": "https://ror.org/02mpq6x41",
                "accepted_submissions": 3,
            },
            {
                "name": "Grace",
                "affiliation": "University of Illinois Chicago",
                "affiliation_ror_id": "https://ror.org/02mpq6x41",
                "accepted_submissions": 2,
            },
            {
                "name": "Unknown",
                "affiliation": "Unmapped Lab",
                "affiliation_ror_id": None,
                "accepted_submissions": 1,
            },
        ]
    }
    locations = {
        "aliases": {"UIC": "University of Illinois Chicago"},
        "logo_domains": {"University of Illinois Chicago": "uic.edu"},
        "locations": {
            "University of Illinois Chicago": {
                "lat": 41.8708,
                "lng": -87.6505,
                "city": "Chicago",
                "country": "United States",
            }
        },
    }

    result = build_affiliation_map(dashboard, locations)

    assert len(result["places"]) == 1
    affiliation = result["places"][0]["affiliations"][0]
    assert affiliation["name"] == "University of Illinois Chicago"
    assert affiliation["search_terms"] == ["UIC"]
    assert affiliation["accepted"] == 5
    assert affiliation["authors"] == [
        {"name": "Ada", "accepted": 3},
        {"name": "Grace", "accepted": 2},
    ]
    assert result["mapped_authors"] == 2
    assert result["mapped_accepted"] == 5
    assert result["omitted"][0]["affiliation"] == "Unmapped Lab"


def test_latest_live_affiliations_are_in_location_registry():
    dashboard = {
        "rows": [
            {
                "name": "Author One",
                "affiliation": "University of Luxembourg",
                "accepted_submissions": 9,
            },
            {
                "name": "Author Two",
                "affiliation": "Research Center for Linguistics at NOVA University Lisbon",
                "accepted_submissions": 3,
            },
            {
                "name": "Author Three",
                "affiliation": "Centro de Investigaciones Históricas, Antropológicas y Culturales (CIHAC -AIP)",
                "accepted_submissions": 1,
            },
            {
                "name": "Author Four",
                "affiliation": "DFKI GmbH and BSC-CNS",
                "accepted_submissions": 1,
            },
        ]
    }

    result = build_affiliation_map(dashboard, load_affiliation_locations())

    assert len(result["places"]) == 4
    assert result["mapped_authors"] == 4
    assert result["mapped_accepted"] == 14
    assert result["omitted"] == []


def test_pending_ror_location_is_mapped_as_provisional():
    config = merge_affiliation_location_reviews(
        {"aliases": {}, "logo_domains": {}, "locations": {}},
        [
            {
                "ror_id": "https://ror.org/012345678",
                "affiliation_name": "Example University",
                "aliases": ["Example U"],
                "lat": 10.5,
                "lng": 20.5,
                "city": "Example City",
                "country": "Example Country",
                "address": "1 Example Street",
                "logo_domain": "example.edu",
                "website": "https://example.edu",
                "precision": "exact",
                "status": "pending",
            }
        ],
    )
    dashboard = {
        "rows": [
            {
                "name": "Ada",
                "affiliation": "A name that does not match",
                "affiliation_ror_id": "https://ror.org/012345678",
                "accepted_submissions": 2,
            }
        ]
    }

    result = build_affiliation_map(dashboard, config)

    affiliation = result["places"][0]["affiliations"][0]
    assert affiliation["name"] == "Example University"
    assert affiliation["location_status"] == "pending"
    assert affiliation["address"] == "1 Example Street"
    assert result["omitted"] == []


def test_each_submission_is_credited_to_every_affiliation():
    dashboard = {
        "rows": [
            {
                "name": "Ada",
                "affiliation": "University One; University Two",
                "affiliation_ror_id": "https://ror.org/012345678",
                "affiliations": [
                    {
                        "name": "University One",
                        "ror_id": "https://ror.org/012345678",
                        "kind": "ror",
                    },
                    {
                        "name": "University Two",
                        "ror_id": "https://ror.org/087654321",
                        "kind": "ror",
                    },
                ],
                "accepted_submissions": 3,
            }
        ]
    }
    locations = {
        "aliases": {},
        "logo_domains": {},
        "ror_ids": {
            "https://ror.org/012345678": "University One",
            "https://ror.org/087654321": "University Two",
        },
        "locations": {
            "University One": {
                "lat": 10.0,
                "lng": 20.0,
                "city": "City One",
                "country": "Country",
            },
            "University Two": {
                "lat": 30.0,
                "lng": 40.0,
                "city": "City Two",
                "country": "Country",
            },
        },
    }

    result = build_affiliation_map(dashboard, locations)

    assert len(result["places"]) == 2
    assert {place["accepted"] for place in result["places"]} == {3}
    assert result["mapped_authors"] == 1
    assert result["mapped_accepted"] == 6
