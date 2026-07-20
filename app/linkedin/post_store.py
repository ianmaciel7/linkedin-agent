"""Encrypted local storage for LinkedIn post metadata."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken

from app.linkedin.models import PostMetadata, PostStoreRecord

logger = logging.getLogger(__name__)

_POST_STORE_VERSION = 1


class LinkedInPostStoreError(RuntimeError):
    """Base error for LinkedIn post storage operations."""


class LinkedInPostStoreConfigurationError(LinkedInPostStoreError):
    """Raised when post storage configuration is invalid."""


class LinkedInPostStoreInvalidRecordError(LinkedInPostStoreError):
    """Raised when a stored post index cannot be decrypted or parsed."""


class LinkedInPostStore(Protocol):
    """Protocol for LinkedIn post metadata persistence implementations."""

    def load(self) -> list[PostMetadata]:
        """Return the stored post metadata list, or an empty list if absent."""

    def save(self, posts: list[PostMetadata]) -> None:
        """Persist the post metadata list, replacing any existing record."""

    def clear(self) -> bool:
        """Delete the stored post index file. Returns True if a file was removed."""

    def mark_unavailable(self, post_urn: str) -> bool:
        """Mark a stored post as unavailable. Returns True if it was found."""


class LocalEncryptedPostStore:
    """Store a LinkedIn post metadata index in an encrypted local file.

    The full index is replaced atomically on each write.  Individual post
    records are never logged or surfaced in error messages.
    """

    def __init__(self, path: str, encryption_key: str) -> None:
        self._path = Path(path).expanduser()
        self._fernet = self._build_fernet(encryption_key)

    def load(self) -> list[PostMetadata]:
        """Return stored posts, or an empty list when no file exists."""
        if not self._path.exists():
            logger.debug("LinkedIn post store: no file at %s", self._path)
            return []

        try:
            decrypted = self._fernet.decrypt(self._path.read_bytes())
        except (FileNotFoundError, InvalidToken) as exc:
            raise LinkedInPostStoreInvalidRecordError(
                "Stored LinkedIn post index could not be decrypted"
            ) from exc

        try:
            payload = json.loads(decrypted.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LinkedInPostStoreInvalidRecordError(
                "Stored LinkedIn post index could not be parsed"
            ) from exc

        if not isinstance(payload, dict):
            raise LinkedInPostStoreInvalidRecordError(
                "Stored LinkedIn post index payload is invalid"
            )
        if payload.get("version") != _POST_STORE_VERSION:
            raise LinkedInPostStoreInvalidRecordError(
                "Stored LinkedIn post index version is not supported"
            )

        try:
            return list(PostStoreRecord.from_store_dict(payload).posts)
        except (KeyError, TypeError, ValueError) as exc:
            raise LinkedInPostStoreInvalidRecordError(
                "Stored LinkedIn post index 'posts' field is invalid"
            ) from exc

    def save(self, posts: list[PostMetadata]) -> None:
        """Atomically replace the stored post index."""
        payload = {
            "version": _POST_STORE_VERSION,
            **PostStoreRecord(posts=tuple(posts)).to_store_dict(),
        }
        encrypted = self._fernet.encrypt(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=self._path.parent,
            delete=False,
        ) as handle:
            handle.write(encrypted)
            temp_path = Path(handle.name)

        os.chmod(temp_path, 0o600)
        temp_path.replace(self._path)
        logger.debug(
            "LinkedIn post store: saved %d posts to %s", len(posts), self._path
        )

    def clear(self) -> bool:
        """Remove the post index file. Returns True if it existed."""
        if not self._path.exists():
            return False
        self._path.unlink()
        logger.debug("LinkedIn post store: cleared %s", self._path)
        return True

    def mark_unavailable(self, post_urn: str) -> bool:
        """Mark a stored post as unavailable and re-persist.

        Returns True if the post was found in the store.
        """
        posts = self.load()
        found = False
        updated: list[PostMetadata] = []
        for post in posts:
            if post.post_urn == post_urn:
                found = True
                # frozen dataclass — rebuild with unavailable=True
                updated.append(
                    PostMetadata(
                        post_urn=post.post_urn,
                        created_at=post.created_at,
                        text_excerpt=post.text_excerpt,
                        visibility=post.visibility,
                        permalink=post.permalink,
                        like_count=post.like_count,
                        comment_count=post.comment_count,
                        unavailable=True,
                    )
                )
            else:
                updated.append(post)
        if found:
            self.save(updated)
        return found

    @staticmethod
    def _build_fernet(encryption_key: str) -> Fernet:
        try:
            return Fernet(encryption_key.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise LinkedInPostStoreConfigurationError(
                "LINKEDIN_TOKEN_ENCRYPTION_KEY must be a valid Fernet key"
            ) from exc
