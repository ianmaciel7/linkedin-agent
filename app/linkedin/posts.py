"""LinkedIn Posts API client for reading the authenticated member's published posts."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from requests import RequestException
from requests.exceptions import Timeout as RequestsTimeout

from app.linkedin.models import PostMetadata
from app.linkedin.restli import build_restli_client, configure_default_timeout
from app.linkedin.typing import RestliFinderClientProtocol

logger = logging.getLogger(__name__)

# LinkedIn versioned API date header (YYYYMM format).
_LINKEDIN_API_VERSION = "202412"

# Maximum posts to fetch in a single page (v0.2.0 is first-page-only).
_DEFAULT_COUNT = 20

_PAGINATION_NOTE = "First page only; pagination not yet supported"


class LinkedInPostsClientError(RuntimeError):
    """Base error raised by the LinkedIn posts client."""

    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class LinkedInPostsTransport(Protocol):
    """Protocol for the transport backing the posts client."""

    def get_posts(
        self,
        member_urn: str,
        access_token: str,
        count: int,
    ) -> dict[str, Any]:
        """Fetch the first page of published posts for the given member URN."""


class RestliPostsTransport:
    """Transport that calls the LinkedIn versioned /rest/posts endpoint.

    Uses the ``RestliClient`` from ``linkedin-api-client`` with the required
    ``LinkedIn-Version`` header to access the versioned API surface.
    """

    def __init__(
        self,
        client: RestliFinderClientProtocol | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._client = client or build_restli_client()
        configure_default_timeout(self._client, timeout_seconds)

    def get_posts(
        self,
        member_urn: str,
        access_token: str,
        count: int,
    ) -> dict[str, Any]:
        """Call /rest/posts with author filter and versioned headers."""
        try:
            # The linkedin-api-client RestliClient supports extra headers via
            # the ``additional_headers`` parameter on versioned finder calls.
            response = self._client.finder(
                resource_path="/posts",
                finder_name="author",
                query_params={
                    "author": member_urn,
                    "count": count,
                    "q": "author",
                },
                access_token=access_token,
                version_string=_LINKEDIN_API_VERSION,
            )
        except RequestsTimeout as exc:
            raise LinkedInPostsClientError(
                "LinkedIn Posts API request timed out", error_code="timeout"
            ) from exc
        except RequestException as exc:
            raise LinkedInPostsClientError(
                "LinkedIn Posts API request failed", error_code="upstream_failure"
            ) from exc

        raw: dict[str, Any] = {}
        if hasattr(response, "elements"):
            raw["elements"] = response.elements
        elif hasattr(response, "entity") and isinstance(response.entity, dict):
            raw = response.entity  # type: ignore[assignment]
        elif isinstance(response, dict):
            raw = response

        status = getattr(response, "status_code", 200)
        raw["_status_code"] = status
        return raw


class LinkedInPostsClient:
    """Read-only client for the authenticated member's published posts.

    Fetches at most ``count`` posts from the LinkedIn Posts API and normalises
    each one into a ``PostMetadata`` object.  Raw API payloads are never
    returned.
    """

    def __init__(
        self,
        transport: LinkedInPostsTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._transport = transport or RestliPostsTransport(
            timeout_seconds=timeout_seconds
        )

    def fetch_posts(
        self,
        member_urn: str,
        access_token: str,
        count: int = _DEFAULT_COUNT,
    ) -> list[PostMetadata]:
        """Return normalised post metadata for the member's most recent posts.

        Args:
            member_urn: The authenticated member's URN (``urn:li:member:<sub>``).
            access_token: A valid LinkedIn access token with ``r_member_social``.
            count: Maximum number of posts to return (capped at 20 for v0.2.0).

        Returns:
            A list of ``PostMetadata`` objects, possibly empty.

        Raises:
            LinkedInPostsClientError: On HTTP 403, 429, timeout, or network failure.
        """
        if not member_urn.strip():
            raise LinkedInPostsClientError(
                "A resolved member URN is required before reading posts",
                error_code="missing_configuration",
            )

        try:
            raw = self._transport.get_posts(
                member_urn=member_urn,
                access_token=access_token,
                count=min(count, _DEFAULT_COUNT),
            )
        except LinkedInPostsClientError:
            raise

        status_code = raw.get("_status_code", 200)
        if isinstance(status_code, int):
            if status_code in {401, 403}:
                raise LinkedInPostsClientError(
                    "LinkedIn Posts API rejected the request: insufficient permissions. "
                    "The r_member_social scope may not be approved for this application.",
                    error_code="permission_denied",
                )
            if status_code == 429:
                raise LinkedInPostsClientError(
                    "LinkedIn Posts API rate limit reached",
                    error_code="rate_limited",
                )
            if status_code not in range(200, 300):
                raise LinkedInPostsClientError(
                    f"LinkedIn Posts API returned unexpected status {status_code}",
                    error_code="upstream_failure",
                )

        elements = raw.get("elements", [])
        if not isinstance(elements, list):
            return []

        posts: list[PostMetadata] = []
        for item in elements:
            if not isinstance(item, dict):
                continue
            post = self._normalise(item)
            if post is not None:
                posts.append(post)
        return posts

    @staticmethod
    def pagination_note() -> str:
        """Return the stable v0.2.0 pagination note."""
        return _PAGINATION_NOTE

    @staticmethod
    def _normalise(item: dict[str, Any]) -> PostMetadata | None:
        """Convert a raw LinkedIn Posts API element into PostMetadata."""
        urn = item.get("id") or item.get("$URN")
        if not urn or not isinstance(urn, str):
            return None

        # Created-at timestamp: prefer epochMilliseconds inside lifecycleState.
        lifecycle = item.get("lifecycleState", {})
        created_at: int = 0
        if isinstance(lifecycle, dict):
            created_at_raw = lifecycle.get("epochMilliseconds", 0)
            if isinstance(created_at_raw, (int, float)):
                created_at = int(created_at_raw)

        # Text excerpt — first 300 chars from the first text annotation.
        commentary = item.get("commentary", "")
        if isinstance(commentary, str):
            text_excerpt = commentary[:300]
        else:
            text_excerpt = ""

        visibility_raw = item.get("visibility", "PUBLIC")
        visibility = str(visibility_raw) if visibility_raw else "PUBLIC"

        # Social counts
        social_detail = item.get("socialDetail", {})
        like_count = 0
        comment_count = 0
        if isinstance(social_detail, dict):
            like_raw = social_detail.get("totalSocialActivityCounts", {})
            if isinstance(like_raw, dict):
                lc = like_raw.get("numLikes", 0)
                cc = like_raw.get("numComments", 0)
                like_count = int(lc) if isinstance(lc, (int, float)) else 0
                comment_count = int(cc) if isinstance(cc, (int, float)) else 0

        # Permalink: not always in the response; skip gracefully.
        permalink_raw = item.get("permalink")
        permalink = permalink_raw if isinstance(permalink_raw, str) else None

        return PostMetadata(
            post_urn=urn,
            created_at=created_at,
            text_excerpt=text_excerpt,
            visibility=visibility,
            permalink=permalink,
            like_count=like_count,
            comment_count=comment_count,
        )
