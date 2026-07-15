"""LinkedIn login service entry point for ADK."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.linkedin.client import LinkedInApiClient
from app.linkedin.oauth import (
    LinkedInOAuthError,
    LinkedInOAuthSmokeResult,
    is_loopback_redirect_uri,
    run_linkedin_oauth_browser_smoke_test,
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
) -> dict[str, object]:
    """Internal testable implementation for the LinkedIn login service."""

    resolved_settings = settings or LinkedInApiSettings.from_env()
    if _should_use_local_browser_oauth(resolved_settings):
        runner = browser_login_runner or run_linkedin_oauth_browser_smoke_test
        try:
            browser_result = await asyncio.to_thread(runner, resolved_settings)
        except LinkedInOAuthError as exc:
            return {
                "ok": False,
                "message": str(exc),
                "error_code": "missing_configuration",
                "status_code": None,
                "account_summary": None,
            }
        return _safe_login_result(_browser_smoke_result_to_login_result(browser_result))

    result = await run_linkedin_api_test(
        tool_context=tool_context, settings=resolved_settings, client=client
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
