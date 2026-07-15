from __future__ import annotations

import socket
from threading import Thread
from urllib.parse import parse_qs, urlparse

import pytest
import requests
from requests.exceptions import Timeout as RequestsTimeout

from app.linkedin.oauth import (
    LinkedInOAuthError,
    LinkedInOAuthRefreshRejectedError,
    LinkedInOAuthRefreshTransientError,
    build_user_authorization_prompt,
    exchange_authorization_code,
    fetch_userinfo,
    generate_authorization_request,
    is_loopback_redirect_uri,
    refresh_access_token,
    run_linkedin_oauth_browser_smoke_test,
    run_linkedin_oauth_smoke_test,
    wait_for_oauth_callback,
)
from app.settings import LinkedInApiSettings, LinkedInOAuthSettings


class FakeResponse:
    def __init__(self, status_code: int, payload: object, text: str = "") -> None:
        self.status_code = status_code
        self.payload = payload
        self.text = text

    def json(self) -> object:
        return self.payload


class FakeSession:
    def __init__(self, post_response: FakeResponse, get_response: FakeResponse) -> None:
        self.post_response = post_response
        self.get_response = get_response

    def post(
        self, url: str, *, data: dict[str, str], headers: dict[str, str], timeout: float
    ) -> FakeResponse:
        self.post_url = url
        self.post_data = data
        self.post_headers = headers
        self.post_timeout = timeout
        return self.post_response

    def get(self, url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
        self.get_url = url
        self.get_headers = headers
        self.get_timeout = timeout
        return self.get_response


class TimeoutSession(FakeSession):
    def post(
        self, url: str, *, data: dict[str, str], headers: dict[str, str], timeout: float
    ) -> FakeResponse:
        raise RequestsTimeout("timed out")


class UserinfoTimeoutSession(FakeSession):
    def get(self, url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
        raise RequestsTimeout("timed out")


def make_oauth_settings() -> LinkedInOAuthSettings:
    return LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8000/callback",
    )


def test_exchange_authorization_code_returns_access_token() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            200,
            {
                "access_token": "token-123",
                "refresh_token": "refresh-123",
                "expires_in": 3600,
            },
        ),
        get_response=FakeResponse(200, {}),
    )

    token = exchange_authorization_code(
        make_oauth_settings(),
        "code-123",
        timeout_seconds=3.0,
        session=session,
    )

    assert token.access_token == "token-123"
    assert token.refresh_token == "refresh-123"
    assert token.expires_in == 3600
    assert token.expires_at is not None
    assert session.post_data["grant_type"] == "authorization_code"
    assert session.post_data["code"] == "code-123"


def test_exchange_authorization_code_raises_on_error() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            400,
            {"error": "invalid_request", "error_description": "bad code"},
            text="bad code",
        ),
        get_response=FakeResponse(200, {}),
    )

    with pytest.raises(LinkedInOAuthError, match="bad code"):
        exchange_authorization_code(
            make_oauth_settings(),
            "code-123",
            timeout_seconds=3.0,
            session=session,
        )


def test_refresh_access_token_returns_refreshed_access_token() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            200,
            {
                "access_token": "token-456",
                "refresh_token": "refresh-456",
                "expires_in": 7200,
            },
        ),
        get_response=FakeResponse(200, {}),
    )

    token = refresh_access_token(
        make_oauth_settings(),
        "refresh-123",
        timeout_seconds=3.0,
        session=session,
    )

    assert token.access_token == "token-456"
    assert token.refresh_token == "refresh-456"
    assert token.expires_in == 7200
    assert session.post_data["grant_type"] == "refresh_token"
    assert session.post_data["refresh_token"] == "refresh-123"


def test_refresh_access_token_rejects_invalid_grant() -> None:
    session = FakeSession(
        post_response=FakeResponse(
            400,
            {"error": "invalid_grant", "error_description": "refresh expired"},
            text="refresh expired",
        ),
        get_response=FakeResponse(200, {}),
    )

    with pytest.raises(
        LinkedInOAuthRefreshRejectedError,
        match="must be authorized again",
    ):
        refresh_access_token(
            make_oauth_settings(),
            "refresh-123",
            timeout_seconds=3.0,
            session=session,
        )


