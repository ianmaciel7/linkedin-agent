"""ADK tool: read normalized LinkedIn posts for the authenticated member."""

from __future__ import annotations

import logging

from app.linkedin.client import LinkedInApiClient, LinkedInApiTestResult
from app.linkedin.models import PostMetadata
from app.linkedin.post_store import (
    LinkedInPostStoreConfigurationError,
    LinkedInPostStoreInvalidRecordError,
    LocalEncryptedPostStore,
)
from app.linkedin.posts import LinkedInPostsClient, LinkedInPostsClientError
from app.linkedin.tool_context_auth import LinkedInToolContext
from app.settings import LinkedInApiSettings, SettingsError

from .resolve_member_urn import _resolve_access_token, run_resolve_member_urn

logger = logging.getLogger(__name__)


def _mark_unavailable(post: PostMetadata) -> PostMetadata:
    return PostMetadata(
        post_urn=post.post_urn,
        created_at=post.created_at,
        text_excerpt=post.text_excerpt,
        visibility=post.visibility,
        permalink=post.permalink,
        like_count=post.like_count,
        comment_count=post.comment_count,
        unavailable=True,
    )


async def run_read_member_posts(
    use_cache: bool = False,
    clear: bool = False,
    tool_context: LinkedInToolContext | None = None,
    settings: LinkedInApiSettings | None = None,
    client: LinkedInApiClient | None = None,
    posts_client: LinkedInPostsClient | None = None,
) -> dict[str, object]:
    """Return the authenticated member's normalized LinkedIn post metadata."""

    try:
        resolved_settings = settings or LinkedInApiSettings.from_env()
    except SettingsError as exc:
        return LinkedInApiTestResult(
            ok=False,
            message=str(exc),
            error_code="missing_configuration",
        ).to_dict()

    post_store = None
    if resolved_settings.post_storage is not None:
        try:
            post_store = LocalEncryptedPostStore(
                resolved_settings.post_storage.path,
                resolved_settings.post_storage.encryption_key,
            )
        except LinkedInPostStoreConfigurationError as exc:
            return LinkedInApiTestResult(
                ok=False,
                message=str(exc),
                error_code="missing_configuration",
            ).to_dict()

    if clear:
        if post_store is not None:
            post_store.clear()
        return {"ok": True, "message": "LinkedIn post store cleared"}

    if use_cache and post_store is not None:
        try:
            cached_posts = post_store.load()
        except LinkedInPostStoreInvalidRecordError as exc:
            return LinkedInApiTestResult(
                ok=False,
                message=str(exc),
                error_code="upstream_failure",
            ).to_dict()
        return {
            "ok": True,
            "message": "LinkedIn post metadata loaded from the local store",
            "posts": [post.to_dict() for post in cached_posts],
            "source": "post_store",
            "stored": True,
            "pagination_note": LinkedInPostsClient.pagination_note(),
        }

    access_token, credential_source, error_result = await _resolve_access_token(
        tool_context=tool_context,
        settings=resolved_settings,
    )
    if error_result is not None:
        return error_result
    if access_token is None:
        return LinkedInApiTestResult(
            ok=False,
            message=(
                "LinkedIn access token is not available. "
                "Run the OAuth tool first to authenticate."
            ),
            error_code="missing_configuration",
        ).to_dict()

    urn_result = await run_resolve_member_urn(
        tool_context=tool_context,
        settings=resolved_settings,
        client=client,
    )
    member_urn = urn_result.get("member_urn")
    if urn_result.get("ok") is not True or not isinstance(member_urn, str):
        return {
            "ok": False,
            "message": "A resolved member URN is required. Run resolve_member_urn first.",
            "error_code": "missing_configuration",
        }

    resolved_posts_client = posts_client or LinkedInPostsClient(
        timeout_seconds=resolved_settings.timeout_seconds
    )
    try:
        posts = resolved_posts_client.fetch_posts(
            member_urn=member_urn,
            access_token=access_token,
        )
    except LinkedInPostsClientError as exc:
        result: dict[str, object] = {
            "ok": False,
            "message": str(exc),
            "error_code": exc.error_code,
        }
        if exc.error_code == "permission_denied":
            result["scope_required"] = "r_member_social"
        return result

    stored = False
    if post_store is not None:
        try:
            previous_posts = {post.post_urn: post for post in post_store.load()}
        except LinkedInPostStoreInvalidRecordError:
            previous_posts = {}
        current_post_urns = {post.post_urn for post in posts}
        merged_posts = list(posts)
        for post_urn, previous_post in previous_posts.items():
            if post_urn not in current_post_urns:
                merged_posts.append(_mark_unavailable(previous_post))
        try:
            post_store.save(merged_posts)
            stored = True
            posts = merged_posts
        except (LinkedInPostStoreConfigurationError, OSError) as exc:
            logger.debug("LinkedIn post store write failed: %s", type(exc).__name__)

    return {
        "ok": True,
        "message": (
            "LinkedIn posts retrieved successfully"
            if posts
            else "No published LinkedIn posts were found"
        ),
        "credential_source": credential_source,
        "posts": [post.to_dict() for post in posts],
        "stored": stored,
        "pagination_note": LinkedInPostsClient.pagination_note(),
    }
