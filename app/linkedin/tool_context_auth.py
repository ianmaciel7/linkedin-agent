"""ADK ToolContext helpers for LinkedIn OAuth credential reuse."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from google.adk.auth import AuthConfig
from google.adk.auth.auth_credential import AuthCredential

from app.linkedin.client import LinkedInApiTestResult


class LinkedInToolContext(Protocol):
    """Subset of ADK tool context behavior required by LinkedIn auth helpers."""

    def request_credential(self, auth_config: AuthConfig) -> None:
        """Request OAuth credentials for the given auth config."""

    def get_auth_response(self, auth_config: AuthConfig) -> AuthCredential | None:
        """Return a completed OAuth response when one is already available."""

    async def load_credential(self, auth_config: AuthConfig) -> AuthCredential | None:
        """Load a previously saved credential for the given auth config."""

    async def save_credential(self, auth_config: AuthConfig) -> None:
        """Persist the exchanged credential for the given auth config."""


@dataclass(frozen=True, slots=True)
class ToolContextCredentialResolution:
    """Outcome of attempting to reuse a LinkedIn ADK ToolContext credential."""

    result: LinkedInApiTestResult | None = None
    credential_source: str | None = None
    browser_reauthorization_required: bool = False


async def load_saved_credential(
    tool_context: LinkedInToolContext,
    auth_config: AuthConfig,
) -> AuthCredential | None:
    """Load a saved ADK credential and suppress missing-state errors."""

    try:
        return await tool_context.load_credential(auth_config)
    except ValueError:
        return None


async def save_credential(
    tool_context: LinkedInToolContext,
    auth_config: AuthConfig,
    credential: AuthCredential,
) -> None:
    """Save an exchanged ADK credential and suppress unsupported-state errors."""

    try:
        await tool_context.save_credential(
            auth_config.model_copy(update={"exchanged_auth_credential": credential})
        )
    except ValueError:
        return


def access_token_from_credential(credential: AuthCredential | None) -> str | None:
    """Extract a LinkedIn OAuth access token from an ADK credential."""

    if credential is None or credential.oauth2 is None:
        return None
    return credential.oauth2.access_token