def test_refresh_access_token_maps_timeout_as_transient_failure() -> None:
    with pytest.raises(LinkedInOAuthRefreshTransientError, match="timed out") as exc:
        refresh_access_token(
            make_oauth_settings(),
            "refresh-123",
            timeout_seconds=3.0,
            session=TimeoutSession(
                post_response=FakeResponse(200, {}),
                get_response=FakeResponse(200, {}),
            ),
        )

    assert exc.value.error_code == "timeout"


def test_run_linkedin_oauth_smoke_test_returns_userinfo_summary() -> None:
    session = FakeSession(
        post_response=FakeResponse(200, {"access_token": "token-123"}),
        get_response=FakeResponse(
            200,
            {
                "sub": "user-123",
                "name": "Jane Example",
                "email": "jane@example.com",
            },
        ),
    )
    settings = LinkedInApiSettings(
        access_token=None,
        test_url="https://api.linkedin.com/v2/userinfo",
        timeout_seconds=3.0,
        oauth=make_oauth_settings(),
    )

    result = run_linkedin_oauth_smoke_test(
        settings,
        "code-123",
        session=session,
    )

    assert result.ok is True
    assert result.access_token == "token-123"
    assert result.refresh_token is None
    assert result.userinfo == {
        "sub": "user-123",
        "name": "Jane Example",
        "email": "jane@example.com",
    }


def test_fetch_userinfo_raises_on_empty_token() -> None:
    session = FakeSession(
        post_response=FakeResponse(200, {}),
        get_response=FakeResponse(200, {}),
    )

    with pytest.raises(LinkedInOAuthError, match="Access token"):
        fetch_userinfo(
            "",
            userinfo_url="https://api.linkedin.com/v2/userinfo",
            timeout_seconds=3.0,
            session=session,
        )


def test_fetch_userinfo_maps_timeout_to_safe_oauth_error() -> None:
    session = UserinfoTimeoutSession(
        post_response=FakeResponse(200, {}),
        get_response=FakeResponse(200, {}),
    )

    with pytest.raises(LinkedInOAuthError, match="userinfo request timed out"):
        fetch_userinfo(
            "token-123",
            userinfo_url="https://api.linkedin.com/v2/userinfo",
            timeout_seconds=3.0,
            session=session,
        )


def test_generate_authorization_request_returns_url_and_state() -> None:
    result = generate_authorization_request(make_oauth_settings())

    parsed = urlparse(result.authorization_uri)
    params = parse_qs(parsed.query)

    assert parsed.netloc == "www.linkedin.com"
    assert params["response_type"] == ["code"]
    assert result.state


def test_build_user_authorization_prompt_returns_safe_guidance() -> None:
    result = build_user_authorization_prompt(make_oauth_settings())

    assert result.authorization_url.startswith("https://www.linkedin.com/")
    assert "LinkedIn" in result.prompt_message
    assert "volte para esta conversa" in result.next_step


def test_is_loopback_redirect_uri_matches_local_hosts() -> None:
    assert is_loopback_redirect_uri("http://localhost:8000/callback") is True
    assert is_loopback_redirect_uri("http://127.0.0.1:8000/dev-ui/") is True
    assert is_loopback_redirect_uri("https://example.com/callback") is False


def test_wait_for_oauth_callback_receives_code() -> None:
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )
    authorization_request = generate_authorization_request(oauth)

    def opener(_: str) -> bool:
        def send_callback() -> None:
            requests.get(
                f"http://localhost:{port}/callback",
                params={
                    "code": "code-123",
                    "state": authorization_request.state or "",
                },
                timeout=3.0,
            )

        thread = Thread(target=send_callback, daemon=True)
        thread.start()
        return True

    callback = wait_for_oauth_callback(
        oauth,
        authorization_request.authorization_uri,
        expected_state=authorization_request.state,
        opener=opener,
    )

    assert callback.authorization_code == "code-123"
    assert callback.state == authorization_request.state


def test_wait_for_oauth_callback_rejects_missing_expected_state() -> None:
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )

    with pytest.raises(LinkedInOAuthError, match="sem um state valido"):
        wait_for_oauth_callback(
            oauth,
            "https://www.linkedin.com/oauth/v2/authorization?response_type=code",
            expected_state=None,
            opener=lambda _url: True,
        )


