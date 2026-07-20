from __future__ import annotations

import asyncio

from cryptography.fernet import Fernet

from app.linkedin.client import LinkedInApiTestResult
from app.linkedin.models import PostMetadata
from app.settings import (
    LinkedInApiSettings,
    LinkedInPostStorageSettings,
    LinkedInProfileStorageSettings,
)
from app.tools.read_member_posts import run_read_member_posts


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


class FakePostsClient:
    def fetch_posts(self, member_urn: str, access_token: str, count: int = 20):
        return [
            PostMetadata(
                post_urn="urn:li:share:1",
                created_at=1,
                text_excerpt="hello",
                visibility="PUBLIC",
            )
        ]


def test_read_member_posts_returns_posts_and_persists(tmp_path) -> None:
    settings = LinkedInApiSettings(
        access_token="token-123",
        profile_storage=LinkedInProfileStorageSettings(
            path=str(tmp_path / "profile.enc"),
            encryption_key=Fernet.generate_key().decode(),
        ),
        post_storage=LinkedInPostStorageSettings(
            path=str(tmp_path / "posts.enc"),
            encryption_key=Fernet.generate_key().decode(),
        ),
    )

    result = asyncio.run(
        run_read_member_posts(
            settings=settings,
            client=FakeClient(),
            posts_client=FakePostsClient(),
        )
    )

    assert result["ok"] is True
    assert result["stored"] is True
    assert len(result["posts"]) == 1
