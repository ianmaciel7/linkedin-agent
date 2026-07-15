from __future__ import annotations

import pytest

from app.settings import LinkedInApiSettings, LinkedInOAuthSettings, SettingsError


def test_from_env_uses_defaults_when_optional_values_missing() -> None:
    settings = LinkedInApiSettings.from_env(
        {
            "LINKEDIN_ACCESS_TOKEN": "token-123",
        }
    )

    assert settings.access_token == "token-123"
    assert settings.test_url == "https://api.linkedin.com/v2/userinfo"
    assert settings.timeout_seconds == 10.0
    assert settings.oauth is None


def test_from_env_rejects_missing_access_token_without_oauth_settings() -> None:
    with pytest.raises(SettingsError, match="LINKEDIN_ACCESS_TOKEN|LINKEDIN_CLIENT_ID"):
        LinkedInApiSettings.from_env({})


def test_from_env_rejects_invalid_timeout() -> None:
    with pytest.raises(SettingsError, match="LINKEDIN_API_TIMEOUT_SECONDS"):
        LinkedInApiSettings.from_env(
            {
                "LINKEDIN_ACCESS_TOKEN": "token-123",
                "LINKEDIN_API_TIMEOUT_SECONDS": "not-a-number",
            }
        )


@pytest.mark.parametrize("timeout_value", ["nan", "inf", "-inf", "0", "-1"])
def test_from_env_rejects_non_finite_or_non_positive_timeout(
    timeout_value: str,
) -> None:
    with pytest.raises(SettingsError, match="LINKEDIN_API_TIMEOUT_SECONDS"):
        LinkedInApiSettings.from_env(
            {
                "LINKEDIN_ACCESS_TOKEN": "token-123",
                "LINKEDIN_API_TIMEOUT_SECONDS": timeout_value,
            }
        )


def test_from_env_accepts_complete_oauth_settings_without_access_token() -> None:
    settings = LinkedInApiSettings.from_env(
        {
            "LINKEDIN_CLIENT_ID": "client-id",
            "LINKEDIN_CLIENT_SECRET": "client-secret",
            "LINKEDIN_REDIRECT_URI": "http://localhost:8000/callback",
        }
    )

    assert settings.access_token is None
    assert settings.oauth == LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8000/callback",
    )


def test_from_env_rejects_partial_oauth_settings() -> None:
    with pytest.raises(SettingsError, match="LINKEDIN_REDIRECT_URI"):
        LinkedInApiSettings.from_env(
            {
                "LINKEDIN_CLIENT_ID": "client-id",
                "LINKEDIN_CLIENT_SECRET": "client-secret",
            }
        )
