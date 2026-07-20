from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.linkedin.models import PostMetadata
from app.linkedin.post_store import (
    LinkedInPostStoreInvalidRecordError,
    LocalEncryptedPostStore,
)


def _store(tmp_path) -> LocalEncryptedPostStore:
    return LocalEncryptedPostStore(
        str(tmp_path / "posts.enc"),
        Fernet.generate_key().decode(),
    )


def test_post_store_save_and_load(tmp_path) -> None:
    store = _store(tmp_path)
    posts = [
        PostMetadata(
            post_urn="urn:li:share:1",
            created_at=1,
            text_excerpt="hello",
            visibility="PUBLIC",
        )
    ]

    store.save(posts)

    assert store.load() == posts


def test_post_store_clear(tmp_path) -> None:
    store = _store(tmp_path)
    store.save([])

    assert store.clear() is True
    assert store.load() == []


def test_post_store_mark_unavailable(tmp_path) -> None:
    store = _store(tmp_path)
    store.save(
        [
            PostMetadata(
                post_urn="urn:li:share:1",
                created_at=1,
                text_excerpt="hello",
                visibility="PUBLIC",
            )
        ]
    )

    assert store.mark_unavailable("urn:li:share:1") is True
    assert store.load()[0].unavailable is True


def test_post_store_invalid_payload_raises(tmp_path) -> None:
    store = _store(tmp_path)
    store._path.write_bytes(b"invalid-token")  # type: ignore[attr-defined]

    with pytest.raises(LinkedInPostStoreInvalidRecordError):
        store.load()
