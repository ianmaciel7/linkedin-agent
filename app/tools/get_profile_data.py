"""ADK tool: return structured LinkedIn profile data."""

from __future__ import annotations

import logging

from app.linkedin.client import LinkedInApiClient, LinkedInApiTestResult
from app.linkedin.profile import assemble_profile
from app.linkedin.profile_store import (
    LinkedInProfileStoreConfigurationError,
    LinkedInProfileStoreInvalidRecordError,
    LocalEncryptedProfileStore,
)
from app.linkedin.tool_context_auth import LinkedInToolContext
from app.settings import LinkedInApiSettings, SettingsError

from .resolve_member_urn import _resolve_access_token

logger = logging.getLogger(__name__)


async def run_get_profile_data(
    user_supplied: dict[str, str] | None = None,
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
) -> dict[str, object]:
    """Return a structured member profile for the authenticated LinkedIn user."""

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

    profile_store = None
    stored_profile = None
    if resolved_settings.profile_storage is not None:
        try:
            profile_store = LocalEncryptedProfileStore(
                resolved_settings.profile_storage.path,
                resolved_settings.profile_storage.encryption_key,
            )
            stored_profile = profile_store.load()
        except (
            LinkedInProfileStoreConfigurationError,
            LinkedInProfileStoreInvalidRecordError,
        ) as exc:
            logger.debug("LinkedIn profile store read failed: %s", type(exc).__name__)

    resolved_client = client or LinkedInApiClient(resolved_settings)
    result = resolved_client.test_connection(access_token=access_token)
    if not result.ok:
        return result.to_dict()

    userinfo: dict[str, object] = (
        dict(result.account_summary) if isinstance(result.account_summary, dict) else {}
    )
    profile = assemble_profile(
        userinfo=userinfo,
        user_supplied=user_supplied,
        stored=stored_profile,
    )

    stored = False
    if profile_store is not None:
        try:
            profile_store.save(profile)
            stored = True
        except (LinkedInProfileStoreConfigurationError, OSError) as exc:
            logger.debug("LinkedIn profile store write failed: %s", type(exc).__name__)

    return {
        "ok": True,
        "message": "LinkedIn profile data retrieved successfully",
        "credential_source": credential_source,
        "profile": profile.to_dict(include_email=True),
        "stored": stored,
    }
