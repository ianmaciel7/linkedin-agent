from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.linkedin.models import MemberProfile
from app.linkedin.profile_store import (
    LinkedInProfileStoreInvalidRecordError,
    LocalEncryptedProfileStore,
)


def test_profile_store_save_and_load(tmp_path) -> None:
    store = LocalEncryptedProfileStore(
        str(tmp_path / "profile.enc"),
        Fernet.generate_key().decode(),
    )
    profile = MemberProfile(
        member_urn="urn:li:member:abc123",
        sub="abc123",
        name="Avery Example",
        email="avery@example.com",
        user_supplied={"headline": "Builder"},
    )

    store.save(profile)

    assert store.load() == profile


def test_profile_store_load_missing_file_returns_none(tmp_path) -> None:
    store = LocalEncryptedProfileStore(
        str(tmp_path / "profile.enc"),
        Fernet.generate_key().decode(),
    )

    assert store.load() is None


def test_profile_store_load_rejects_invalid_payload(tmp_path) -> None:
    store = LocalEncryptedProfileStore(
        str(tmp_path / "profile.enc"),
        Fernet.generate_key().decode(),
    )
    store._path.write_bytes(b"invalid-token")  # type: ignore[attr-defined]

    with pytest.raises(LinkedInProfileStoreInvalidRecordError):
        store.load()
