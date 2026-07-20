from __future__ import annotations

from app.linkedin.models import PostMetadata


def test_post_metadata_from_store_dict_coerces_string_counts() -> None:
    result = PostMetadata.from_store_dict(
        {
            "post_urn": "urn:li:share:123",
            "created_at": "1700000000000",
            "text_excerpt": "Example",
            "visibility": "PUBLIC",
            "like_count": "12",
            "comment_count": "3",
        }
    )

    assert result.created_at == 1700000000000
    assert result.like_count == 12
    assert result.comment_count == 3


def test_post_metadata_from_store_dict_defaults_invalid_counts() -> None:
    result = PostMetadata.from_store_dict(
        {
            "post_urn": "urn:li:share:123",
            "created_at": object(),
            "text_excerpt": "Example",
            "visibility": "PUBLIC",
            "like_count": object(),
            "comment_count": "not-a-number",
        }
    )

    assert result.created_at == 0
    assert result.like_count == 0
    assert result.comment_count == 0
