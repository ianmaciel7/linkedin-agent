from __future__ import annotations

import pytest

from app.linkedin.posts import (
    LinkedInPostsClient,
    LinkedInPostsClientError,
    RestliPostsTransport,
)


class FakePostsTransport:
    def __init__(self, payload=None) -> None:
        self.payload = payload if payload is not None else {"elements": []}
        self.calls: list[tuple[str, str, int]] = []

    def get_posts(
        self,
        member_urn: str,
        access_token: str,
        count: int,
    ) -> dict[str, object]:
        self.calls.append((member_urn, access_token, count))
        return dict(self.payload)


class FakeRestliPostsResponse:
    status_code = 200
    elements = [
        {
            "id": "urn:li:share:1",
            "commentary": "hello world",
        }
    ]


class FakeRestliPostsClient:
    def __init__(self) -> None:
        self.session = type(
            "Session", (), {"send": lambda self, *args, **kwargs: None}
        )()
        self.finder_call: dict[str, object] | None = None

    def finder(
        self,
        *,
        resource_path: str,
        finder_name: str,
        query_params: dict[str, object],
        access_token: str,
        version_string: str,
    ) -> object:
        self.finder_call = {
            "resource_path": resource_path,
            "finder_name": finder_name,
            "query_params": query_params,
            "access_token": access_token,
            "version_string": version_string,
        }
        return FakeRestliPostsResponse()


def test_posts_client_returns_normalized_posts() -> None:
    client = LinkedInPostsClient(
        transport=FakePostsTransport(
            {
                "_status_code": 200,
                "elements": [
                    {
                        "id": "urn:li:share:1",
                        "commentary": "hello world",
                        "visibility": "PUBLIC",
                        "socialDetail": {
                            "totalSocialActivityCounts": {
                                "numLikes": 3,
                                "numComments": 1,
                            }
                        },
                    }
                ],
            }
        )
    )

    posts = client.fetch_posts("urn:li:member:123", "token")

    assert len(posts) == 1
    assert posts[0].post_urn == "urn:li:share:1"
    assert posts[0].text_excerpt == "hello world"


def test_restli_posts_transport_uses_official_finder_shape() -> None:
    fake_client = FakeRestliPostsClient()
    transport = RestliPostsTransport(client=fake_client, timeout_seconds=5.0)

    result = transport.get_posts("urn:li:member:123", "token", 20)

    assert result["_status_code"] == 200
    assert result["elements"] == FakeRestliPostsResponse.elements
    assert fake_client.finder_call == {
        "resource_path": "/posts",
        "finder_name": "author",
        "query_params": {
            "author": "urn:li:member:123",
            "count": 20,
            "q": "author",
        },
        "access_token": "token",
        "version_string": "202412",
    }


def test_posts_client_returns_empty_list() -> None:
    client = LinkedInPostsClient(
        transport=FakePostsTransport({"_status_code": 200, "elements": []})
    )

    assert client.fetch_posts("urn:li:member:123", "token") == []


@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [(403, "permission_denied"), (429, "rate_limited"), (500, "upstream_failure")],
)
def test_posts_client_normalizes_http_failures(
    status_code: int,
    error_code: str,
) -> None:
    client = LinkedInPostsClient(
        transport=FakePostsTransport({"_status_code": status_code, "elements": []})
    )

    with pytest.raises(LinkedInPostsClientError) as exc_info:
        client.fetch_posts("urn:li:member:123", "token")

    assert exc_info.value.error_code == error_code


def test_posts_client_raises_for_missing_member_urn() -> None:
    client = LinkedInPostsClient(transport=FakePostsTransport())

    with pytest.raises(LinkedInPostsClientError, match="member URN"):
        client.fetch_posts("", "token")
