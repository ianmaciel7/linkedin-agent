"""Helpers for LinkedIn OAuth verification and local browser smoke tests."""

from __future__ import annotations

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

from app.linkedin.client import JsonValue
from app.settings import LinkedInApiSettings, LinkedInOAuthSettings


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


@dataclass(frozen=True, slots=True)
class LinkedInOAuthSmokeResult:
    """Structured result for the manual LinkedIn OAuth smoke flow."""

    ok: bool
    message: str
    access_token: str | None = None
    userinfo: dict[str, str] | None = None
    status_code: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary for scripts and smoke checks."""

        return {
            "ok": self.ok,
            "message": self.message,
            "access_token": self.access_token,
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
    opener=webbrowser.open,
) -> LinkedInOAuthBrowserFlowResult:
    """Open the browser and wait for the LinkedIn redirect callback locally."""

    parsed_redirect = urlparse(oauth.redirect_uri)
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
) -> str:
    """Exchange a LinkedIn authorization code for an access token."""

    code = authorization_code.strip()
    if not code:
        raise LinkedInOAuthError("Authorization code must not be empty")

    http = session or requests.Session()
    response = http.post(
        oauth.token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth.redirect_uri,
            "client_id": oauth.client_id,
            "client_secret": oauth.client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout_seconds,
    )
    payload = response.json()
    if not isinstance(payload, dict):
        raise LinkedInOAuthError(
            f"LinkedIn token exchange returned non-JSON payload with status {response.status_code}"
        )

    access_token = payload.get("access_token")
    if (
        response.status_code != 200
        or not isinstance(access_token, str)
        or not access_token
    ):
        message = (
            payload.get("error_description") or payload.get("error") or response.text
        )
        raise LinkedInOAuthError(
            f"LinkedIn token exchange failed with status {response.status_code}: {message}"
        )

    return access_token


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
    response = http.get(
        userinfo_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout_seconds,
    )
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

    access_token = exchange_authorization_code(
        settings.oauth,
        authorization_code,
        timeout_seconds=settings.timeout_seconds,
        session=session,
    )
    status_code, payload = fetch_userinfo(
        access_token,
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
        access_token=access_token,
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
