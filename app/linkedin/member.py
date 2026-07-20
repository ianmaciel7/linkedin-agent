"""LinkedIn member URN resolution helpers."""

from __future__ import annotations


class MemberUrnError(ValueError):
    """Raised when a member URN cannot be derived from the provided data."""


def resolve_member_urn(userinfo: dict[str, object]) -> str:
    """Derive the LinkedIn member URN from an OIDC /userinfo response.

    The URN is constructed as ``urn:li:member:<sub>`` where ``sub`` is the
    subject claim from the OIDC response.  This is a documented LinkedIn
    pattern and requires no additional API call beyond the existing /userinfo
    request.

    Args:
        userinfo: The decoded JSON payload from the LinkedIn /userinfo endpoint.

    Returns:
        A string in the form ``urn:li:member:<sub>``.

    Raises:
        MemberUrnError: If ``sub`` is missing or empty in the response.
    """
    sub = userinfo.get("sub")
    if not sub or not isinstance(sub, str) or not sub.strip():
        raise MemberUrnError(
            "LinkedIn /userinfo response did not include a valid 'sub' claim; "
            "cannot derive member URN"
        )
    return f"urn:li:member:{sub.strip()}"
