from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from google.adk.auth.auth_credential import OAuth2Auth

from app.linkedin.token_store import (
    LinkedInTokenStoreConfigurationError,
    LinkedInTokenStoreExpiredCredentialError,
    LinkedInTokenStoreInvalidRecordError,
    LocalEncryptedLinkedInTokenStore,
)
from app.settings import LinkedInOAuthSettings, LinkedInTokenStorageSettings


def make_oauth_settings() -> LinkedInOAuthSettings:
    return LinkedInOAuthSettings(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8000/callback",
        credential_key="linkedin_oauth",
    )


def test_local_encrypted_token_store_round_trips_credential(tmp_path) -> None:
    store = LocalEncryptedLinkedInTokenStore(
        LinkedInTokenStorageSettings(
            path=str(tmp_path / "linkedin-token.enc"),
            encryption_key=Fernet.generate_key().decode("utf-8"),
        ),
        clock=lambda: 100.0,
    )

    store.save(
        make_oauth_settings(),
        OAuth2Auth(
            access_token="token-123",
            refresh_token="refresh-123",
            expires_at=12345.0,
            expires_in=3600,
        ),
        subject="user-123",
    )

    loaded = store.load(make_oauth_settings())

    assert loaded is not None
    assert loaded.access_token == "token-123"
    assert loaded.refresh_token == "refresh-123"
    assert loaded.expires_at == 12345.0
    assert loaded.expires_in == 3600
    assert b"token-123" not in (tmp_path / "linkedin-token.enc").read_bytes()


def test_local_encrypted_token_store_rejects_invalid_key(tmp_path) -> None:
    with pytest.raises(
        LinkedInTokenStoreConfigurationError,
        match="LINKEDIN_TOKEN_ENCRYPTION_KEY",
    ):
        LocalEncryptedLinkedInTokenStore(
            LinkedInTokenStorageSettings(
                path=str(tmp_path / "linkedin-token.enc"),
                encryption_key="not-a-valid-fernet-key",
            )
        )


def test_local_encrypted_token_store_raises_on_corrupt_record(tmp_path) -> None:
    path = tmp_path / "linkedin-token.enc"
    path.write_text("not-encrypted", encoding="utf-8")
    store = LocalEncryptedLinkedInTokenStore(
        LinkedInTokenStorageSettings(
            path=str(path),
            encryption_key=Fernet.generate_key().decode("utf-8"),
        )
    )

    with pytest.raises(LinkedInTokenStoreInvalidRecordError, match="decrypted"):
        store.load(make_oauth_settings())


def test_local_encrypted_token_store_raises_on_expired_credential(tmp_path) -> None:
    store = LocalEncryptedLinkedInTokenStore(
        LinkedInTokenStorageSettings(
            path=str(tmp_path / "linkedin-token.enc"),
            encryption_key=Fernet.generate_key().decode("utf-8"),
        ),
        clock=lambda: 200.0,
    )
    store.save(
        make_oauth_settings(),
        OAuth2Auth(access_token="token-123", expires_at=100.0),
    )

    with pytest.raises(LinkedInTokenStoreExpiredCredentialError, match="expired"):
        store.load(make_oauth_settings())


def test_local_encrypted_token_store_ignores_other_oauth_context(tmp_path) -> None:
    store = LocalEncryptedLinkedInTokenStore(
        LinkedInTokenStorageSettings(
            path=str(tmp_path / "linkedin-token.enc"),
            encryption_key=Fernet.generate_key().decode("utf-8"),
        )
    )
    store.save(make_oauth_settings(), OAuth2Auth(access_token="token-123"))

    other_settings = LinkedInOAuthSettings(
        client_id="other-client-id",
        client_secret="client-secret",
        redirect_uri="http://localhost:8000/callback",
        credential_key="linkedin_oauth",
    )

    assert store.load(other_settings) is None


def test_local_encrypted_token_store_clears_record(tmp_path) -> None:
    path = tmp_path / "linkedin-token.enc"
    store = LocalEncryptedLinkedInTokenStore(
        LinkedInTokenStorageSettings(
            path=str(path),
            encryption_key=Fernet.generate_key().decode("utf-8"),
        )
    )
    store.save(make_oauth_settings(), OAuth2Auth(access_token="token-123"))

    assert store.clear(make_oauth_settings()) is True
    assert not path.exists()
