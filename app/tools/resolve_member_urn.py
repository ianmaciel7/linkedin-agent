"""ADK tool: resolve the authenticated LinkedIn member URN."""

from __future__ import annotations

import logging

from app.linkedin.client import LinkedInApiClient, LinkedInApiTestResult
from app.linkedin.credential_lifecycle import resolve_stored_credential
from app.linkedin.member import MemberUrnError, resolve_member_urn
from app.linkedin.models import MemberProfile
from app.linkedin.profile_store import (
    LinkedInProfileStoreConfigurationError,
    LinkedInProfileStoreInvalidRecordError,
    LocalEncryptedProfileStore,
)
from app.linkedin.tool_context_auth import (
    LinkedInToolContext,
    access_token_from_credential,
    load_saved_credential,
)
from app.settings import LinkedInApiSettings, SettingsError

logger = logging.getLogger(__name__)


def _optional_string(value: object) -> str | None:
    """Return a non-empty string value for optional profile claims."""

    if value in (None, ""):
        return None
    return str(value)


async def _resolve_access_token(
    *,
    tool_context: LinkedInToolContext | None,
    settings: LinkedInApiSettings,
) -> tuple[str | None, str | None, dict[str, object] | None]:
    """Resolve a usable access token using env, local store, or ToolContext."""

    access_token: str | None = settings.access_token
    credential_source = "env" if access_token else None

    if not access_token and settings.token_storage is not None:
        try:
            from app.linkedin.token_store import LocalEncryptedLinkedInTokenStore

            token_store = LocalEncryptedLinkedInTokenStore(settings.token_storage)
            resolution = resolve_stored_credential(settings, token_store)
            if resolution.error_result is not None:
                return None, None, resolution.error_result.to_dict()
            if resolution.credential is not None:
                access_token = resolution.credential.access_token
                credential_source = resolution.credential_source or "secure_token_store"
        except Exception as exc:  # noqa: BLE001
            logger.debug("LinkedIn token store lookup failed: %s", type(exc).__name__)

    if not access_token and tool_context is not None and settings.oauth is not None:
        from app.linkedin.oauth import build_auth_config

        auth_config = build_auth_config(settings.oauth)
        credential = await load_saved_credential(tool_context, auth_config)
        if credential is None:
            credential = tool_context.get_auth_response(auth_config)
        if credential is not None:
            access_token = access_token_from_credential(credential)
            credential_source = "adk_tool_context"

    if not access_token:
        return (
            None,
            None,
            LinkedInApiTestResult(
                ok=False,
                message=(
                    "LinkedIn access token is not available. "
                    "Run the OAuth tool first to authenticate."
                ),
                error_code="missing_configuration",
            ).to_dict(),
        )

    return access_token, credential_source, None


async def run_resolve_member_urn(
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
) -> dict[str, object]:
    """Resolve and return the authenticated LinkedIn member URN.

    Derives the member URN from the OIDC ``sub`` claim returned by
    ``/userinfo``.  When a profile storage path is configured, the resolved URN
    is persisted so that subsequent tool calls can retrieve it without a network
    round-trip.

    Call this tool when the user wants to confirm their LinkedIn identity, or
    before calling any tool that requires a member URN.

    Returns a structured result with:
    - ``ok``: True on success.
    - ``member_urn``: The member URN in ``urn:li:member:<sub>`` form.
    - ``credential_source``: Where the access token came from.
    - ``stored``: True when the URN was persisted to the profile store.
    """
    try:
        resolved_settings = settings or LinkedInApiSettings.from_env()
    except SettingsError as exc:
        return LinkedInApiTestResult(
            ok=False,
            message=str(exc),
            error_code="missing_configuration",
        ).to_dict()

    access_token, credential_source, error_result = await _resolve_access_token(
        tool_context=tool_context,
        settings=resolved_settings,
    )
    if error_result is not None:
        return error_result

    # Check if URN is already stored to avoid a redundant /userinfo call.
    profile_store = None
    if resolved_settings.profile_storage is not None:
        try:
            profile_store = LocalEncryptedProfileStore(
                resolved_settings.profile_storage.path,
                resolved_settings.profile_storage.encryption_key,
            )
            stored_profile = profile_store.load()
            if stored_profile is not None and stored_profile.member_urn:
                return {
                    "ok": True,
                    "member_urn": stored_profile.member_urn,
                    "credential_source": "profile_store",
                    "stored": True,
                }
        except (
            LinkedInProfileStoreConfigurationError,
            LinkedInProfileStoreInvalidRecordError,
        ) as exc:
            logger.debug("LinkedIn profile store read failed: %s", type(exc).__name__)

    # Fetch /userinfo to obtain the sub claim.
    api_client = client or LinkedInApiClient(resolved_settings)
    result = api_client.test_connection(access_token=access_token)
    if not result.ok:
        return result.to_dict()

    userinfo: dict[str, object] = {}
    if isinstance(result.account_summary, dict):
        userinfo = dict(result.account_summary)

    # The account_summary is a safe subset; we need the full sub from /userinfo.
    # Resolve it directly from the userinfo response the client already fetched.
    try:
        member_urn = resolve_member_urn(userinfo)
    except MemberUrnError as exc:
        return {
            "ok": False,
            "message": str(exc),
            "error_code": "upstream_failure",
        }

    out: dict[str, object] = {
        "ok": True,
        "member_urn": member_urn,
        "credential_source": credential_source,
        "stored": False,
    }

    # Persist the URN in the profile store when available.
    if profile_store is not None:
        try:
            sub = userinfo.get("sub", "")
            profile_store.save(
                MemberProfile(
                    member_urn=member_urn,
                    sub=str(sub),
                    name=_optional_string(userinfo.get("name")),
                    given_name=_optional_string(userinfo.get("given_name")),
                    family_name=_optional_string(userinfo.get("family_name")),
                    email=_optional_string(userinfo.get("email")),
                )
            )
            out["stored"] = True
        except (LinkedInProfileStoreConfigurationError, OSError) as exc:
            profile_storage_path = (
                resolved_settings.profile_storage.path
                if resolved_settings.profile_storage is not None
                else "<unconfigured>"
            )
            logger.debug(
                "LinkedIn profile store write failed: %s at %s",
                type(exc).__name__,
                profile_storage_path,
            )

    return out
