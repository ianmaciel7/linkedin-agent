from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from google.adk.auth.auth_handler import AuthHandler

from app.linkedin.client import (
    JsonValue,
    LinkedInApiClient,
    LinkedInApiResponse,
    LinkedInApiTestResult,
)
from app.linkedin.oauth import (
    LinkedInOAuthError,
    LinkedInOAuthSmokeResult,
    build_auth_config,
    run_linkedin_oauth_browser_smoke_test,
    run_linkedin_oauth_smoke_test,
)
from app.linkedin.token_store import (
    LinkedInTokenStoreConfigurationError,
    StoredLinkedInCredential,
)
from app.settings import (
    LinkedInApiSettings,
    LinkedInOAuthSettings,
    LinkedInTokenStorageSettings,
)
from app.tools.linkedin_login_service import _run_linkedin_login_service


@dataclass
class FakeResponse:
    _status_code: int
    _entity: JsonValue

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def entity(self) -> JsonValue:
        return self._entity


@dataclass
class FakeTransport:
    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        self.resource_path = resource_path
        self.access_token = access_token
        return FakeResponse(
            _status_code=200,
            _entity={
                "sub": "user-456",
                "name": "Avery Example",
                "email": "avery@example.com",
            },
        )


@dataclass
class DeniedResponse:
    _status_code: int = 403
    _entity: JsonValue = ""

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def entity(self) -> JsonValue:
        return self._entity


@dataclass
class DeniedTransport:
    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        self.resource_path = resource_path
        self.access_token = access_token
        return DeniedResponse()


@dataclass
class UpstreamFailureResponse:
    _status_code: int = 500
    _entity: JsonValue = ""

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def entity(self) -> JsonValue:
        return self._entity


@dataclass
class UpstreamFailureTransport:
    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        self.resource_path = resource_path
        self.access_token = access_token
        return UpstreamFailureResponse()


@dataclass
class FakeToolContext:
    saved_credential: AuthCredential | None = None
    auth_response: AuthCredential | None = None
    requested_auth_config: object | None = None
    saved_auth_config: object | None = None

    def request_credential(self, auth_config: object) -> None:
        self.requested_auth_config = auth_config

    def get_auth_response(self, auth_config: object) -> AuthCredential | None:
        self.requested_auth_config = auth_config
        return self.auth_response

    async def load_credential(self, auth_config: object) -> AuthCredential | None:
        self.requested_auth_config = auth_config
        return self.saved_credential

    async def save_credential(self, auth_config: object) -> None:
        self.saved_auth_config = auth_config


@dataclass
class FakeTokenStore:
    stored_credential: StoredLinkedInCredential | None = None
    save_calls: list[tuple[str, OAuth2Auth, str | None]] | None = None
    clear_calls: int = 0
    load_error: Exception | None = None
    save_error: Exception | None = None

    def __post_init__(self) -> None:
        if self.save_calls is None:
            self.save_calls = []

    def load(self, oauth: LinkedInOAuthSettings) -> StoredLinkedInCredential | None:
        if self.load_error is not None:
            raise self.load_error
        return self.stored_credential

    def save(
        self,
        oauth: LinkedInOAuthSettings,
        credential: OAuth2Auth,
        *,
        subject: str | None = None,
    ) -> None:
        if self.save_error is not None:
            raise self.save_error
        self.save_calls.append((oauth.credential_key, credential, subject))
        self.stored_credential = StoredLinkedInCredential.from_oauth2(credential)

    def clear(self, oauth: LinkedInOAuthSettings) -> bool:
        self.clear_calls += 1
        had_credential = self.stored_credential is not None
        self.stored_credential = None
        return had_credential


def fake_browser_login_runner(
    settings: LinkedInApiSettings,
) -> LinkedInOAuthSmokeResult:
    assert settings.oauth is not None
    return LinkedInOAuthSmokeResult(
        ok=True,
        message="LinkedIn OAuth smoke test succeeded",
        access_token="browser-token-123",
        expires_at=12345.0,
        expires_in=3600,
        userinfo={
            "sub": "user-789",
            "name": "Jordan Example",
            "email": "jordan@example.com",
        },
        status_code=200,
    )


