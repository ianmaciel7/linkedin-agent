from app import app


def test_app_exports_adk_app() -> None:
    assert app is not None
