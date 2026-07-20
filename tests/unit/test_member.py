"""Unit tests for LinkedIn member URN resolution."""

from __future__ import annotations

import pytest

from app.linkedin.member import MemberUrnError, resolve_member_urn


def test_resolve_member_urn_derives_urn_from_sub() -> None:
    result = resolve_member_urn({"sub": "AaBbCc123", "name": "Jane"})
    assert result == "urn:li:member:AaBbCc123"


def test_resolve_member_urn_strips_whitespace_from_sub() -> None:
    result = resolve_member_urn({"sub": "  user-999  "})
    assert result == "urn:li:member:user-999"


def test_resolve_member_urn_raises_when_sub_is_missing() -> None:
    with pytest.raises(MemberUrnError, match="'sub' claim"):
        resolve_member_urn({"name": "No Sub"})


def test_resolve_member_urn_raises_when_sub_is_empty_string() -> None:
    with pytest.raises(MemberUrnError, match="'sub' claim"):
        resolve_member_urn({"sub": ""})


def test_resolve_member_urn_raises_when_sub_is_whitespace_only() -> None:
    with pytest.raises(MemberUrnError, match="'sub' claim"):
        resolve_member_urn({"sub": "   "})


def test_resolve_member_urn_raises_when_sub_is_not_a_string() -> None:
    with pytest.raises(MemberUrnError, match="'sub' claim"):
        resolve_member_urn({"sub": 12345})
