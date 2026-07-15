"""LinkedIn login service entry point for ADK."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from google.adk.auth.auth_credential import OAuth2Auth

from app.linkedin.client import LinkedInApiClient
from app.linkedin.oauth import (
    LinkedInOAuthError,
    LinkedInOAuthSmokeResult,
    is_loopback_redirect_uri,
    run_linkedin_oauth_browser_smoke_test,
)
from app.linkedin.token_store import (
    LinkedInTokenStore,
    LinkedInTokenStoreConfigurationError,
    LinkedInTokenStoreExpiredCredentialError,
    LinkedInTokenStoreInvalidRecordError,
    LocalEncryptedLinkedInTokenStore,
)
from app.settings import LinkedInApiSettings
from app.tools.linkedin_api_check import LinkedInToolContext, run_linkedin_api_test

_SAFE_ACCOUNT_SUMMARY_KEYS = frozenset({"sub", "name", "given_name", "family_name"})


async def run_linkedin_login_service(
    tool_context: LinkedInToolContext | None = None,
) -> dict[str, object]:
    """Run the LinkedIn login service.

    Use this tool when the user wants to sign in to LinkedIn, reuse a cached ADK
    credential, or verify that the current OAuth configuration can complete a
    read-only LinkedIn connectivity check. For loopback redirect URIs such as
    `localhost`, the tool prefers the repository-controlled local browser flow;
    otherwise it falls back to ADK-managed authorization. It returns a structured,
    safe result without exposing raw tokens or private profile data.
    """

    return await _run_linkedin_login_service(tool_context=tool_context)


async def _run_linkedin_login_service(
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
    browser_login_runner: Callable[[LinkedInApiSettings], LinkedInOAuthSmokeResult]
    | None = None,
    token_store: LinkedInTokenStore | None = None,
) -> dict[str, object]:
    """Internal testable implementation for the LinkedIn login service."""

    resolved_settings = settings or LinkedInApiSettings.from_env()
    resolved_client = client or LinkedInApiClient(resolved_settings)
    try:
        resolved_token_store = _resolve_token_store(resolved_settings, token_store)
    except LinkedInTokenStoreConfigurationError as exc:
        return {
            "ok": False,
            "message": str(exc),
            "error_code": "missing_configuration",
            "status_code": None,
            "account_summary": None,
        }

    if _should_use_local_browser_oauth(resolved_settings):
        stored_result, reauthorization_required = _try_stored_credential_login(
            resolved_settings,
            resolved_client,
            resolved_token_store,
        )
        if stored_result is not None:
            return _safe_login_result(stored_result)
        if reauthorization_required and resolved_token_store is None:
            return {
                "ok": False,
                "message": (
                    "Stored LinkedIn credential is unavailable or no longer valid. "
                    "Configure secure token storage and authorize LinkedIn again."
                ),
                "error_code": "missing_configuration",
                "status_code": None,
                "account_summary": None,
            }

        runner = browser_login_runner or run_linkedin_oauth_browser_smoke_test
        try:
            browser_result = await asyncio.to_thread(runner, resolved_settings)
        except LinkedInOAuthError as exc:
            return {
                "ok": False,
                "message": str(exc),
                "error_code": "oauth_login_failed",
                "status_code": None,
                "account_summary": None,
            }
        if resolved_settings.oauth is not None and resolved_token_store is not None:
            try:
                resolved_token_store.save(
                    resolved_settings.oauth,
                    _oauth2_from_browser_result(resolved_settings, browser_result),
                    subject=browser_result.userinfo.get("sub")
                    if isinstance(browser_result.userinfo, dict)
                    else None,
                )
            except LinkedInTokenStoreConfigurationError as exc:
                return {
                    "ok": False,
                    "message": str(exc),
                    "error_code": "missing_configuration",
                    "status_code": None,
                    "account_summary": None,
                }
        return _safe_login_result(_browser_smoke_result_to_login_result(browser_result))

    result = await run_linkedin_api_test(
        tool_context=tool_context,
        settings=resolved_settings,
        client=resolved_client,
        token_store=resolved_token_store,
    )
    return _safe_login_result(result)


def _safe_login_result(result: dict[str, object]) -> dict[str, object]:
    safe_result = dict(result)
    account_summary = safe_result.get("account_summary")
    if isinstance(account_summary, dict):
        safe_result["account_summary"] = {
            key: value
            for key, value in account_summary.items()
            if key in _SAFE_ACCOUNT_SUMMARY_KEYS
        } or None
    return safe_result


def _should_use_local_browser_oauth(settings: LinkedInApiSettings) -> bool:
    if settings.access_token:
        return False
    oauth = settings.oauth
    if oauth is None:
        return False
    return is_loopback_redirect_uri(oauth.redirect_uri)


def _browser_smoke_result_to_login_result(
    result: LinkedInOAuthSmokeResult,
) -> dict[str, object]:
    return {
        "ok": result.ok,
        "message": result.message,
        "error_code": None,
        "status_code": result.status_code,
        "account_summary": result.userinfo,
    }


def _resolve_token_store(
    settings: LinkedInApiSettings,
    token_store: LinkedInTokenStore | None,
) -> LinkedInTokenStore | None:
    if token_store is not None:
        return token_store
    if settings.token_storage is None:
        return None
    return LocalEncryptedLinkedInTokenStore(settings.token_storage)


def _try_stored_credential_login(
    settings: LinkedInApiSettings,
    client: LinkedInApiClient,
    token_store: LinkedInTokenStore | None,
) -> tuple[dict[str, object] | None, bool]:
    oauth = settings.oauth
    if oauth is None or token_store is None:
        return None, False

    try:
        stored_credential = token_store.load(oauth)
    except LinkedInTokenStoreConfigurationError as exc:
        return {
            "ok": False,
            "message": str(exc),
            "error_code": "missing_configuration",
            "status_code": None,
            "account_summary": None,
        }, False
    except LinkedInTokenStoreExpiredCredentialError:
        token_store.clear(oauth)
        return None, True
    except LinkedInTokenStoreInvalidRecordError:
        token_store.clear(oauth)
        return None, True

    if stored_credential is None:
        return None, False

    result = client.test_connection(
        access_token=stored_credential.access_token
    ).to_dict()
    if result.get("ok") is True:
        result["credential_source"] = "secure_token_store"
        return result, False
    if result.get("error_code") == "permission_denied":
        token_store.clear(oauth)
        return None, True

    result["credential_source"] = "secure_token_store"
    return result, False


def _oauth2_from_browser_result(
    settings: LinkedInApiSettings,
    browser_result: LinkedInOAuthSmokeResult,
) -> OAuth2Auth:
    if settings.oauth is None or not browser_result.access_token:
        raise LinkedInTokenStoreConfigurationError(
            "LinkedIn browser login did not yield a reusable access token"
        )

    return OAuth2Auth(
        client_id=settings.oauth.client_id,
        redirect_uri=settings.oauth.redirect_uri,
        access_token=browser_result.access_token,
        refresh_token=browser_result.refresh_token,
        expires_at=browser_result.expires_at,
        expires_in=browser_result.expires_in,
    )