def fake_browser_login_error_runner(
    settings: LinkedInApiSettings,
) -> LinkedInOAuthSmokeResult:
    raise LinkedInOAuthError("LinkedIn OAuth retornou state diferente do esperado")


def test_run_linkedin_login_service_with_fake_transport() -> None:
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token="token-123",
        test_url="https://example.com/test",
        timeout_seconds=3.0,
    )
    client = LinkedInApiClient(settings, transport=transport)

    result = asyncio.run(_run_linkedin_login_service(settings=settings, client=client))

    assert (
        result
        == LinkedInApiTestResult(
            ok=True,
            message="LinkedIn API test succeeded",
            status_code=200,
            account_summary={
                "sub": "user-456",
                "name": "Avery Example",
            },
        ).to_dict()
    )
    assert transport.resource_path == "/test"
    assert transport.access_token == "token-123"


def test_run_linkedin_login_service_requests_oauth_when_no_credential_is_available() -> (
    None
):
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token=None,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
    )
    client = LinkedInApiClient(settings, transport=transport)
    tool_context = FakeToolContext()

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
            browser_login_runner=fake_browser_login_runner,
        )
    )

    assert result["ok"] is True
    assert result["status_code"] == 200
    assert result["account_summary"] == {
        "sub": "user-789",
        "name": "Jordan Example",
    }
    assert tool_context.requested_auth_config is None


def test_run_linkedin_login_service_reuses_secure_token_store_before_browser_flow() -> (
    None
):
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token=None,
        test_url="https://example.com/test",
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
        token_storage=LinkedInTokenStorageSettings(
            path=".secrets/linkedin-token.enc",
            encryption_key="unused-for-fake-store",
        ),
    )
    client = LinkedInApiClient(settings, transport=transport)
    token_store = FakeTokenStore(
        stored_credential=StoredLinkedInCredential(access_token="stored-token-123")
    )

    def fail_if_called(_settings: LinkedInApiSettings) -> LinkedInOAuthSmokeResult:
        raise AssertionError("browser flow should not run when stored token is valid")

    result = asyncio.run(
        _run_linkedin_login_service(
            settings=settings,
            client=client,
            browser_login_runner=fail_if_called,
            token_store=token_store,
        )
    )

    assert result["ok"] is True
    assert result["credential_source"] == "secure_token_store"
    assert result["account_summary"] == {
        "sub": "user-456",
        "name": "Avery Example",
    }
    assert transport.access_token == "stored-token-123"


def test_run_linkedin_login_service_clears_rejected_stored_token_and_reauthorizes() -> (
    None
):
    settings = LinkedInApiSettings(
        access_token=None,
        test_url="https://example.com/test",
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
        token_storage=LinkedInTokenStorageSettings(
            path=".secrets/linkedin-token.enc",
            encryption_key="unused-for-fake-store",
        ),
    )
    client = LinkedInApiClient(settings, transport=DeniedTransport())
    token_store = FakeTokenStore(
        stored_credential=StoredLinkedInCredential(access_token="stale-token-123")
    )

    browser_runs: list[str] = []

    def browser_runner(_settings: LinkedInApiSettings) -> LinkedInOAuthSmokeResult:
        browser_runs.append("called")
        return fake_browser_login_runner(_settings)

    result = asyncio.run(
        _run_linkedin_login_service(
            settings=settings,
            client=client,
            browser_login_runner=browser_runner,
            token_store=token_store,
        )
    )

    assert result["ok"] is True
    assert browser_runs == ["called"]
    assert token_store.clear_calls == 1
    assert token_store.stored_credential is not None
    assert token_store.stored_credential.access_token == "browser-token-123"


