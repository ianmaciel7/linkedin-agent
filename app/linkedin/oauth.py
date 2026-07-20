"""Helpers for LinkedIn OAuth verification and local browser smoke tests."""

from __future__ import annotations

import logging
import math
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Empty, Queue
from threading import Thread
from typing import Protocol
from urllib.parse import parse_qs, urlparse

import requests
from google.adk.auth import AuthConfig
from google.adk.auth.auth_credential import (
    AuthCredential,
    AuthCredentialTypes,
    OAuth2Auth,
)
from google.adk.auth.auth_handler import AuthHandler
from google.adk.auth.auth_schemes import OpenIdConnectWithConfig
from requests import RequestException
from requests.exceptions import Timeout as RequestsTimeout

from app.linkedin.typing import ErrorCode, JsonValue
from app.settings import LinkedInApiSettings, LinkedInOAuthSettings

logger = logging.getLogger(__name__)


class OAuthResponse(Protocol):
    """Subset of the requests response API used by the OAuth helpers."""

    @property
    def status_code(self) -> int:
        """Return the HTTP status code."""

    @property
    def text(self) -> str:
        """Return the raw response body."""

    def json(self) -> object:
        """Return the decoded JSON body."""


class OAuthSession(Protocol):
    """Subset of requests.Session used by the manual OAuth smoke helper."""

    def post(
        self,
        url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str],
        timeout: float,
    ) -> OAuthResponse:
        """Send a form-encoded POST request."""

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout: float,
    ) -> OAuthResponse:
        """Send a GET request."""


class LinkedInOAuthError(RuntimeError):
    """Raised when the manual LinkedIn OAuth smoke flow fails."""


class LinkedInOAuthRefreshError(LinkedInOAuthError):
    """Base error for LinkedIn OAuth refresh failures."""


class LinkedInOAuthRefreshRejectedError(LinkedInOAuthRefreshError):
    """Raised when LinkedIn rejects refresh and reauthorization is required."""


