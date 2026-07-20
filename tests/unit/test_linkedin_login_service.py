from __future__ import annotations

import asyncio

from cryptography.fernet import Fernet
from google.adk.auth.auth_credential import OAuth2Auth

from app.linkedin.client import JsonValue, LinkedInApiClient, LinkedInApiResponse
from app.linkedin.login_service import LinkedInLoginService
from app.linkedin.models import MemberProfile
from app.linkedin.oauth import LinkedInOAuthSmokeResult
from app.linkedin.profile_store import LocalEncryptedProfileStore
from app.linkedin.token_store import (
    StoredLinkedInCredential,
    StoredLinkedInCredentialRecord,
)
from app.settings import (
    LinkedInApiSettings,
    LinkedInOAuthSettings,
    LinkedInProfileStorageSettings,
)


class FakeResponse:
    def __init__(self, status_code: int, entity: JsonValue) -> None:
        self._status_code = status_code
        self._entity = entity

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def entity(self) -> JsonValue:
        return self._entity


class FakeTransport:
    def __init__(self, entity: JsonValue) -> None:
        self._entity = entity
        self.access_token = ""

    def get(self, resource_path: str, access_token: str) -> LinkedInApiResponse:
        self.access_token = access_token
        return FakeResponse(status_code=200, entity=self._entity)


class FakeTokenStore:
    def __init__(self, credential: StoredLinkedInCredential | None = None) -> None:
        self.credential = credential
        self.save_calls: list[tuple[str, str | None]] = []

    def inspect(
        self, oauth: LinkedInOAuthSettings
    ) -> StoredLinkedInCredentialRecord | None:
        if self.credential is None:
            return None
        is_expired = (
            self.credential.expires_at is not None and self.credential.expires_at <= 0
        )
        return StoredLinkedInCredentialRecord(
            credential=self.credential,
            is_expired=is_expired,
        )

    def load(self, oauth: LinkedInOAuthSettings) -> StoredLinkedInCredential | None:
        return self.credential

    def save(
        self,
        oauth: LinkedInOAuthSettings,
        credential: OAuth2Auth,
        *,
        subject: str | None = None,
    ) -> None:
        self.save_calls.append(((credential.access_token or ""), subject))
        self.credential = StoredLinkedInCredential.from_oauth2(credential)

    def clear(self, oauth: LinkedInOAuthSettings) -> bool:
        had_credential = self.credential is not None
        self.credential = None
        return had_credential


def _oauth_settings() -> LinkedInOAuthSettings:
    return LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8000/callback",
    )


def test_login_service_filters_account_summary_for_browser_flow() -> None:
    settings = LinkedInApiSettings(access_token=None, oauth=_oauth_settings())
    client = LinkedInApiClient(
        settings,
        transport=FakeTransport({"sub": "unused", "name": "unused"}),
    )

    def browser_runner(_: LinkedInApiSettings) -> LinkedInOAuthSmokeResult:
        return LinkedInOAuthSmokeResult(
            ok=True,
            message="LinkedIn OAuth smoke test succeeded",
            access_token="browser-token-123",
            userinfo={
                "sub": "user-123",
                "name": "Avery Example",
                "email": "avery@example.com",
            },
            status_code=200,
        )

    result = asyncio.run(
        LinkedInLoginService(
            settings=settings,
            client=client,
            browser_login_runner=browser_runner,
            token_store=FakeTokenStore(),
        ).run()
    )

    assert result["ok"] is True
    assert result["account_summary"] == {
        "sub": "user-123",
        "name": "Avery Example",
    }


def test_login_service_reuses_stored_credential_before_browser_login() -> None:
    settings = LinkedInApiSettings(access_token=None, oauth=_oauth_settings())
    transport = FakeTransport({"sub": "user-456", "name": "Jordan Example"})
    client = LinkedInApiClient(settings, transport=transport)
    token_store = FakeTokenStore(
        StoredLinkedInCredential(access_token="stored-token-123")
    )

    def browser_runner(_: LinkedInApiSettings) -> LinkedInOAuthSmokeResult:
        raise AssertionError("browser flow should not run when stored credential works")

    result = asyncio.run(
        LinkedInLoginService(
            settings=settings,
            client=client,
            browser_login_runner=browser_runner,
            token_store=token_store,
        ).run()
    )

    assert result["credential_source"] == "secure_token_store"
    assert transport.access_token == "stored-token-123"
    assert result["account_summary"] == {
        "sub": "user-456",
        "name": "Jordan Example",
    }


def test_login_service_includes_stored_member_urn_when_available(tmp_path) -> None:
    encryption_key = Fernet.generate_key().decode()
    profile_path = tmp_path / "profile.enc"
    LocalEncryptedProfileStore(str(profile_path), encryption_key).save(
        MemberProfile(
            member_urn="urn:li:member:user-456",
            sub="user-456",
        )
    )
    settings = LinkedInApiSettings(
        access_token="token-123",
        profile_storage=LinkedInProfileStorageSettings(
            path=str(profile_path),
            encryption_key=encryption_key,
        ),
    )
    client = LinkedInApiClient(
        settings,
        transport=FakeTransport({"sub": "user-456", "name": "Jordan Example"}),
    )

    result = asyncio.run(LinkedInLoginService(settings=settings, client=client).run())

    assert result["member_urn"] == "urn:li:member:user-456"
