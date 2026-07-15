"""LinkedIn API test tool implementation."""

from __future__ import annotations

from typing import Protocol

from google.adk.auth import AuthConfig
from google.adk.auth.auth_credential import AuthCredential

from app.linkedin.client import LinkedInApiClient, LinkedInApiTestResult
from app.linkedin.oauth import (
    LinkedInOAuthError,
    build_auth_config,
    build_user_authorization_prompt,
)
from app.settings import LinkedInApiSettings, SettingsError


class LinkedInToolContext(Protocol):
    """Subset of ADK tool context behavior required by the LinkedIn test tool."""

    def request_credential(self, auth_config: AuthConfig) -> None:
        """Request OAuth credentials for the given auth config."""

    def get_auth_response(self, auth_config: AuthConfig) -> AuthCredential | None:
        """Return a completed OAuth response when one is already available."""

    async def load_credential(self, auth_config: AuthConfig) -> AuthCredential | None:
        """Load a previously saved credential for the given auth config."""

    async def save_credential(self, auth_config: AuthConfig) -> None:
        """Persist the exchanged credential for the given auth config."""


async def _load_saved_credential(
    tool_context: LinkedInToolContext, auth_config: AuthConfig
) -> AuthCredential | None:
    try:
        return await tool_context.load_credential(auth_config)
    except ValueError:
        return None


async def _save_credential(
    tool_context: LinkedInToolContext,
    auth_config: AuthConfig,
    credential: AuthCredential,
) -> None:
    try:
        await tool_context.save_credential(
            auth_config.model_copy(update={"exchanged_auth_credential": credential})
        )
    except ValueError:
        return


def _pending_authorization_result(settings: LinkedInApiSettings) -> dict[str, object]:
    result = LinkedInApiTestResult(
        ok=False,
        message="Awaiting LinkedIn authorization",
        error_code="missing_configuration",
    ).to_dict()
    result["pending_auth"] = True

    oauth_settings = settings.oauth
    if oauth_settings is None:
        return result

    try:
        prompt = build_user_authorization_prompt(oauth_settings)
    except LinkedInOAuthError:
        return result

    result["authorization_url"] = prompt.authorization_url
    result["authorization_message"] = prompt.prompt_message
    result["next_step"] = prompt.next_step
    return result


def _access_token_from_credential(credential: AuthCredential | None) -> str | None:
    if credential is None or credential.oauth2 is None:
        return None
    return credential.oauth2.access_token


async def run_linkedin_api_test(
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
) -> dict[str, object]:
    """Execute the LinkedIn API test flow and return a structured result.

    Use this helper when you need a non-mutating check that the LinkedIn API token,
    OAuth client settings, and endpoint are configured correctly. The helper prefers
    ADK-managed OAuth via `ToolContext` and falls back to `LINKEDIN_ACCESS_TOKEN` when
    one is provided directly. It returns a structured result with `ok`, `message`,
    optional safe `account_summary`, and normalized `error_code`.
    """

    try:
        resolved_settings = settings or LinkedInApiSettings.from_env()
    except SettingsError as exc:
        return LinkedInApiTestResult(
            ok=False,
            message=str(exc),
            error_code="missing_configuration",
        ).to_dict()

    resolved_client = client or LinkedInApiClient(resolved_settings)
    if resolved_settings.access_token:
        return resolved_client.test_connection(
            access_token=resolved_settings.access_token
        ).to_dict()

    if resolved_settings.oauth is None or tool_context is None:
        return LinkedInApiTestResult(
            ok=False,
            message=(
                "LinkedIn OAuth configuration is present, but ADK ToolContext is "
                "required to request or reuse credentials"
            ),
            error_code="missing_configuration",
        ).to_dict()

    auth_config = build_auth_config(resolved_settings.oauth)
    credential = await _load_saved_credential(tool_context, auth_config)
    if credential is None:
        credential = tool_context.get_auth_response(auth_config)

    if credential is None:
        tool_context.request_credential(auth_config)
        return _pending_authorization_result(resolved_settings)

    access_token = _access_token_from_credential(credential)
    if not access_token:
        return LinkedInApiTestResult(
            ok=False,
            message="LinkedIn authorization did not yield an access token",
            error_code="missing_configuration",
        ).to_dict()

    await _save_credential(tool_context, auth_config, credential)
    return resolved_client.test_connection(access_token=access_token).to_dict()
