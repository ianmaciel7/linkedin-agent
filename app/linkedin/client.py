"""Read-only LinkedIn API client helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeAlias
from urllib.parse import urlparse

from linkedin_api.clients.restli.client import RestliClient
from requests import RequestException
from requests.exceptions import Timeout as RequestsTimeout

from app.settings import LinkedInApiSettings

ErrorCode = Literal[
    "missing_configuration",
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


class RestliSession(Protocol):
    """Protocol for the subset of Requests session behavior we rely on."""

    def send(self, prepared_request: Any, **kwargs: Any) -> Any:
        """Send a prepared request."""


class RestliClientProtocol(Protocol):
    """Protocol for the subset of RestliClient used by the transport."""

    session: RestliSession

    def get(self, *, resource_path: str, access_token: str) -> LinkedInApiResponse:
        """Perform a GET request via the official client shape."""


class LinkedInApiClientError(RuntimeError):
    """Normalized error raised by the LinkedIn client adapter."""

    def __init__(self, message: str, error_code: ErrorCode) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True, slots=True)
class LinkedInApiTestResult:
    """Structured result for the LinkedIn API test helper."""

    ok: bool
    message: str
    error_code: ErrorCode | None = None
    status_code: int | None = None
    account_summary: dict[str, str] | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary for tool responses and tests."""

        return {
            "ok": self.ok,
            "message": self.message,
            "error_code": self.error_code,
            "status_code": self.status_code,
            "account_summary": self.account_summary,
        }


class RestliLinkedInTransport:
    """Default transport backed by the official LinkedIn client library."""

    def __init__(
        self,
        client: RestliClientProtocol | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._client = client or RestliClient()
        self._timeout_seconds = timeout_seconds
        self._configure_timeout()

    def _configure_timeout(self) -> None:
        session = getattr(self._client, "session", None)
        if session is None or not hasattr(session, "send"):
            return

        original_send = session.send

        def send(prepared_request, **kwargs):
            kwargs.setdefault("timeout", self._timeout_seconds)
            return original_send(prepared_request, **kwargs)

        session.send = send

    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        try:
            return self._client.get(
                resource_path=resource_path,
                access_token=access_token,
            )
        except RequestsTimeout as exc:
            raise LinkedInApiClientError(
                "LinkedIn API request timed out",
                error_code="timeout",
            ) from exc
        except RequestException as exc:
            raise LinkedInApiClientError(
                "LinkedIn API request failed before a response was received",
                error_code="upstream_failure",
            ) from exc


class LinkedInApiClient:
    """Small read-only adapter for testing LinkedIn API connectivity."""

    def __init__(
        self,
        settings: LinkedInApiSettings,
        transport: LinkedInTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport or RestliLinkedInTransport(
            timeout_seconds=settings.timeout_seconds
        )

    def test_connection(self, access_token: str | None = None) -> LinkedInApiTestResult:
        """Call the configured LinkedIn test endpoint and normalize the result."""

        resource_path = self._resource_path_from_endpoint(self._settings.test_url)
        resolved_access_token = access_token or self._settings.access_token
        if not resolved_access_token:
            return LinkedInApiTestResult(
                ok=False,
                message="LinkedIn API access token is not available",
                error_code="missing_configuration",
            )

        try:
            response = self._transport.get(resource_path, resolved_access_token)
        except LinkedInApiClientError as exc:
            return LinkedInApiTestResult(
                ok=False, message=str(exc), error_code=exc.error_code
            )
        except TimeoutError:
            return LinkedInApiTestResult(
                ok=False,
                message="LinkedIn API request timed out",
                error_code="timeout",
            )

        if 200 <= response.status_code < 300:
            return LinkedInApiTestResult(
                ok=True,
                message="LinkedIn API test succeeded",
                status_code=response.status_code,
                account_summary=self._extract_account_summary(response.entity),
            )

        error_code = self._map_status_code(response.status_code)
        return LinkedInApiTestResult(
            ok=False,
            message=self._message_for_status_code(response.status_code, error_code),
            error_code=error_code,
            status_code=response.status_code,
        )

    @staticmethod
    def _resource_path_from_endpoint(test_url: str) -> str:
        parsed_url = urlparse(test_url)
        resource_path = parsed_url.path or test_url
        if resource_path.startswith("/v2/"):
            resource_path = resource_path.removeprefix("/v2")
        if not resource_path.startswith("/"):
            resource_path = f"/{resource_path}"
        return resource_path

    @staticmethod
    def _map_status_code(status_code: int) -> ErrorCode:
        if status_code in {401, 403}:
            return "permission_denied"
        if status_code == 429:
            return "rate_limited"
        if status_code == 408:
            return "timeout"
        return "upstream_failure"

    @staticmethod
    def _message_for_status_code(status_code: int, error_code: ErrorCode) -> str:
        if error_code == "permission_denied":
            return "LinkedIn API rejected the request due to missing or invalid permissions"
        if error_code == "rate_limited":
            return "LinkedIn API rate limit reached for the test request"
        if error_code == "timeout":
            return "LinkedIn API request timed out"
        return f"LinkedIn API returned unexpected status {status_code}"

    @staticmethod
    def _extract_account_summary(entity: object) -> dict[str, str] | None:
        if not isinstance(entity, dict):
            return None

        summary_keys = ("sub", "name", "given_name", "family_name", "email")
        summary = {
            key: str(entity[key])
            for key in summary_keys
            if key in entity and entity[key] not in (None, "")
        }
        return summary or None
