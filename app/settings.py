"""Validated runtime settings for the LinkedIn login and API helpers."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse


class SettingsError(ValueError):
    """Raised when required runtime settings are missing or invalid."""


DEFAULT_LINKEDIN_API_TEST_URL = "https://api.linkedin.com/v2/userinfo"
DEFAULT_LINKEDIN_API_TIMEOUT_SECONDS = 10.0
DEFAULT_LINKEDIN_OAUTH_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
DEFAULT_LINKEDIN_OAUTH_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
DEFAULT_LINKEDIN_OAUTH_USERINFO_URL = DEFAULT_LINKEDIN_API_TEST_URL
DEFAULT_LINKEDIN_OAUTH_SCOPES = ("openid", "profile", "email")
DEFAULT_LINKEDIN_OAUTH_CREDENTIAL_KEY = "linkedin_oauth"
DEFAULT_LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS = 180.0


@dataclass(frozen=True, slots=True)
class LinkedInOAuthSettings:
    """OAuth settings required for ADK-managed LinkedIn authorization."""

    client_id: str
    client_secret: str
    redirect_uri: str
    auth_url: str = DEFAULT_LINKEDIN_OAUTH_AUTH_URL
    token_url: str = DEFAULT_LINKEDIN_OAUTH_TOKEN_URL
    userinfo_url: str = DEFAULT_LINKEDIN_OAUTH_USERINFO_URL
    scopes: tuple[str, ...] = DEFAULT_LINKEDIN_OAUTH_SCOPES
    credential_key: str = DEFAULT_LINKEDIN_OAUTH_CREDENTIAL_KEY
    callback_timeout_seconds: float = DEFAULT_LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class LinkedInTokenStorageSettings:
    """Settings required for local encrypted LinkedIn token persistence."""

    path: str
    encryption_key: str


@dataclass(frozen=True, slots=True)
class LinkedInProfileStorageSettings:
    """Settings required for local encrypted LinkedIn profile persistence."""

    path: str
    encryption_key: str


@dataclass(frozen=True, slots=True)
class LinkedInPostStorageSettings:
    """Settings required for local encrypted LinkedIn post metadata persistence."""

    path: str
    encryption_key: str


@dataclass(frozen=True, slots=True)
class LinkedInApiSettings:
    """Settings required for the read-only LinkedIn API connectivity test."""

    access_token: str | None = None
    test_url: str = DEFAULT_LINKEDIN_API_TEST_URL
    timeout_seconds: float = DEFAULT_LINKEDIN_API_TIMEOUT_SECONDS
    oauth: LinkedInOAuthSettings | None = None
    token_storage: LinkedInTokenStorageSettings | None = None
    profile_storage: LinkedInProfileStorageSettings | None = None
    post_storage: LinkedInPostStorageSettings | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LinkedInApiSettings:
        """Build validated LinkedIn API settings from environment variables."""

        values = os.environ if env is None else env

        access_token = values.get("LINKEDIN_ACCESS_TOKEN", "").strip() or None

        test_url = values.get(
            "LINKEDIN_API_TEST_URL", DEFAULT_LINKEDIN_API_TEST_URL
        ).strip()
        if not test_url:
            raise SettingsError("LINKEDIN_API_TEST_URL must not be empty when provided")

        raw_timeout = values.get(
            "LINKEDIN_API_TIMEOUT_SECONDS", str(DEFAULT_LINKEDIN_API_TIMEOUT_SECONDS)
        ).strip()
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise SettingsError(
                "LINKEDIN_API_TIMEOUT_SECONDS must be a positive number"
            ) from exc

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise SettingsError(
                "LINKEDIN_API_TIMEOUT_SECONDS must be a positive number"
            )

        oauth = cls._oauth_settings_from_env(values)
        token_storage = cls._token_storage_settings_from_env(values)
        if access_token is None and oauth is None:
            raise SettingsError(
                "Missing LinkedIn credentials. Provide LINKEDIN_ACCESS_TOKEN or "
                "configure LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and "
                "LINKEDIN_REDIRECT_URI."
            )
        if (
            access_token is None
            and oauth is not None
            and token_storage is None
            and cls._requires_local_token_storage(oauth)
        ):
            raise SettingsError(
                "Missing required environment variable: LINKEDIN_TOKEN_STORAGE_PATH"
            )

        profile_storage = cls._profile_storage_settings_from_env(values)
        post_storage = cls._post_storage_settings_from_env(values)

        return cls(
            access_token=access_token,
            test_url=test_url,
            timeout_seconds=timeout_seconds,
            oauth=oauth,
            token_storage=token_storage,
            profile_storage=profile_storage,
            post_storage=post_storage,
        )

    @staticmethod
    def _oauth_settings_from_env(
        values: Mapping[str, str],
    ) -> LinkedInOAuthSettings | None:
        client_id = values.get("LINKEDIN_CLIENT_ID", "").strip()
        client_secret = values.get("LINKEDIN_CLIENT_SECRET", "").strip()
        redirect_uri = values.get("LINKEDIN_REDIRECT_URI", "").strip()

        oauth_values = {
            "LINKEDIN_CLIENT_ID": client_id,
            "LINKEDIN_CLIENT_SECRET": client_secret,
            "LINKEDIN_REDIRECT_URI": redirect_uri,
        }
        provided_keys = [key for key, value in oauth_values.items() if value]
        if not provided_keys:
            return None

        missing_keys = [key for key, value in oauth_values.items() if not value]
        if missing_keys:
            raise SettingsError(
                f"Missing required environment variable: {missing_keys[0]}"
            )

        auth_url = values.get(
            "LINKEDIN_OAUTH_AUTH_URL", DEFAULT_LINKEDIN_OAUTH_AUTH_URL
        ).strip()
        token_url = values.get(
            "LINKEDIN_OAUTH_TOKEN_URL", DEFAULT_LINKEDIN_OAUTH_TOKEN_URL
        ).strip()
        userinfo_url = values.get(
            "LINKEDIN_OAUTH_USERINFO_URL", DEFAULT_LINKEDIN_OAUTH_USERINFO_URL
        ).strip()
        credential_key = values.get(
            "LINKEDIN_OAUTH_CREDENTIAL_KEY", DEFAULT_LINKEDIN_OAUTH_CREDENTIAL_KEY
        ).strip()
        raw_callback_timeout = values.get(
            "LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS",
            str(DEFAULT_LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS),
        ).strip()
        raw_scopes = values.get(
            "LINKEDIN_OAUTH_SCOPES", ",".join(DEFAULT_LINKEDIN_OAUTH_SCOPES)
        )
        scopes = tuple(
            scope.strip() for scope in raw_scopes.split(",") if scope.strip()
        )
        try:
            callback_timeout_seconds = float(raw_callback_timeout)
        except ValueError as exc:
            raise SettingsError(
                "LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS must be a positive number"
            ) from exc

        if not auth_url:
            raise SettingsError(
                "LINKEDIN_OAUTH_AUTH_URL must not be empty when provided"
            )
        if not token_url:
            raise SettingsError(
                "LINKEDIN_OAUTH_TOKEN_URL must not be empty when provided"
            )
        if not userinfo_url:
            raise SettingsError(
                "LINKEDIN_OAUTH_USERINFO_URL must not be empty when provided"
            )
        if not scopes:
            raise SettingsError("LINKEDIN_OAUTH_SCOPES must include at least one scope")
        if not credential_key:
            raise SettingsError(
                "LINKEDIN_OAUTH_CREDENTIAL_KEY must not be empty when provided"
            )
        if not math.isfinite(callback_timeout_seconds) or callback_timeout_seconds <= 0:
            raise SettingsError(
                "LINKEDIN_OAUTH_CALLBACK_TIMEOUT_SECONDS must be a positive number"
            )

        return LinkedInOAuthSettings(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            auth_url=auth_url,
            token_url=token_url,
            userinfo_url=userinfo_url,
            scopes=scopes,
            credential_key=credential_key,
            callback_timeout_seconds=callback_timeout_seconds,
        )

    @staticmethod
    def _token_storage_settings_from_env(
        values: Mapping[str, str],
    ) -> LinkedInTokenStorageSettings | None:
        path = values.get("LINKEDIN_TOKEN_STORAGE_PATH", "").strip()
        encryption_key = values.get("LINKEDIN_TOKEN_ENCRYPTION_KEY", "").strip()

        if not path and not encryption_key:
            return None
        if not path:
            raise SettingsError(
                "Missing required environment variable: LINKEDIN_TOKEN_STORAGE_PATH"
            )
        if not encryption_key:
            raise SettingsError(
                "Missing required environment variable: LINKEDIN_TOKEN_ENCRYPTION_KEY"
            )

        return LinkedInTokenStorageSettings(
            path=path,
            encryption_key=encryption_key,
        )

    @staticmethod
    def _profile_storage_settings_from_env(
        values: Mapping[str, str],
    ) -> LinkedInProfileStorageSettings | None:
        path = values.get("LINKEDIN_PROFILE_STORAGE_PATH", "").strip()
        # Reuses the token encryption key — no additional secret required.
        encryption_key = values.get("LINKEDIN_TOKEN_ENCRYPTION_KEY", "").strip()

        if not path:
            return None
        if not encryption_key:
            raise SettingsError(
                "LINKEDIN_PROFILE_STORAGE_PATH is set but "
                "LINKEDIN_TOKEN_ENCRYPTION_KEY is missing"
            )
        return LinkedInProfileStorageSettings(path=path, encryption_key=encryption_key)

    @staticmethod
    def _post_storage_settings_from_env(
        values: Mapping[str, str],
    ) -> LinkedInPostStorageSettings | None:
        path = values.get("LINKEDIN_POST_STORAGE_PATH", "").strip()
        encryption_key = values.get("LINKEDIN_TOKEN_ENCRYPTION_KEY", "").strip()

        if not path:
            return None
        if not encryption_key:
            raise SettingsError(
                "LINKEDIN_POST_STORAGE_PATH is set but "
                "LINKEDIN_TOKEN_ENCRYPTION_KEY is missing"
            )
        return LinkedInPostStorageSettings(path=path, encryption_key=encryption_key)

    @staticmethod
    def _requires_local_token_storage(oauth: LinkedInOAuthSettings) -> bool:
        parsed = urlparse(oauth.redirect_uri)
        return parsed.hostname in {"localhost", "127.0.0.1"}
