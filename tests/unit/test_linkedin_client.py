from __future__ import annotations

from dataclasses import dataclass, field

from app.linkedin.client import (
    JsonValue,
    LinkedInApiClient,
    LinkedInApiResponse,
    LinkedInApiTestResult,
    RestliLinkedInTransport,
)
from app.settings import LinkedInApiSettings


def make_default_entity() -> JsonValue:
    """Return a JSON-typed fake member payload for tests."""

    return {
        "sub": "user-123",
        "name": "Jane Example",
        "email": "jane@example.com",
    }


@dataclass
class FakeResponse:
    status_code: int
    entity: JsonValue


@dataclass
class FakeTransport:
    status_code: int = 200
    entity: JsonValue = field(default_factory=make_default_entity)

    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        self.resource_path = resource_path
        self.access_token = access_token
        return FakeResponse(status_code=self.status_code, entity=self.entity)


def test_test_connection_returns_success_with_safe_summary() -> None:
    transport = FakeTransport()
    client = LinkedInApiClient(
        LinkedInApiSettings(access_token="token-123"),
        transport=transport,
    )

    result = client.test_connection()

    assert result == LinkedInApiTestResult(
        ok=True,
        message="LinkedIn API test succeeded",
        status_code=200,
        account_summary={
            "sub": "user-123",
            "name": "Jane Example",
            "email": "jane@example.com",
        },
    )
    assert transport.resource_path == "/userinfo"
    assert transport.access_token == "token-123"


def test_test_connection_returns_missing_configuration_without_access_token() -> None:
    client = LinkedInApiClient(
        LinkedInApiSettings(access_token=None),
        transport=FakeTransport(),
    )

    result = client.test_connection()

    assert result.ok is False
    assert result.error_code == "missing_configuration"


def test_test_connection_maps_permission_denied() -> None:
    client = LinkedInApiClient(
        LinkedInApiSettings(access_token="token-123"),
        transport=FakeTransport(status_code=403, entity=""),
    )

    result = client.test_connection()

    assert result.ok is False
    assert result.error_code == "permission_denied"
    assert result.status_code == 403


def test_test_connection_maps_rate_limit() -> None:
    client = LinkedInApiClient(
        LinkedInApiSettings(access_token="token-123"),
        transport=FakeTransport(status_code=429, entity=""),
    )

    result = client.test_connection()

    assert result.ok is False
    assert result.error_code == "rate_limited"
    assert result.status_code == 429


def test_test_connection_maps_timeout_error() -> None:
    class TimeoutTransport:
        def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
            raise TimeoutError("timed out")

    client = LinkedInApiClient(
        LinkedInApiSettings(access_token="token-123"),
        transport=TimeoutTransport(),
    )

    result = client.test_connection()

    assert result.ok is False
    assert result.error_code == "timeout"


def test_restli_transport_normalizes_resource_path() -> None:
    class FakeRestliClient:
        def __init__(self) -> None:
            self.session = type(
                "Session", (), {"send": lambda self, *args, **kwargs: None}
            )()

        def get(self, *, resource_path: str, access_token: str) -> LinkedInApiResponse:
            self.resource_path = resource_path
            self.access_token = access_token
            return FakeResponse(status_code=200, entity={"sub": "user-999"})

    fake_client = FakeRestliClient()
    transport = RestliLinkedInTransport(client=fake_client, timeout_seconds=5.0)

    response = transport.get("/userinfo", "token-123")

    assert response.status_code == 200
    assert response.entity == {"sub": "user-999"}
    assert fake_client.resource_path == "/userinfo"
    assert fake_client.access_token == "token-123"
