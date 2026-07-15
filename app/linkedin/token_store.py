"""Encrypted local storage for LinkedIn OAuth credentials."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from cryptography.fernet import Fernet, InvalidToken
from google.adk.auth.auth_credential import OAuth2Auth

from app.settings import LinkedInOAuthSettings, LinkedInTokenStorageSettings

logger = logging.getLogger(__name__)

_TOKEN_STORE_VERSION = 1


class LinkedInTokenStoreError(RuntimeError):
    """Base error for secure LinkedIn token storage operations."""


class LinkedInTokenStoreConfigurationError(LinkedInTokenStoreError):
    """Raised when secure token storage configuration is invalid."""


class LinkedInTokenStoreInvalidRecordError(LinkedInTokenStoreError):
    """Raised when a stored credential cannot be decrypted or parsed."""


class LinkedInTokenStoreExpiredCredentialError(LinkedInTokenStoreError):
    """Raised when a stored credential is present but expired."""


@dataclass(frozen=True, slots=True)
class StoredLinkedInCredential:
    """Minimal LinkedIn OAuth credential fields needed for reuse."""

    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    expires_in: int | None = None

    def to_oauth2(self) -> OAuth2Auth:
        """Convert the stored credential into ADK's OAuth2 model."""

        return OAuth2Auth(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            expires_at=self.expires_at,
            expires_in=self.expires_in,
        )

    @classmethod
    def from_oauth2(cls, credential: OAuth2Auth) -> StoredLinkedInCredential:
        """Extract the minimal reusable fields from an OAuth2 credential."""

        access_token = (credential.access_token or "").strip()
        if not access_token:
            raise LinkedInTokenStoreInvalidRecordError(
                "LinkedIn credential did not include an access token"
            )

        expires_at = credential.expires_at
        expires_in = credential.expires_in
        return cls(
            access_token=access_token,
            refresh_token=(credential.refresh_token or "").strip() or None,
            expires_at=float(expires_at) if expires_at is not None else None,
            expires_in=expires_in,
        )


class LinkedInTokenStore(Protocol):
    """Protocol for LinkedIn credential persistence implementations."""

    def load(self, oauth: LinkedInOAuthSettings) -> StoredLinkedInCredential | None:
        """Load a stored credential for the current LinkedIn OAuth app context."""

    def save(
        self,
        oauth: LinkedInOAuthSettings,
        credential: OAuth2Auth,
        *,
        subject: str | None = None,
    ) -> None:
        """Persist a reusable LinkedIn OAuth credential securely."""

    def clear(self, oauth: LinkedInOAuthSettings) -> bool:
        """Clear a stored credential for the current app context."""


class LocalEncryptedLinkedInTokenStore:
    """Store a single LinkedIn OAuth credential in an encrypted local file."""

    def __init__(
        self,
        settings: LinkedInTokenStorageSettings,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._path = Path(settings.path).expanduser()
        self._fernet = self._build_fernet(settings.encryption_key)

    def load(self, oauth: LinkedInOAuthSettings) -> StoredLinkedInCredential | None:
        if not self._path.exists():
            logger.info(
                "LinkedIn token store miss for credential key %s",
                oauth.credential_key,
            )
            return None

        payload = self._decrypt_payload()
        if payload["context"] != self._context_payload(oauth):
            logger.info(
                "LinkedIn token store context mismatch for credential key %s",
                oauth.credential_key,
            )
            return None

        credential_payload = payload["credential"]
        credential = StoredLinkedInCredential(
            access_token=credential_payload["access_token"],
            refresh_token=credential_payload.get("refresh_token"),
            expires_at=credential_payload.get("expires_at"),
            expires_in=credential_payload.get("expires_in"),
        )
        if credential.expires_at is not None and credential.expires_at <= self._clock():
            logger.info(
                "LinkedIn token store expired credential for credential key %s",
                oauth.credential_key,
            )
            raise LinkedInTokenStoreExpiredCredentialError(
                "Stored LinkedIn credential has expired"
            )

        logger.info(
            "LinkedIn token store hit for credential key %s",
            oauth.credential_key,
        )
        return credential

    def save(
        self,
        oauth: LinkedInOAuthSettings,
        credential: OAuth2Auth,
        *,
        subject: str | None = None,
    ) -> None:
        stored_credential = StoredLinkedInCredential.from_oauth2(credential)
        payload = {
            "version": _TOKEN_STORE_VERSION,
            "context": self._context_payload(oauth),
            "credential": {
                "access_token": stored_credential.access_token,
                "refresh_token": stored_credential.refresh_token,
                "expires_at": stored_credential.expires_at,
                "expires_in": stored_credential.expires_in,
            },
            "account": {
                "sub": subject,
            },
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
        logger.info(
            "LinkedIn token store saved credential for credential key %s",
            oauth.credential_key,
        )

    def clear(self, oauth: LinkedInOAuthSettings) -> bool:
        if not self._path.exists():
            return False
        self._path.unlink()
        logger.info(
            "LinkedIn token store cleared credential for credential key %s",
            oauth.credential_key,
        )
        return True

    def _decrypt_payload(self) -> dict[str, Any]:
        try:
            decrypted = self._fernet.decrypt(self._path.read_bytes())
        except FileNotFoundError:
            return {"context": {}, "credential": {}}
        except InvalidToken as exc:
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential could not be decrypted"
            ) from exc

        try:
            payload = json.loads(decrypted.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential could not be parsed"
            ) from exc

        if not isinstance(payload, dict):
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential payload is invalid"
            )
        if payload.get("version") != _TOKEN_STORE_VERSION:
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential version is not supported"
            )

        context = payload.get("context")
        credential = payload.get("credential")
        if not isinstance(context, dict) or not isinstance(credential, dict):
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential payload is incomplete"
            )

        access_token = credential.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential does not contain a valid access token"
            )

        expires_at = credential.get("expires_at")
        expires_in = credential.get("expires_in")
        if expires_at is not None and not isinstance(expires_at, (int, float)):
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential expires_at is invalid"
            )
        if expires_in is not None and not isinstance(expires_in, int):
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential expires_in is invalid"
            )
        refresh_token = credential.get("refresh_token")
        if refresh_token is not None and not isinstance(refresh_token, str):
            raise LinkedInTokenStoreInvalidRecordError(
                "Stored LinkedIn credential refresh_token is invalid"
            )

        return {
            "context": context,
            "credential": {
                "access_token": access_token.strip(),
                "refresh_token": refresh_token.strip() or None
                if isinstance(refresh_token, str)
                else None,
                "expires_at": float(expires_at) if expires_at is not None else None,
                "expires_in": expires_in,
            },
        }

    @staticmethod
    def _context_payload(oauth: LinkedInOAuthSettings) -> dict[str, str]:
        return {
            "client_id": oauth.client_id,
            "credential_key": oauth.credential_key,
            "redirect_uri": oauth.redirect_uri,
        }

    @staticmethod
    def _build_fernet(encryption_key: str) -> Fernet:
        try:
            return Fernet(encryption_key.encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise LinkedInTokenStoreConfigurationError(
                "LINKEDIN_TOKEN_ENCRYPTION_KEY must be a valid Fernet key"
            ) from exc
