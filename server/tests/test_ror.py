from last_translation_benchmark.ror import _format_organization


def test_format_organization_prefers_ror_display_name():
    result = _format_organization(
        {
            "id": "https://ror.org/02mpq6x41",
            "names": [
                {"value": "UIC", "types": ["acronym"]},
                {
                    "value": "University of Illinois Chicago",
                    "types": ["ror_display", "label"],
                },
            ],
            "locations": [
                {
                    "geonames_details": {
                        "name": "Chicago",
                        "country_name": "United States",
                    }
                }
            ],
            "types": ["education"],
            "domains": ["uic.edu"],
            "links": [{"type": "website", "value": "https://www.uic.edu"}],
        }
    )

    assert result == {
        "ror_id": "https://ror.org/02mpq6x41",
        "name": "University of Illinois Chicago",
        "name_variants": ["UIC"],
        "locations": [{"city": "Chicago", "country": "United States"}],
        "organization_types": ["education"],
        "domains": ["uic.edu"],
        "website": "https://www.uic.edu",
    }


def test_format_organization_rejects_incomplete_records():
    assert _format_organization({"id": "", "names": []}) is None
