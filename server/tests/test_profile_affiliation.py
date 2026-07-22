import pytest
from fastapi import HTTPException

from last_translation_benchmark.models import ProfileReq
from last_translation_benchmark.routers import (
    normalize_profile_affiliation,
    normalize_profile_affiliations,
    user_affiliations,
)


def profile(affiliation: str, ror_id: str | None = None) -> ProfileReq:
    return ProfileReq(
        name="Example Contributor",
        affiliation=affiliation,
        affiliation_ror_id=ror_id,
        email="example@example.com",
        credit_consent=True,
        notification_consent=True,
    )


def test_independent_affiliation_is_canonicalized_without_ror():
    assert normalize_profile_affiliation(
        profile(" independent ", "https://ror.org/012345678")
    ) == ("Independent researcher", None)


def test_other_affiliation_is_preserved_without_ror():
    assert normalize_profile_affiliation(profile("Community Translation Lab")) == (
        "Community Translation Lab",
        None,
    )


def test_affiliation_cannot_be_blank():
    with pytest.raises(HTTPException) as error:
        normalize_profile_affiliation(profile("  "))

    assert error.value.status_code == 400


def test_multiple_affiliations_are_normalized_in_order():
    affiliations = [
        {
            "name": "Primary University",
            "ror_id": "https://ror.org/012345678",
            "kind": "ror",
        },
        {
            "name": "Second Institute",
            "ror_id": "https://ror.org/087654321",
            "kind": "ror",
        },
    ]
    request = ProfileReq(
        name="Example Contributor",
        affiliation="Primary University",
        affiliation_ror_id="https://ror.org/012345678",
        affiliations=affiliations,
        email="example@example.com",
        credit_consent=True,
        notification_consent=True,
    )

    assert normalize_profile_affiliations(request) == affiliations


def test_independent_cannot_be_combined_with_an_affiliation():
    request = ProfileReq(
        name="Example Contributor",
        affiliation="Independent researcher",
        affiliation_ror_id=None,
        affiliations=[
            {
                "name": "Independent researcher",
                "ror_id": None,
                "kind": "independent",
            },
            {"name": "Community Lab", "ror_id": None, "kind": "other"},
        ],
        email="example@example.com",
        credit_consent=True,
        notification_consent=True,
    )

    with pytest.raises(HTTPException) as error:
        normalize_profile_affiliations(request)

    assert error.value.status_code == 400


def test_legacy_user_affiliation_is_exposed_as_an_array():
    assert user_affiliations(
        {
            "affiliation": "Example University",
            "affiliation_ror_id": "https://ror.org/012345678",
        }
    ) == [
        {
            "name": "Example University",
            "ror_id": "https://ror.org/012345678",
            "kind": "ror",
        }
    ]