def test_run_linkedin_login_service_surfaces_secure_storage_configuration_error() -> (
    None
):
    settings = LinkedInApiSettings(
        access_token=None,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://example.com/callback",
        ),
        token_storage=LinkedInTokenStorageSettings(
            path=".secrets/linkedin-token.enc",
            encryption_key="unused-for-fake-store",
        ),
    )
    client = LinkedInApiClient(settings, transport=FakeTransport())
    token_store = FakeTokenStore(
        load_error=LinkedInTokenStoreConfigurationError(
            "LINKEDIN_TOKEN_ENCRYPTION_KEY must be a valid Fernet key"
        )
    )

    result = asyncio.run(
        _run_linkedin_login_service(
            settings=settings,
            client=client,
            tool_context=FakeToolContext(),
            token_store=token_store,
        )
    )

    assert result == {
        "ok": False,
        "message": "LINKEDIN_TOKEN_ENCRYPTION_KEY must be a valid Fernet key",
        "error_code": "missing_configuration",
        "status_code": None,
        "account_summary": None,
    }


def test_run_linkedin_login_service_surfaces_local_oauth_callback_validation_error() -> (
    None
):
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token=None,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
    )
    client = LinkedInApiClient(settings, transport=transport)
    tool_context = FakeToolContext()

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
            browser_login_runner=fake_browser_login_error_runner,
        )
    )

    assert result == {
        "ok": False,
        "message": "LinkedIn OAuth retornou state diferente do esperado",
        "error_code": "oauth_login_failed",
        "status_code": None,
        "account_summary": None,
    }
    assert tool_context.requested_auth_config is None


def test_run_linkedin_login_service_reuses_saved_oauth_credential() -> None:
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token=None,
        test_url="https://example.com/test",
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
    )
    client = LinkedInApiClient(settings, transport=transport)
    tool_context = FakeToolContext(
        saved_credential=AuthCredential(
            auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,
            oauth2=OAuth2Auth(access_token="oauth-token-123"),
        )
    )

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
            browser_login_runner=fake_browser_login_runner,
            token_store=FakeTokenStore(),
        )
    )

    assert result["ok"] is True
    assert result["account_summary"] == {
        "sub": "user-789",
        "name": "Jordan Example",
    }
    assert tool_context.saved_auth_config is None


def test_run_linkedin_login_service_saves_adk_oauth_credential_to_secure_store() -> (
    None
):
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token=None,
        test_url="https://example.com/test",
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://example.com/callback",
        ),
        token_storage=LinkedInTokenStorageSettings(
            path=".secrets/linkedin-token.enc",
            encryption_key="unused-for-fake-store",
        ),
    )
    client = LinkedInApiClient(settings, transport=transport)
    token_store = FakeTokenStore()
    tool_context = FakeToolContext(
        auth_response=AuthCredential(
            auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,
            oauth2=OAuth2Auth(
                access_token="oauth-token-123",
                refresh_token="refresh-token-123",
                expires_at=12345.0,
                expires_in=3600,
            ),
        )
    )

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
            token_store=token_store,
        )
    )

    assert result["ok"] is True
    assert token_store.stored_credential is not None
    assert token_store.stored_credential.access_token == "oauth-token-123"
    assert token_store.stored_credential.refresh_token == "refresh-token-123"


def test_run_linkedin_login_service_maps_permission_denied_after_oauth_auth() -> None:
    settings = LinkedInApiSettings(
        access_token=None,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
    )
    client = LinkedInApiClient(settings, transport=DeniedTransport())
    tool_context = FakeToolContext(
        auth_response=AuthCredential(
            auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,
            oauth2=OAuth2Auth(access_token="oauth-token-123"),
        )
    )

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
            browser_login_runner=lambda _settings: LinkedInOAuthSmokeResult(
                ok=False,
                message="permission denied",
                status_code=403,
                userinfo=None,
            ),
        )
    )

    assert result["ok"] is False
    assert result["status_code"] == 403


def test_run_linkedin_login_service_maps_upstream_failure_after_oauth_auth() -> None:
    settings = LinkedInApiSettings(
        access_token=None,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
    )
    client = LinkedInApiClient(settings, transport=UpstreamFailureTransport())
    tool_context = FakeToolContext(
        auth_response=AuthCredential(
            auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,
            oauth2=OAuth2Auth(access_token="oauth-token-123"),
        )
    )

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
            browser_login_runner=lambda _settings: LinkedInOAuthSmokeResult(
                ok=False,
                message="upstream failure",
                status_code=500,
                userinfo=None,
            ),
        )
    )

    assert result["ok"] is False
    assert result["status_code"] == 500


