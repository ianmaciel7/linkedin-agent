from app import app
from app.agent import root_agent
from app.tools import run_linkedin_login_service


def test_app_exports_adk_app() -> None:
    assert app is not None


def test_root_agent_registers_linkedin_api_test_tool() -> None:
    assert root_agent.tools == [run_linkedin_login_service]
    assert "authorization_url" in root_agent.instruction
