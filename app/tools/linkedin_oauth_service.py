"""LinkedIn OAuth service entry point for ADK."""

from __future__ import annotations

from collections.abc import Callable

from app.linkedin.client import LinkedInApiClient
from app.linkedin.oauth import (
    LinkedInOAuthSmokeResult,
)
from app.linkedin.oauth_service import OAuthService
from app.linkedin.token_store import (
    LinkedInTokenStore,
)
from app.settings import LinkedInApiSettings
from app.tools.linkedin_api_check import LinkedInToolContext


async def run_linkedin_oauth_service(
    tool_context: LinkedInToolContext | None = None,
) -> dict[str, object]:
    """Run the LinkedIn OAuth service.

    Use this tool when the user wants to sign in to LinkedIn, reuse a cached ADK
    credential, or verify that the current OAuth configuration can complete a
    read-only LinkedIn connectivity check. For loopback redirect URIs such as
    `localhost`, the tool prefers the repository-controlled local browser flow;
    otherwise it falls back to ADK-managed authorization. It returns a structured,
    safe result without exposing raw tokens or private profile data.
    """

    return await _run_linkedin_oauth_service(tool_context=tool_context)


async def _run_linkedin_oauth_service(
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
    browser_oauth_runner: Callable[[LinkedInApiSettings], LinkedInOAuthSmokeResult]
    | None = None,
    token_store: LinkedInTokenStore | None = None,
) -> dict[str, object]:
    """Internal testable implementation for the LinkedIn OAuth service."""

    service = OAuthService(
        settings=settings,
        client=client,
        browser_oauth_runner=browser_oauth_runner,
        token_store=token_store,
    )
    return await service.run(tool_context=tool_context)
