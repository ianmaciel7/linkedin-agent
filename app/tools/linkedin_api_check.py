"""LinkedIn API test tool implementation."""

from __future__ import annotations

import logging

from app.linkedin.client import LinkedInApiClient, LinkedInApiTestResult
from app.linkedin.credential_lifecycle import resolve_stored_credential
from app.linkedin.oauth import (
    LinkedInOAuthError,
    build_auth_config,
    build_user_authorization_prompt,
)
from app.linkedin.token_store import (
    LinkedInTokenStore,
    LinkedInTokenStoreConfigurationError,
    LocalEncryptedLinkedInTokenStore,
)
from app.linkedin.tool_context_auth import (
    LinkedInToolContext,
    access_token_from_credential,
    load_saved_credential,
    save_credential,
)
from app.settings import LinkedInApiSettings, SettingsError

logger = logging.getLogger(__name__)


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


def _token_store_from_settings(
    settings: LinkedInApiSettings,
    token_store: LinkedInTokenStore | None,
) -> LinkedInTokenStore | None:
    if token_store is not None:
        return token_store
    if settings.token_storage is None:
        return None
    return LocalEncryptedLinkedInTokenStore(settings.token_storage)


def _store_configuration_error_result(message: str) -> dict[str, object]:
    return LinkedInApiTestResult(
        ok=False,
        message=message,
        error_code="missing_configuration",
    ).to_dict()


def _invalid_stored_credential_result(message: str) -> dict[str, object]:
    result = LinkedInApiTestResult(
        ok=False,
        message=message,
        error_code="invalid_stored_credential",
    ).to_dict()
    result["reauthorization_required"] = True
    return result


async def run_linkedin_api_test(
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
    token_store: LinkedInTokenStore | None = None,
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

    try:
        resolved_token_store = _token_store_from_settings(
            resolved_settings, token_store
        )
    except LinkedInTokenStoreConfigurationError as exc:
        return _store_configuration_error_result(str(exc))

    if resolved_settings.oauth is None:
        return LinkedInApiTestResult(
            ok=False,
            message=(
                "LinkedIn OAuth configuration is present, but ADK ToolContext is "
                "required to request or reuse credentials"
            ),
            error_code="missing_configuration",
        ).to_dict()

    resolution = None
    if resolved_token_store is not None:
        resolution = resolve_stored_credential(
            resolved_settings,
            resolved_token_store,
        )
        if resolution.error_result is not None:
            return resolution.error_result.to_dict()
        if resolution.credential is not None:
            result = resolved_client.test_connection(
                access_token=resolution.credential.access_token
            ).to_dict()
            if result.get("ok") is True:
                result["credential_source"] = (
                    resolution.credential_source or "secure_token_store"
                )
                return result
            if result.get("error_code") == "permission_denied":
                resolved_token_store.clear(resolved_settings.oauth)
                logger.info(
                    "LinkedIn stored credential rejected for credential key %s",
                    resolved_settings.oauth.credential_key,
                )
            else:
                result["credential_source"] = (
                    resolution.credential_source or "secure_token_store"
                )
                return result

    if tool_context is None:
        if (
            resolved_token_store is not None
            and resolution is not None
            and resolution.reauthorization_required
        ):
            return _invalid_stored_credential_result(
                "Stored LinkedIn credential is unavailable or no longer valid. "
                "Reauthorize LinkedIn from an ADK tool session to continue."
            )
        return LinkedInApiTestResult(
            ok=False,
            message=(
                "LinkedIn OAuth configuration is present, but ADK ToolContext is "
                "required to request or reuse credentials"
            ),
            error_code="missing_configuration",
        ).to_dict()

    auth_config = build_auth_config(resolved_settings.oauth)
    credential = await load_saved_credential(tool_context, auth_config)
    if credential is None:
        credential = tool_context.get_auth_response(auth_config)

    if credential is None:
        tool_context.request_credential(auth_config)
        return _pending_authorization_result(resolved_settings)

    access_token = access_token_from_credential(credential)
    if not access_token:
        return LinkedInApiTestResult(
            ok=False,
            message="LinkedIn authorization did not yield an access token",
            error_code="missing_configuration",
        ).to_dict()

    await save_credential(tool_context, auth_config, credential)
    result = resolved_client.test_connection(access_token=access_token).to_dict()
    if (
        result.get("ok") is True
        and credential.oauth2 is not None
        and resolved_token_store is not None
    ):
        try:
            account_summary = result.get("account_summary")
            resolved_token_store.save(
                resolved_settings.oauth,
                credential.oauth2,
                subject=account_summary.get("sub")
                if isinstance(account_summary, dict)
                else None,
            )
        except LinkedInTokenStoreConfigurationError as exc:
            return _store_configuration_error_result(str(exc))
    elif (
        result.get("error_code") == "permission_denied"
        and resolved_token_store is not None
    ):
        resolved_token_store.clear(resolved_settings.oauth)

    return result
