from __future__ import annotations

from google.adk.auth.auth_credential import OAuth2Auth

from app.linkedin.credential_lifecycle import resolve_stored_credential
from app.linkedin.oauth import (
    LinkedInOAuthRefreshRejectedError,
    LinkedInOAuthRefreshTransientError,
    LinkedInOAuthToken,
)
from app.linkedin.token_store import (
    StoredLinkedInCredential,
    StoredLinkedInCredentialRecord,
)
from app.settings import LinkedInApiSettings, LinkedInOAuthSettings


class FakeTokenStore:
    def __init__(self, record: StoredLinkedInCredentialRecord | None) -> None:
        self.record = record
        self.clear_calls = 0
        self.saved_credentials: list[OAuth2Auth] = []

    def inspect(
        self, oauth: LinkedInOAuthSettings
    ) -> StoredLinkedInCredentialRecord | None:
        return self.record

    def load(self, oauth: LinkedInOAuthSettings) -> StoredLinkedInCredential | None:
        return None if self.record is None else self.record.credential

    def save(
        self,
        oauth: LinkedInOAuthSettings,
        credential: OAuth2Auth,
        *,
        subject: str | None = None,
    ) -> None:
        self.saved_credentials.append(credential)
        self.record = StoredLinkedInCredentialRecord(
            credential=StoredLinkedInCredential.from_oauth2(credential),
            is_expired=False,
        )

    def clear(self, oauth: LinkedInOAuthSettings) -> bool:
        had_record = self.record is not None
        self.record = None
        self.clear_calls += 1
        return had_record


def _settings() -> LinkedInApiSettings:
    return LinkedInApiSettings(
        access_token=None,
        test_url="https://example.com/test",
        timeout_seconds=3.0,
        oauth=LinkedInOAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="http://localhost:8000/callback",
        ),
    )


def test_resolve_stored_credential_refreshes_expired_token(monkeypatch) -> None:
    token_store = FakeTokenStore(
        StoredLinkedInCredentialRecord(
            credential=StoredLinkedInCredential(
                access_token="expired-token-123",
                refresh_token="refresh-token-123",
                expires_at=100.0,
            ),
            is_expired=True,
        )
    )

    def fake_refresh(
        oauth: LinkedInOAuthSettings,
        refresh_token: str,
        *,
        timeout_seconds: float,
        session=None,
    ) -> LinkedInOAuthToken:
        assert refresh_token == "refresh-token-123"
        return LinkedInOAuthToken(
            access_token="refreshed-token-123",
            refresh_token="refreshed-refresh-123",
            expires_at=500.0,
            expires_in=3600,
        )

    monkeypatch.setattr(
        "app.linkedin.credential_lifecycle.refresh_access_token",
        fake_refresh,
    )

    resolution = resolve_stored_credential(_settings(), token_store)

    assert resolution.credential is not None
    assert resolution.credential.access_token == "refreshed-token-123"
    assert resolution.credential.refresh_token == "refreshed-refresh-123"
    assert resolution.credential_source == "secure_token_store_refresh"
    assert resolution.reauthorization_required is False
    assert token_store.clear_calls == 0
    assert len(token_store.saved_credentials) == 1


def test_resolve_stored_credential_requires_reauth_without_refresh_token() -> None:
    token_store = FakeTokenStore(
        StoredLinkedInCredentialRecord(
            credential=StoredLinkedInCredential(
                access_token="expired-token-123",
                refresh_token=None,
                expires_at=100.0,
            ),
            is_expired=True,
        )
    )

    resolution = resolve_stored_credential(_settings(), token_store)

    assert resolution.credential is None
    assert resolution.error_result is None
    assert resolution.reauthorization_required is True
    assert token_store.clear_calls == 1


def test_resolve_stored_credential_clears_rejected_refresh_token(monkeypatch) -> None:
    token_store = FakeTokenStore(
        StoredLinkedInCredentialRecord(
            credential=StoredLinkedInCredential(
                access_token="expired-token-123",
                refresh_token="refresh-token-123",
                expires_at=100.0,
            ),
            is_expired=True,
        )
    )

    def fake_refresh(
        oauth: LinkedInOAuthSettings,
        refresh_token: str,
        *,
        timeout_seconds: float,
        session=None,
    ) -> LinkedInOAuthToken:
        raise LinkedInOAuthRefreshRejectedError("reject")

    monkeypatch.setattr(
        "app.linkedin.credential_lifecycle.refresh_access_token",
        fake_refresh,
    )

    resolution = resolve_stored_credential(_settings(), token_store)

    assert resolution.credential is None
    assert resolution.reauthorization_required is True
    assert token_store.clear_calls == 1


def test_resolve_stored_credential_returns_transient_refresh_failure(
    monkeypatch,
) -> None:
    token_store = FakeTokenStore(
        StoredLinkedInCredentialRecord(
            credential=StoredLinkedInCredential(
                access_token="expired-token-123",
                refresh_token="refresh-token-123",
                expires_at=100.0,
            ),
            is_expired=True,
        )
    )

    def fake_refresh(
        oauth: LinkedInOAuthSettings,
        refresh_token: str,
        *,
        timeout_seconds: float,
        session=None,
    ) -> LinkedInOAuthToken:
        raise LinkedInOAuthRefreshTransientError(
            "LinkedIn OAuth token refresh timed out",
            error_code="timeout",
        )

    monkeypatch.setattr(
        "app.linkedin.credential_lifecycle.refresh_access_token",
        fake_refresh,
    )

    resolution = resolve_stored_credential(_settings(), token_store)

    assert resolution.credential is None
    assert resolution.error_result is not None
    assert resolution.error_result.to_dict() == {
        "ok": False,
        "message": "LinkedIn OAuth token refresh timed out",
        "error_code": "timeout",
        "status_code": None,
        "account_summary": None,
    }
    assert resolution.reauthorization_required is False
    assert token_store.clear_calls == 0
