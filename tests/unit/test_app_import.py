from app import app
from app.agent import root_agent
from app.tools import (
    run_get_profile_data,
    run_linkedin_login_service,
    run_read_member_posts,
    run_resolve_member_urn,
)


def test_app_exports_adk_app() -> None:
    assert app is not None


def test_root_agent_registers_linkedin_api_test_tool() -> None:
    assert root_agent.tools == [
        run_linkedin_login_service,
        run_resolve_member_urn,
        run_get_profile_data,
        run_read_member_posts,
    ]
    instruction = root_agent.instruction
    assert isinstance(instruction, str)
    assert "authorization_url" in instruction