def test_wait_for_oauth_callback_rejects_missing_state_in_callback() -> None:
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )

    def opener(_: str) -> bool:
        def send_callback() -> None:
            requests.get(
                oauth.redirect_uri,
                params={"code": "code-123"},
                timeout=3.0,
            )

        thread = Thread(target=send_callback, daemon=True)
        thread.start()
        return True

    with pytest.raises(LinkedInOAuthError, match="nao retornou state"):
        wait_for_oauth_callback(
            oauth,
            "https://www.linkedin.com/oauth/v2/authorization?response_type=code",
            expected_state="expected-state",
            opener=opener,
        )


def test_wait_for_oauth_callback_rejects_mismatched_state() -> None:
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )

    def opener(_: str) -> bool:
        def send_callback() -> None:
            requests.get(
                oauth.redirect_uri,
                params={"code": "code-123", "state": "wrong-state"},
                timeout=3.0,
            )

        thread = Thread(target=send_callback, daemon=True)
        thread.start()
        return True

    with pytest.raises(LinkedInOAuthError, match="state diferente do esperado"):
        wait_for_oauth_callback(
            oauth,
            "https://www.linkedin.com/oauth/v2/authorization?response_type=code",
            expected_state="expected-state",
            opener=opener,
        )


def test_wait_for_oauth_callback_rejects_provider_error_callback() -> None:
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )

    def opener(_: str) -> bool:
        def send_callback() -> None:
            requests.get(
                oauth.redirect_uri,
                params={
                    "error": "access_denied",
                    "error_description": "user denied",
                    "state": "expected-state",
                },
                timeout=3.0,
            )

        thread = Thread(target=send_callback, daemon=True)
        thread.start()
        return True

    with pytest.raises(LinkedInOAuthError, match="access_denied"):
        wait_for_oauth_callback(
            oauth,
            "https://www.linkedin.com/oauth/v2/authorization?response_type=code",
            expected_state="expected-state",
            opener=opener,
        )


def test_run_linkedin_oauth_browser_smoke_test_completes_round_trip() -> None:
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )
    settings = LinkedInApiSettings(
        access_token=None,
        timeout_seconds=3.0,
        oauth=oauth,
    )
    session = FakeSession(
        post_response=FakeResponse(200, {"access_token": "token-123"}),
        get_response=FakeResponse(
            200,
            {"sub": "user-123", "name": "Jane Example"},
        ),
    )

    def opener(url: str) -> bool:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        expected_state = params["state"][0]

        def send_callback() -> None:
            requests.get(
                oauth.redirect_uri,
                params={"code": "code-123", "state": expected_state},
                timeout=3.0,
            )

        thread = Thread(target=send_callback, daemon=True)
        thread.start()
        return bool(url)

    result = run_linkedin_oauth_browser_smoke_test(
        settings,
        session=session,
        opener=opener,
    )

    assert result.ok is True
    assert result.access_token == "token-123"
    assert result.userinfo == {"sub": "user-123", "name": "Jane Example"}


def test_run_linkedin_oauth_browser_smoke_test_rejects_invalid_state_before_exchange() -> (
    None
):
    port = _find_free_port()
    oauth = LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        callback_timeout_seconds=3.0,
    )
    settings = LinkedInApiSettings(
        access_token=None,
        timeout_seconds=3.0,
        oauth=oauth,
    )
    session = FakeSession(
        post_response=FakeResponse(200, {"access_token": "token-123"}),
        get_response=FakeResponse(200, {"sub": "user-123"}),
    )

    def opener(_: str) -> bool:
        def send_callback() -> None:
            requests.get(
                oauth.redirect_uri,
                params={"code": "code-123", "state": "wrong-state"},
                timeout=3.0,
            )

        thread = Thread(target=send_callback, daemon=True)
        thread.start()
        return True

    with pytest.raises(LinkedInOAuthError, match="state diferente do esperado"):
        run_linkedin_oauth_browser_smoke_test(
            settings,
            session=session,
            opener=opener,
        )

    assert not hasattr(session, "post_url")


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("localhost", 0))
        return int(sock.getsockname()[1])
