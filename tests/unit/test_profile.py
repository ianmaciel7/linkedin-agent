from __future__ import annotations

from app.linkedin.models import MemberProfile
from app.linkedin.profile import assemble_profile


def test_assemble_profile_full_oidc_merge() -> None:
    profile = assemble_profile(
        {
            "sub": "abc123",
            "name": "Avery Example",
            "given_name": "Avery",
            "family_name": "Example",
            "email": "avery@example.com",
        }
    )

    assert profile.member_urn == "urn:li:member:abc123"
    assert profile.email == "avery@example.com"


def test_assemble_profile_partial_oidc_merge() -> None:
    profile = assemble_profile({"sub": "abc123", "name": "Avery Example"})

    assert profile.name == "Avery Example"
    assert profile.email is None


def test_assemble_profile_uses_user_supplied_mapping() -> None:
    profile = assemble_profile(
        {"sub": "abc123", "name": "Avery Example"},
        user_supplied={"headline": "Builder", "location": "Sao Paulo"},
    )

    assert profile.user_supplied == {
        "headline": "Builder",
        "location": "Sao Paulo",
    }


def test_assemble_profile_carries_forward_stored_user_supplied_data() -> None:
    stored = MemberProfile(
        member_urn="urn:li:member:abc123",
        sub="abc123",
        user_supplied={"industry": "Software"},
    )

    profile = assemble_profile({"sub": "abc123"}, stored=stored)

    assert profile.user_supplied == {"industry": "Software"}
