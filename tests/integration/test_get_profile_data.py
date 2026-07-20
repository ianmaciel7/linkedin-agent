from __future__ import annotations

import asyncio

from cryptography.fernet import Fernet

from app.linkedin.client import LinkedInApiTestResult
from app.settings import LinkedInApiSettings, LinkedInProfileStorageSettings
from app.tools.get_profile_data import run_get_profile_data


class FakeClient:
    def test_connection(self, access_token: str | None = None) -> LinkedInApiTestResult:
        return LinkedInApiTestResult(
            ok=True,
            message="ok",
            status_code=200,
            account_summary={
                "sub": "user-123",
                "name": "Avery Example",
                "given_name": "Avery",
                "family_name": "Example",
                "email": "avery@example.com",
            },
        )


def test_get_profile_data_returns_profile_and_persists(tmp_path) -> None:
    settings = LinkedInApiSettings(
        access_token="token-123",
        profile_storage=LinkedInProfileStorageSettings(
            path=str(tmp_path / "profile.enc"),
            encryption_key=Fernet.generate_key().decode(),
        ),
    )

    result = asyncio.run(
        run_get_profile_data(
            user_supplied={"headline": "Builder"},
            settings=settings,
            client=FakeClient(),
        )
    )

    assert result["ok"] is True
    assert result["stored"] is True
    assert result["profile"]["user_supplied"] == {"headline": "Builder"}