def test_run_linkedin_login_service_falls_back_to_adk_for_non_loopback_redirect() -> (
    None
):
    transport = FakeTransport()
    settings = LinkedInApiSettings(
        access_token=None,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://example.com/callback",
        ),
    )
    client = LinkedInApiClient(settings, transport=transport)
    tool_context = FakeToolContext()

    result = asyncio.run(
        _run_linkedin_login_service(
            tool_context=tool_context,
            settings=settings,
            client=client,
        )
    )

    assert result["ok"] is False
    assert result["pending_auth"] is True
    assert tool_context.requested_auth_config is not None


@pytest.mark.live
def test_run_linkedin_login_service_against_live_endpoint() -> None:
    try:
        settings = LinkedInApiSettings.from_env()
    except ValueError as exc:
        pytest.skip(str(exc))

    if not settings.access_token:
        pytest.skip("LINKEDIN_ACCESS_TOKEN is required for the current live test path")

    client = LinkedInApiClient(settings)
    result = asyncio.run(_run_linkedin_login_service(settings=settings, client=client))

    assert result["ok"] is True
    assert result["message"] == "LinkedIn API test succeeded"
    assert result["status_code"] == 200
    assert isinstance(result["account_summary"], dict)


@pytest.mark.live
def test_linkedin_oauth_configuration_generates_authorization_url() -> None:
    try:
        settings = LinkedInApiSettings.from_env()
    except ValueError as exc:
        pytest.skip(str(exc))

    if settings.oauth is None:
        pytest.skip(
            "LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET e LINKEDIN_REDIRECT_URI "
            "sao necessarios para testar o fluxo OAuth"
        )

    auth_config = build_auth_config(settings.oauth)
    auth_request = AuthHandler(auth_config).generate_auth_request()
    exchanged = auth_request.exchanged_auth_credential
    oauth2 = exchanged.oauth2 if exchanged else None

    assert oauth2 is not None
    assert oauth2.auth_uri is not None

    parsed = urlparse(oauth2.auth_uri)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "www.linkedin.com"
    assert parsed.path == "/oauth/v2/authorization"
    assert params["client_id"] == [settings.oauth.client_id]
    assert params["redirect_uri"] == [settings.oauth.redirect_uri]
    assert params["response_type"] == ["code"]


@pytest.mark.live
def test_linkedin_oauth_code_exchange_and_userinfo_round_trip() -> None:
    try:
        settings = LinkedInApiSettings.from_env()
    except ValueError as exc:
        pytest.skip(str(exc))

    if settings.oauth is None:
        pytest.skip(
            "LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET e LINKEDIN_REDIRECT_URI "
            "sao necessarios para o smoke test OAuth"
        )

    authorization_code = os.getenv("LINKEDIN_AUTH_CODE", "").strip()
    if not authorization_code:
        pytest.skip(
            "LINKEDIN_AUTH_CODE is required for the OAuth round-trip smoke test"
        )

    try:
        result = run_linkedin_oauth_smoke_test(settings, authorization_code)
    except LinkedInOAuthError as exc:
        pytest.fail(str(exc))

    assert result.ok is True
    assert result.status_code == 200
    assert result.userinfo is not None


@pytest.mark.live
def test_linkedin_oauth_browser_round_trip() -> None:
    try:
        settings = LinkedInApiSettings.from_env()
    except ValueError as exc:
        pytest.skip(str(exc))

    if settings.oauth is None:
        pytest.skip(
            "LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET e LINKEDIN_REDIRECT_URI "
            "sao necessarios para o round-trip automatico"
        )

    try:
        result = run_linkedin_oauth_browser_smoke_test(settings)
    except LinkedInOAuthError as exc:
        pytest.fail(str(exc))

    assert result.ok is True
    assert result.status_code == 200
    assert result.userinfo is not None
