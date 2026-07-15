"""LinkedIn login orchestration service."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from google.adk.auth.auth_credential import OAuth2Auth

from app.linkedin.client import LinkedInApiClient, LinkedInApiTestResult
from app.linkedin.credential_lifecycle import resolve_stored_credential
from app.linkedin.oauth import (
    LinkedInOAuthError,
    LinkedInOAuthSmokeResult,
    build_auth_config,
    is_loopback_redirect_uri,
    run_linkedin_oauth_browser_smoke_test,
)
from app.linkedin.token_store import (
    LinkedInTokenStore,
    LinkedInTokenStoreConfigurationError,
    LocalEncryptedLinkedInTokenStore,
)
from app.linkedin.tool_context_auth import (
    ToolContextCredentialResolution,
    access_token_from_credential,
    load_saved_credential,
    save_credential,
)
from app.settings import LinkedInApiSettings

if TYPE_CHECKING:
    from app.linkedin.tool_context_auth import LinkedInToolContext

_SAFE_ACCOUNT_SUMMARY_KEYS = frozenset({"sub", "name", "given_name", "family_name"})
logger = logging.getLogger(__name__)


class LinkedInLoginService:
    """Coordinate LinkedIn login flows behind a small service boundary.

    The service follows the same general shape as ADK's native services:
    dependencies are injected at construction time, and the public method
    exposes one focused operation for the caller.
    """

    def __init__(
        self,
        *,
        settings: LinkedInApiSettings | None = None,
        client: LinkedInApiClient | None = None,
        browser_login_runner: Callable[[LinkedInApiSettings], LinkedInOAuthSmokeResult]
        | None = None,
        token_store: LinkedInTokenStore | None = None,
    ) -> None:
        self._settings = settings or LinkedInApiSettings.from_env()
        self._client = client or LinkedInApiClient(self._settings)
        self._browser_login_runner = (
            browser_login_runner or run_linkedin_oauth_browser_smoke_test
        )
        self._token_store = token_store

    async def run(
        self,
        tool_context: LinkedInToolContext | None = None,
    ) -> dict[str, object]:
        """Run the LinkedIn login flow and return a safe structured result."""

        try:
            resolved_token_store = self._resolve_token_store()
        except LinkedInTokenStoreConfigurationError as exc:
            return LinkedInApiTestResult(
                ok=False,
                message=str(exc),
                error_code="missing_configuration",
            ).to_dict()

        if self._should_use_local_browser_oauth():
            stored_result, reauthorization_required = self._try_stored_credential_login(
                resolved_token_store
            )
            if stored_result is not None:
                return self._safe_login_result(stored_result)
            if reauthorization_required and resolved_token_store is None:
                return LinkedInApiTestResult(
                    ok=False,
                    message=(
                        "Stored LinkedIn credential is unavailable or no longer "
                        "valid. Configure secure token storage and authorize "
                        "LinkedIn again."
                    ),
                    error_code="missing_configuration",
                ).to_dict()

            tool_context_resolution = await self._try_tool_context_credential_login(
                tool_context=tool_context,
                token_store=resolved_token_store,
            )
            if tool_context_resolution.result is not None:
                tool_context_result = tool_context_resolution.result.to_dict()
                if tool_context_resolution.credential_source is not None:
                    tool_context_result["credential_source"] = (
                        tool_context_resolution.credential_source
                    )
                return self._safe_login_result(tool_context_result)

            try:
                browser_result = await asyncio.to_thread(
                    self._browser_login_runner, self._settings
                )
            except LinkedInOAuthError as exc:
                return LinkedInApiTestResult(
                    ok=False,
                    message=str(exc),
                    error_code="oauth_login_failed",
                ).to_dict()
            if self._settings.oauth is not None and resolved_token_store is not None:
                try:
                    resolved_token_store.save(
                        self._settings.oauth,
                        self._oauth2_from_browser_result(browser_result),
                        subject=browser_result.userinfo.get("sub")
                        if isinstance(browser_result.userinfo, dict)
                        else None,
                    )
                except LinkedInTokenStoreConfigurationError as exc:
                    return LinkedInApiTestResult(
                        ok=False,
                        message=str(exc),
                        error_code="missing_configuration",
                    ).to_dict()
            return self._safe_login_result(
                self._browser_smoke_result_to_login_result(browser_result)
            )

        from app.tools.linkedin_api_check import run_linkedin_api_test

        result = await run_linkedin_api_test(
            tool_context=tool_context,
            settings=self._settings,
            client=self._client,
            token_store=resolved_token_store,
        )
        return self._safe_login_result(result)

    def _resolve_token_store(self) -> LinkedInTokenStore | None:
        if self._token_store is not None:
            return self._token_store
        if self._settings.token_storage is None:
            return None
        return LocalEncryptedLinkedInTokenStore(self._settings.token_storage)

    def _should_use_local_browser_oauth(self) -> bool:
        if self._settings.access_token:
            return False
        oauth = self._settings.oauth
        if oauth is None:
            return False
        return is_loopback_redirect_uri(oauth.redirect_uri)

    def _try_stored_credential_login(
        self,
        token_store: LinkedInTokenStore | None,
    ) -> tuple[dict[str, object] | None, bool]:
        oauth = self._settings.oauth
        resolution = resolve_stored_credential(self._settings, token_store)
        if resolution.error_result is not None:
            return resolution.error_result.to_dict(), False
        if resolution.credential is None:
            return None, resolution.reauthorization_required

        stored_credential = resolution.credential
        result = self._client.test_connection(
            access_token=stored_credential.access_token
        ).to_dict()
        credential_source = resolution.credential_source or "secure_token_store"
        if result.get("ok") is True:
            result["credential_source"] = credential_source
            return result, False
        if (
            result.get("error_code") == "permission_denied"
            and oauth is not None
            and token_store is not None
        ):
            logger.info(
                "LinkedIn stored credential was rejected after reuse for credential key %s",
                oauth.credential_key,
            )
            token_store.clear(oauth)
            return None, True

        result["credential_source"] = credential_source
        return result, False

    async def _try_tool_context_credential_login(
        self,
        *,
        tool_context: LinkedInToolContext | None,
        token_store: LinkedInTokenStore | None,
    ) -> ToolContextCredentialResolution:
        oauth = self._settings.oauth
        if tool_context is None or oauth is None:
            return ToolContextCredentialResolution()

        auth_config = build_auth_config(oauth)
        credential = await load_saved_credential(tool_context, auth_config)
        if credential is None:
            credential = tool_context.get_auth_response(auth_config)
        if credential is None or credential.oauth2 is None:
            return ToolContextCredentialResolution()

        access_token = (access_token_from_credential(credential) or "").strip()
        if not access_token:
            return ToolContextCredentialResolution(
                result=LinkedInApiTestResult(
                    ok=False,
                    message="LinkedIn authorization did not yield an access token",
                    error_code="missing_configuration",
                )
            )

        result = self._client.test_connection(access_token=access_token)
        if result.ok is not True:
            if result.error_code == "permission_denied":
                logger.info(
                    "LinkedIn ADK ToolContext credential was rejected for credential key %s",
                    oauth.credential_key,
                )
                return ToolContextCredentialResolution(
                    browser_reauthorization_required=True
                )
            return ToolContextCredentialResolution(result=result)

        await save_credential(tool_context, auth_config, credential)

        if token_store is not None:
            try:
                account_summary = result.account_summary
                subject = None
                if isinstance(account_summary, dict):
                    raw_subject = account_summary.get("sub")
                    if isinstance(raw_subject, str):
                        subject = raw_subject
                token_store.save(
                    oauth,
                    credential.oauth2,
                    subject=subject,
                )
            except LinkedInTokenStoreConfigurationError as exc:
                return ToolContextCredentialResolution(
                    result=LinkedInApiTestResult(
                        ok=False,
                        message=str(exc),
                        error_code="missing_configuration",
                    )
                )

        return ToolContextCredentialResolution(
            result=result,
            credential_source="adk_tool_context",
        )

    @staticmethod
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

    @staticmethod
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

    def _oauth2_from_browser_result(
        self,
        browser_result: LinkedInOAuthSmokeResult,
    ) -> OAuth2Auth:
        if self._settings.oauth is None or not browser_result.access_token:
            raise LinkedInTokenStoreConfigurationError(
                "LinkedIn browser login did not yield a reusable access token"
            )

        return OAuth2Auth(
            client_id=self._settings.oauth.client_id,
            redirect_uri=self._settings.oauth.redirect_uri,
            access_token=browser_result.access_token,
            refresh_token=browser_result.refresh_token,
            expires_at=browser_result.expires_at,
            expires_in=browser_result.expires_in,
        )
