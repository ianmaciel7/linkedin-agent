"""Encrypted local storage for LinkedIn member profile data."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken

from app.linkedin.models import MemberProfile

logger = logging.getLogger(__name__)

_PROFILE_STORE_VERSION = 1


class LinkedInProfileStoreError(RuntimeError):
    """Base error for LinkedIn profile storage operations."""


class LinkedInProfileStoreConfigurationError(LinkedInProfileStoreError):
    """Raised when profile storage configuration is invalid."""


class LinkedInProfileStoreInvalidRecordError(LinkedInProfileStoreError):
    """Raised when a stored profile cannot be decrypted or parsed."""


class LinkedInProfileStore(Protocol):
    """Protocol for LinkedIn member profile persistence implementations."""

    def load(self) -> MemberProfile | None:
        """Load a previously persisted member profile, or None if absent."""

    def save(self, profile: MemberProfile) -> None:
        """Persist the member profile, replacing any existing record."""

    def clear(self) -> bool:
        """Delete the stored profile file. Returns True if a file was removed."""


class LocalEncryptedProfileStore:
    """Store a LinkedIn member profile in an encrypted local file.

    The encryption key is reused from ``LINKEDIN_TOKEN_ENCRYPTION_KEY`` so no
    additional secret is required.  The file format is versioned JSON encrypted
    with Fernet.
    """

    def __init__(self, path: str, encryption_key: str) -> None:
        self._path = Path(path).expanduser()
        self._fernet = self._build_fernet(encryption_key)

    def load(self) -> MemberProfile | None:
        """Return the stored profile, or None if the file is absent."""
        if not self._path.exists():
            logger.debug("LinkedIn profile store: no file at %s", self._path)
            return None

        try:
            decrypted = self._fernet.decrypt(self._path.read_bytes())
        except (FileNotFoundError, InvalidToken) as exc:
            raise LinkedInProfileStoreInvalidRecordError(
                "Stored LinkedIn profile could not be decrypted"
            ) from exc

        try:
            payload = json.loads(decrypted.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LinkedInProfileStoreInvalidRecordError(
                "Stored LinkedIn profile could not be parsed"
            ) from exc

        if not isinstance(payload, dict):
            raise LinkedInProfileStoreInvalidRecordError(
                "Stored LinkedIn profile payload is invalid"
            )
        if payload.get("version") != _PROFILE_STORE_VERSION:
            raise LinkedInProfileStoreInvalidRecordError(
                "Stored LinkedIn profile version is not supported"
            )

        profile_data = payload.get("profile")
        if not isinstance(profile_data, dict):
            raise LinkedInProfileStoreInvalidRecordError(
                "Stored LinkedIn profile payload is incomplete"
            )

        try:
            return MemberProfile.from_store_dict(profile_data)
        except (KeyError, TypeError, ValueError) as exc:
            raise LinkedInProfileStoreInvalidRecordError(
                "Stored LinkedIn profile data is malformed"
            ) from exc

    def save(self, profile: MemberProfile) -> None:
        """Atomically write the profile to the encrypted file."""
        payload = {
            "version": _PROFILE_STORE_VERSION,
            "profile": profile.to_store_dict(),
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
        logger.debug("LinkedIn profile store: saved to %s", self._path)

    def clear(self) -> bool:
        """Remove the profile file. Returns True if it existed."""
        if not self._path.exists():
            return False
        self._path.unlink()
        logger.debug("LinkedIn profile store: cleared %s", self._path)
        return True

    @staticmethod
    def _build_fernet(encryption_key: str) -> Fernet:
        try:
            return Fernet(encryption_key.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise LinkedInProfileStoreConfigurationError(
                "LINKEDIN_TOKEN_ENCRYPTION_KEY must be a valid Fernet key"
            ) from exc
