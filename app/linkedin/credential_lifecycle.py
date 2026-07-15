"""Shared lifecycle helpers for stored LinkedIn OAuth credentials."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from google.adk.auth.auth_credential import OAuth2Auth

from app.linkedin.client import LinkedInApiTestResult
from app.linkedin.oauth import (
    LinkedInOAuthRefreshRejectedError,
    LinkedInOAuthRefreshTransientError,
    refresh_access_token,
)
from app.linkedin.token_store import (
    LinkedInTokenStore,
    LinkedInTokenStoreConfigurationError,
    LinkedInTokenStoreInvalidRecordError,
    StoredLinkedInCredential,
)
from app.settings import LinkedInApiSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredCredentialResolution:
    """Result of resolving a stored credential for immediate use."""

    credential: StoredLinkedInCredential | None = None
    error_result: LinkedInApiTestResult | None = None
    reauthorization_required: bool = False
    credential_source: str | None = None


def resolve_stored_credential(
    settings: LinkedInApiSettings,
    token_store: LinkedInTokenStore | None,
) -> StoredCredentialResolution:
    """Resolve a stored credential, refreshing it when safe and possible."""

    oauth = settings.oauth
    if oauth is None or token_store is None:
        return StoredCredentialResolution()

    try:
        stored_record = token_store.inspect(oauth)
    except LinkedInTokenStoreConfigurationError as exc:
        return StoredCredentialResolution(
            error_result=LinkedInApiTestResult(
                ok=False,
                message=str(exc),
                error_code="missing_configuration",
            )
        )
    except LinkedInTokenStoreInvalidRecordError:
        token_store.clear(oauth)
        logger.info(
            "LinkedIn stored credential was invalid for credential key %s",
            oauth.credential_key,
        )
        return StoredCredentialResolution(reauthorization_required=True)

    if stored_record is None:
        return StoredCredentialResolution()

    if not stored_record.is_expired:
        return StoredCredentialResolution(
            credential=stored_record.credential,
            credential_source="secure_token_store",
        )

    logger.info(
        "LinkedIn stored credential expired for credential key %s",
        oauth.credential_key,
    )
    refresh_token = stored_record.credential.refresh_token
    if not refresh_token:
        logger.info(
            "LinkedIn stored credential cannot be refreshed for credential key %s",
            oauth.credential_key,
        )
        token_store.clear(oauth)
        return StoredCredentialResolution(reauthorization_required=True)

    try:
        refreshed_token = refresh_access_token(
            oauth,
            refresh_token,
            timeout_seconds=settings.timeout_seconds,
        )
    except LinkedInOAuthRefreshRejectedError:
        token_store.clear(oauth)
        return StoredCredentialResolution(reauthorization_required=True)
    except LinkedInOAuthRefreshTransientError as exc:
        logger.info(
            "LinkedIn OAuth refresh failed transiently for credential key %s",
            oauth.credential_key,
        )
        return StoredCredentialResolution(
            error_result=LinkedInApiTestResult(
                ok=False,
                message=str(exc),
                error_code=exc.error_code,
                status_code=exc.status_code,
            )
        )

    refreshed_oauth = OAuth2Auth(
        client_id=oauth.client_id,
        redirect_uri=oauth.redirect_uri,
        access_token=refreshed_token.access_token,
        refresh_token=refreshed_token.refresh_token or refresh_token,
        expires_at=refreshed_token.expires_at,
        expires_in=refreshed_token.expires_in,
    )
    try:
        token_store.save(oauth, refreshed_oauth)
    except LinkedInTokenStoreConfigurationError as exc:
        return StoredCredentialResolution(
            error_result=LinkedInApiTestResult(
                ok=False,
                message=str(exc),
                error_code="missing_configuration",
            )
        )

    return StoredCredentialResolution(
        credential=StoredLinkedInCredential.from_oauth2(refreshed_oauth),
        credential_source="secure_token_store_refresh",
    )
