"""Shared typing contracts for the LinkedIn integration package."""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypeAlias, runtime_checkable

ErrorCode = Literal[
    "missing_configuration",
    "invalid_stored_credential",
    "oauth_login_failed",
    "permission_denied",
    "rate_limited",
    "timeout",
    "upstream_failure",
]

JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


class LinkedInApiResponse(Protocol):
    """Protocol for the response object returned by the LinkedIn API client."""

    @property
    def status_code(self) -> int:
        """Return the HTTP status code."""

    @property
    def entity(self) -> JsonValue:
        """Return the decoded response payload."""


class LinkedInTransport(Protocol):
    """Protocol for the LinkedIn API client used by the helper."""

    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        """Perform a read-only GET request and return the LinkedIn response."""


@runtime_checkable
class RestliSession(Protocol):
    """Protocol for the subset of Requests session behavior we rely on."""

    def send(self, prepared_request: Any, **kwargs: Any) -> Any:
        """Send a prepared request."""


class RestliClientProtocol(Protocol):
    """Protocol for the subset of RestliClient used by the transport."""

    session: RestliSession

    def get(self, *, resource_path: str, access_token: str) -> LinkedInApiResponse:
        """Perform a GET request via the official client shape."""


class RestliFinderClientProtocol(Protocol):
    """Protocol for RestliClient finder requests used by versioned APIs."""

    session: RestliSession

    def finder(
        self,
        *,
        resource_path: str,
        finder_name: str,
        query_params: dict[str, object],
        access_token: str,
        version_string: str,
    ) -> object:
        """Perform a finder request via the official client shape."""
