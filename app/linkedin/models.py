"""Domain models for LinkedIn member identity and post metadata."""

from __future__ import annotations

from dataclasses import dataclass, field


def _coerce_int(value: object, default: int = 0) -> int:
    """Return an integer for stored numeric values, or the default."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


@dataclass(frozen=True, slots=True)
class MemberProfile:
    """Structured LinkedIn member profile record.

    Fields sourced from the OIDC /userinfo response are stored under their
    standard claim names.  User-supplied fields (headline, industry, location,
    summary) are kept in a separate mapping so callers can distinguish their
    origin.
    """

    member_urn: str
    """Authenticated member URN in the form ``urn:li:member:<sub>``."""

    sub: str
    """OIDC subject claim — the raw identifier used to build the URN."""

    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None

    # User-supplied enrichments that are not available from the OIDC response.
    user_supplied: dict[str, str] = field(default_factory=dict)

    def to_dict(self, *, include_email: bool = False) -> dict[str, object]:
        """Return a plain dictionary suitable for tool responses."""
        result: dict[str, object] = {
            "member_urn": self.member_urn,
        }
        for key in ("name", "given_name", "family_name"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        if include_email and self.email is not None:
            result["email"] = self.email
        if self.user_supplied:
            result["user_supplied"] = dict(self.user_supplied)
        return result

    def to_store_dict(self) -> dict[str, object]:
        """Return a full dictionary for encrypted-at-rest storage."""
        result: dict[str, object] = {
            "member_urn": self.member_urn,
            "sub": self.sub,
        }
        for key in ("name", "given_name", "family_name", "email"):
            value = getattr(self, key)
            if value is not None:
                result[key] = value
        result["user_supplied"] = dict(self.user_supplied)
        return result

    @classmethod
    def from_store_dict(cls, data: dict[str, object]) -> MemberProfile:
        """Reconstruct a MemberProfile from an encrypted store payload."""
        user_supplied_raw = data.get("user_supplied", {})
        user_supplied: dict[str, str] = (
            {str(k): str(v) for k, v in user_supplied_raw.items()}
            if isinstance(user_supplied_raw, dict)
            else {}
        )
        return cls(
            member_urn=str(data["member_urn"]),
            sub=str(data["sub"]),
            name=str(data["name"]) if data.get("name") else None,
            given_name=str(data["given_name"]) if data.get("given_name") else None,
            family_name=str(data["family_name"]) if data.get("family_name") else None,
            email=str(data["email"]) if data.get("email") else None,
            user_supplied=user_supplied,
        )


@dataclass(frozen=True, slots=True)
class PostMetadata:
    """Normalised LinkedIn post metadata record.

    Contains only the fields required for analytics and content planning.
    Raw API payloads are never stored or surfaced through tools.
    """

    post_urn: str
    """LinkedIn post URN (e.g. ``urn:li:share:<id>``)."""

    created_at: int
    """Unix epoch milliseconds when the post was created."""

    text_excerpt: str
    """First 300 characters of post text."""

    visibility: str
    """Post visibility string (e.g. ``PUBLIC``, ``CONNECTIONS``)."""

    permalink: str | None = None
    like_count: int = 0
    comment_count: int = 0
    unavailable: bool = False
    """Marked True when the post can no longer be retrieved from the API."""

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary for tool responses."""
        return {
            "post_urn": self.post_urn,
            "created_at": self.created_at,
            "text_excerpt": self.text_excerpt,
            "visibility": self.visibility,
            "permalink": self.permalink,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "unavailable": self.unavailable,
        }

    def to_store_dict(self) -> dict[str, object]:
        """Return a dictionary for encrypted-at-rest storage."""
        return self.to_dict()

    @classmethod
    def from_store_dict(cls, data: dict[str, object]) -> PostMetadata:
        """Reconstruct a PostMetadata from a stored dictionary."""
        return cls(
            post_urn=str(data["post_urn"]),
            created_at=_coerce_int(data.get("created_at", 0)),
            text_excerpt=str(data.get("text_excerpt", "")),
            visibility=str(data.get("visibility", "PUBLIC")),
            permalink=str(data["permalink"]) if data.get("permalink") else None,
            like_count=_coerce_int(data.get("like_count", 0)),
            comment_count=_coerce_int(data.get("comment_count", 0)),
            unavailable=bool(data.get("unavailable", False)),
        )


@dataclass(frozen=True, slots=True)
class PostStoreRecord:
    """Version-stable record used by the encrypted post store."""

    posts: tuple[PostMetadata, ...] = ()

    def to_store_dict(self) -> dict[str, object]:
        """Return the persisted payload for the post store."""
        return {
            "posts": [post.to_store_dict() for post in self.posts],
        }

    @classmethod
    def from_store_dict(cls, data: dict[str, object]) -> PostStoreRecord:
        """Reconstruct a post-store record from persisted data."""
        posts_raw = data.get("posts", [])
        if not isinstance(posts_raw, list):
            raise TypeError("posts must be a list")
        return cls(
            posts=tuple(
                PostMetadata.from_store_dict(item)
                for item in posts_raw
                if isinstance(item, dict)
            )
        )
