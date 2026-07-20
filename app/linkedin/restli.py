"""Shared Rest.li client helpers backed by linkedin-api-client."""

from __future__ import annotations

from typing import Any

from linkedin_api.clients.restli.client import RestliClient

from app.linkedin.typing import RestliSession


def build_restli_client() -> RestliClient:
    """Create the official LinkedIn Rest.li client."""

    return RestliClient()


def configure_default_timeout(client: object, timeout_seconds: float) -> None:
    """Inject a default timeout into the official client's Requests session."""

    session = getattr(client, "session", None)
    if session is None or not _has_send(session):
        return

    original_send = session.send

    def send(prepared_request: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", timeout_seconds)
        return original_send(prepared_request, **kwargs)

    session.send = send


def _has_send(session: object) -> bool:
    return isinstance(session, RestliSession)
