from __future__ import annotations

import asyncio

from cryptography.fernet import Fernet

from app.linkedin.client import LinkedInApiTestResult
from app.settings import LinkedInApiSettings, LinkedInProfileStorageSettings
from app.tools.resolve_member_urn import run_resolve_member_urn


class FakeClient:
    def test_connection(self, access_token: str | None = None) -> LinkedInApiTestResult:
        return LinkedInApiTestResult(
            ok=True,
            message="ok",
            status_code=200,
            account_summary={
                "sub": "user-123",
                "name": "Avery Example",
                "email": "avery@example.com",
            },
        )


def test_resolve_member_urn_persists_result(tmp_path) -> None:
    settings = LinkedInApiSettings(
        access_token="token-123",
        profile_storage=LinkedInProfileStorageSettings(
            path=str(tmp_path / "profile.enc"),
            encryption_key=Fernet.generate_key().decode(),
        ),
    )

    result = asyncio.run(run_resolve_member_urn(settings=settings, client=FakeClient()))

    assert result["ok"] is True
    assert result["member_urn"] == "urn:li:member:user-123"
    assert result["stored"] is True
