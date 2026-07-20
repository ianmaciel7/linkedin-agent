"""LinkedIn member profile assembly helpers."""

from __future__ import annotations

from app.linkedin.member import resolve_member_urn
from app.linkedin.models import MemberProfile

_OIDC_FIELD_KEYS = ("name", "given_name", "family_name", "email")


def assemble_profile(
    userinfo: dict[str, object],
    user_supplied: dict[str, str] | None = None,
    stored: MemberProfile | None = None,
) -> MemberProfile:
    """Build a MemberProfile from OIDC userinfo and optional user-supplied fields.

    Merging rules:
    - The member URN and ``sub`` are always derived from ``userinfo``.
    - Standard OIDC fields (name, given_name, family_name, email) come from
      ``userinfo`` when present.
    - ``user_supplied`` overrides nothing in the OIDC set; it is a separate
      enrichment layer kept in the ``user_supplied`` mapping.
    - When ``stored`` is provided and ``user_supplied`` is None, the stored
      user-supplied fields are carried forward so they survive session restarts.

    Args:
        userinfo: Decoded OIDC /userinfo JSON payload.
        user_supplied: Optional caller-provided enrichments such as headline,
            industry, or location.
        stored: Previously persisted profile from which user_supplied fields
            are inherited when no new ones are provided.

    Returns:
        A fully assembled MemberProfile ready for storage and tool responses.
    """
    member_urn = resolve_member_urn(userinfo)
    sub = str(userinfo.get("sub", "")).strip()

    def _str_or_none(key: str) -> str | None:
        value = userinfo.get(key)
        return str(value).strip() or None if value is not None else None

    # Merge user_supplied: caller wins over stored.
    resolved_user_supplied: dict[str, str]
    if user_supplied is not None:
        resolved_user_supplied = {
            key: value for key, value in user_supplied.items() if value.strip()
        }
    elif stored is not None:
        resolved_user_supplied = dict(stored.user_supplied)
    else:
        resolved_user_supplied = {}

    return MemberProfile(
        member_urn=member_urn,
        sub=sub,
        name=_str_or_none("name"),
        given_name=_str_or_none("given_name"),
        family_name=_str_or_none("family_name"),
        email=_str_or_none("email"),
        user_supplied=resolved_user_supplied,
    )