class LinkedInOAuthRefreshTransientError(LinkedInOAuthRefreshError):
    """Raised when refresh fails transiently and may succeed on a later retry."""

    def __init__(
        self,
        message: str,
        *,
        error_code: ErrorCode,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class LinkedInOAuthSmokeResult:
    """Structured result for the manual LinkedIn OAuth smoke flow."""

    ok: bool
    message: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: float | None = None
    expires_in: int | None = None
    userinfo: dict[str, str] | None = None
    status_code: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary for scripts and smoke checks."""

        return {
            "ok": self.ok,
            "message": self.message,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "expires_in": self.expires_in,
            "userinfo": self.userinfo,
            "status_code": self.status_code,
        }


@dataclass(frozen=True, slots=True)
class LinkedInOAuthBrowserFlowResult:
    """Authorization URI plus the captured callback response."""

    authorization_uri: str
    authorization_code: str
    state: str | None = None


@dataclass(frozen=True, slots=True)
class LinkedInAuthorizationPrompt:
    """Safe metadata the agent can use to guide a user through consent."""

    authorization_url: str
    prompt_message: str
    next_step: str


@dataclass(frozen=True, slots=True)
class _OAuthCallbackPayload:
    code: str | None = None
    state: str | None = None
    error: str | None = None
    error_description: str | None = None


@dataclass(frozen=True, slots=True)
class LinkedInOAuthToken:
    """Minimal OAuth token fields returned by LinkedIn."""

    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    expires_in: int | None = None


def build_auth_config(oauth: LinkedInOAuthSettings) -> AuthConfig:
    """Build the ADK auth config used for LinkedIn OAuth consent."""

    auth_scheme = OpenIdConnectWithConfig(
        authorization_endpoint=oauth.auth_url,
        token_endpoint=oauth.token_url,
        userinfo_endpoint=oauth.userinfo_url,
        token_endpoint_auth_methods_supported=["client_secret_post"],
        grant_types_supported=["authorization_code"],
        scopes=list(oauth.scopes),
    )
    raw_auth_credential = AuthCredential(
        auth_type=AuthCredentialTypes.OPEN_ID_CONNECT,
        oauth2=OAuth2Auth(
            client_id=oauth.client_id,
            client_secret=oauth.client_secret,
            redirect_uri=oauth.redirect_uri,
            prompt="consent",
            token_endpoint_auth_method="client_secret_post",
        ),
    )
    return AuthConfig(
        auth_scheme=auth_scheme,
        raw_auth_credential=raw_auth_credential,
        credential_key=oauth.credential_key,
    )


def generate_authorization_request(
    oauth: LinkedInOAuthSettings,
) -> LinkedInOAuthBrowserFlowResult:
    """Generate the LinkedIn authorization URI and expected state."""

    auth_request = AuthHandler(build_auth_config(oauth)).generate_auth_request()
    exchanged = auth_request.exchanged_auth_credential
    oauth2 = exchanged.oauth2 if exchanged is not None else None
    if oauth2 is None or oauth2.auth_uri is None:
        raise LinkedInOAuthError(
            "Nao foi possivel gerar a URL de autorizacao do LinkedIn"
        )

    return LinkedInOAuthBrowserFlowResult(
        authorization_uri=oauth2.auth_uri,
        authorization_code="",
        state=oauth2.state,
    )


def build_user_authorization_prompt(
    oauth: LinkedInOAuthSettings,
) -> LinkedInAuthorizationPrompt:
    """Return safe, user-facing guidance for the LinkedIn consent step."""

    authorization_request = generate_authorization_request(oauth)
    return LinkedInAuthorizationPrompt(
        authorization_url=authorization_request.authorization_uri,
        prompt_message=(
            "Abra o link do LinkedIn para autorizar o login e concluir a "
            "verificacao OAuth."
        ),
        next_step=(
            "Depois de aprovar o acesso no LinkedIn, volte para esta conversa. "
            "Se a interface nao continuar sozinha, peca para tentar novamente."
        ),
    )


def is_loopback_redirect_uri(redirect_uri: str) -> bool:
    """Return whether the redirect URI points to a local loopback address."""

    parsed = urlparse(redirect_uri)
    return parsed.hostname in {"localhost", "127.0.0.1"}


def wait_for_oauth_callback(
    oauth: LinkedInOAuthSettings,
    authorization_uri: str,
    *,
    expected_state: str | None,
    opener=webbrowser.open,
) -> LinkedInOAuthBrowserFlowResult:
    """Open the browser and wait for the LinkedIn redirect callback locally."""

    parsed_redirect = urlparse(oauth.redirect_uri)
    normalized_expected_state = (expected_state or "").strip()
    if not normalized_expected_state:
        raise LinkedInOAuthError(
            "Nao foi possivel iniciar o OAuth local do LinkedIn sem um state valido"
        )
    if parsed_redirect.scheme != "http":
        raise LinkedInOAuthError(
            "O teste automatico via pytest exige LINKEDIN_REDIRECT_URI com esquema http"
        )
    if parsed_redirect.hostname not in {"localhost", "127.0.0.1"}:
        raise LinkedInOAuthError(
            "O teste automatico via pytest exige LINKEDIN_REDIRECT_URI apontando para localhost ou 127.0.0.1"
        )
    if parsed_redirect.port is None:
        raise LinkedInOAuthError(
            "O teste automatico via pytest exige porta explicita no LINKEDIN_REDIRECT_URI"
        )

    callback_path = parsed_redirect.path or "/"
    callback_queue: Queue[_OAuthCallbackPayload] = Queue(maxsize=1)

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != callback_path:
                self.send_response(404)
                self.end_headers()
                return

            params = parse_qs(parsed.query)
            payload = _OAuthCallbackPayload(
                code=_first_query_value(params, "code"),
                state=_first_query_value(params, "state"),
                error=_first_query_value(params, "error"),
                error_description=_first_query_value(params, "error_description"),
            )
            callback_queue.put(payload)

            body = (
                b"<html><body><h1>LinkedIn OAuth recebido.</h1>"
                b"<p>Voce pode fechar esta janela e voltar ao terminal.</p>"
                b"</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(
        (parsed_redirect.hostname, parsed_redirect.port),
        CallbackHandler,
    )
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        opener(authorization_uri)
        try:
            payload = callback_queue.get(timeout=oauth.callback_timeout_seconds)
        except Empty as exc:
            raise LinkedInOAuthError(
                "Tempo esgotado aguardando o callback OAuth do LinkedIn. "
                f"Abra manualmente esta URL se necessario: {authorization_uri}"
            ) from exc
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    if payload.error:
        raise LinkedInOAuthError(
            f"LinkedIn OAuth retornou erro: {payload.error} ({payload.error_description or 'sem detalhes'})"
        )
    if not payload.code:
        raise LinkedInOAuthError(
            "LinkedIn OAuth nao retornou authorization code no callback"
        )
    if payload.state is None:
        raise LinkedInOAuthError("LinkedIn OAuth nao retornou state no callback")
    if payload.state != normalized_expected_state:
        raise LinkedInOAuthError("LinkedIn OAuth retornou state diferente do esperado")

    return LinkedInOAuthBrowserFlowResult(
        authorization_uri=authorization_uri,
        authorization_code=payload.code,
        state=payload.state,
    )


def exchange_authorization_code(
    oauth: LinkedInOAuthSettings,
    authorization_code: str,
    *,
    timeout_seconds: float,
    session: OAuthSession | None = None,
) -> LinkedInOAuthToken:
    """Exchange a LinkedIn authorization code for an access token."""

    code = authorization_code.strip()
    if not code:
        raise LinkedInOAuthError("Authorization code must not be empty")

    token = _exchange_linkedin_token(
        oauth=oauth,
        grant_payload={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth.redirect_uri,
        },
        timeout_seconds=timeout_seconds,
        session=session,
        action_name="token exchange",
    )
    if isinstance(token, LinkedInOAuthToken):
        return token
    raise AssertionError(
        "authorization-code flow must not yield refresh-specific errors"
    )


def refresh_access_token(
    oauth: LinkedInOAuthSettings,
    refresh_token: str,
    *,
    timeout_seconds: float,
    session: OAuthSession | None = None,
) -> LinkedInOAuthToken:
    """Refresh an expired LinkedIn access token with a stored refresh token."""

    normalized_refresh_token = refresh_token.strip()
    if not normalized_refresh_token:
        raise LinkedInOAuthRefreshRejectedError(
            "Stored LinkedIn credential does not include a usable refresh token"
        )

    logger.info(
        "LinkedIn OAuth refresh attempt for credential key %s",
        oauth.credential_key,
    )
    token = _exchange_linkedin_token(
        oauth=oauth,
        grant_payload={
            "grant_type": "refresh_token",
            "refresh_token": normalized_refresh_token,
        },
        timeout_seconds=timeout_seconds,
        session=session,
        action_name="refresh",
    )
    if isinstance(token, LinkedInOAuthToken):
        logger.info(
            "LinkedIn OAuth refresh succeeded for credential key %s",
            oauth.credential_key,
        )
        return token
    raise AssertionError("refresh flow must return a LinkedInOAuthToken")


def _exchange_linkedin_token(
    *,
    oauth: LinkedInOAuthSettings,
    grant_payload: dict[str, str],
    timeout_seconds: float,
    session: OAuthSession | None,
    action_name: str,
) -> LinkedInOAuthToken:
    http = session or requests.Session()
    try:
        response = http.post(
            oauth.token_url,
            data={
                **grant_payload,
                "client_id": oauth.client_id,
                "client_secret": oauth.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=timeout_seconds,
        )
    except RequestsTimeout as exc:
        raise LinkedInOAuthRefreshTransientError(
            "LinkedIn OAuth token refresh timed out"
            if action_name == "refresh"
            else "LinkedIn token exchange timed out",
            error_code="timeout",
        ) from exc
    except RequestException as exc:
        raise LinkedInOAuthRefreshTransientError(
            "LinkedIn OAuth token refresh failed before a response was received"
            if action_name == "refresh"
            else "LinkedIn token exchange failed before a response was received",
            error_code="upstream_failure",
        ) from exc

    payload = response.json()
    if not isinstance(payload, dict):
        if action_name == "refresh":
            raise LinkedInOAuthRefreshTransientError(
                "LinkedIn OAuth token refresh returned an invalid response",
                error_code="upstream_failure",
                status_code=response.status_code,
            )
        raise LinkedInOAuthError(
            f"LinkedIn token exchange returned non-JSON payload with status {response.status_code}"
        )

    access_token = payload.get("access_token")
    if response.status_code == 200 and isinstance(access_token, str) and access_token:
        refresh_token = payload.get("refresh_token")
        expires_in_value = payload.get("expires_in")
        expires_in = _coerce_expires_in(expires_in_value)
        expires_at = time.time() + expires_in if expires_in is not None else None

        return LinkedInOAuthToken(
            access_token=access_token,
            refresh_token=refresh_token.strip() or None
            if isinstance(refresh_token, str)
            else None,
            expires_at=expires_at,
            expires_in=expires_in,
        )

    message = payload.get("error_description") or payload.get("error") or response.text
    if action_name != "refresh":
        raise LinkedInOAuthError(
            f"LinkedIn token exchange failed with status {response.status_code}: {message}"
        )

    error = payload.get("error")
    error_text = error.strip() if isinstance(error, str) else ""
    if response.status_code in {400, 401} and error_text in {
        "invalid_grant",
        "invalid_request",
        "unauthorized_client",
    }:
        logger.info(
            "LinkedIn OAuth refresh rejected for credential key %s",
            oauth.credential_key,
        )
        raise LinkedInOAuthRefreshRejectedError(
            "Stored LinkedIn credential is no longer valid and must be authorized again"
        )

    if response.status_code == 429:
        raise LinkedInOAuthRefreshTransientError(
            "LinkedIn OAuth token refresh is rate limited",
            error_code="rate_limited",
            status_code=response.status_code,
        )
    if response.status_code == 408:
        raise LinkedInOAuthRefreshTransientError(
            "LinkedIn OAuth token refresh timed out",
            error_code="timeout",
            status_code=response.status_code,
        )
    raise LinkedInOAuthRefreshTransientError(
        f"LinkedIn OAuth token refresh failed with status {response.status_code}",
        error_code="upstream_failure",
        status_code=response.status_code,
    )


def fetch_userinfo(
    access_token: str,
    *,
    userinfo_url: str,
    timeout_seconds: float,
    session: OAuthSession | None = None,
) -> tuple[int, JsonValue]:
    """Fetch `/userinfo` with the supplied LinkedIn OAuth access token."""

    token = access_token.strip()
    if not token:
        raise LinkedInOAuthError("Access token must not be empty")

    http = session or requests.Session()
    try:
        response = http.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
        )
    except RequestsTimeout as exc:
        raise LinkedInOAuthError("LinkedIn userinfo request timed out") from exc
    except RequestException as exc:
        raise LinkedInOAuthError(
            "LinkedIn userinfo request failed before a response was received"
        ) from exc

    payload = response.json()
    return response.status_code, payload if isinstance(
        payload, (dict, list, str, int, float, bool)
    ) or payload is None else {}


def run_linkedin_oauth_smoke_test(
    settings: LinkedInApiSettings,
    authorization_code: str,
    *,
    session: OAuthSession | None = None,
) -> LinkedInOAuthSmokeResult:
    """Exchange a LinkedIn auth code and call the configured read-only endpoint."""

    if settings.oauth is None:
        raise LinkedInOAuthError(
            "LinkedIn OAuth settings are required for the manual OAuth smoke test"
        )

    token = exchange_authorization_code(
        settings.oauth,
        authorization_code,
        timeout_seconds=settings.timeout_seconds,
        session=session,
    )
    status_code, payload = fetch_userinfo(
        token.access_token,
        userinfo_url=settings.test_url,
        timeout_seconds=settings.timeout_seconds,
        session=session,
    )
    userinfo = _extract_userinfo_summary(payload)
    if status_code != 200:
        raise LinkedInOAuthError(
            f"LinkedIn userinfo request failed with status {status_code}"
        )

    return LinkedInOAuthSmokeResult(
        ok=True,
        message="LinkedIn OAuth smoke test succeeded",
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        expires_at=token.expires_at,
        expires_in=token.expires_in,
        userinfo=userinfo,
        status_code=status_code,
    )


def run_linkedin_oauth_browser_smoke_test(
    settings: LinkedInApiSettings,
    *,
    session: OAuthSession | None = None,
    opener=webbrowser.open,
) -> LinkedInOAuthSmokeResult:
    """Run a browser-driven OAuth smoke test close to a local production flow."""

    if settings.oauth is None:
        raise LinkedInOAuthError(
            "LinkedIn OAuth settings are required for the browser smoke test"
        )

    authorization_request = generate_authorization_request(settings.oauth)
    callback_result = wait_for_oauth_callback(
        settings.oauth,
        authorization_request.authorization_uri,
        expected_state=authorization_request.state,
        opener=opener,
    )
    return run_linkedin_oauth_smoke_test(
        settings,
        callback_result.authorization_code,
        session=session,
    )


def _extract_userinfo_summary(payload: JsonValue) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None

    summary_keys = ("sub", "name", "given_name", "family_name", "email")
    summary = {
        key: str(payload[key])
        for key in summary_keys
        if key in payload and payload[key] not in (None, "")
    }
    return summary or None


def _first_query_value(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _coerce_expires_in(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if not math.isfinite(value) or value <= 0:
            return None
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            parsed = float(stripped)
        except ValueError:
            return None
        if not math.isfinite(parsed) or parsed <= 0:
            return None
        return int(parsed)
    return None
