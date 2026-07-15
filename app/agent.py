"""ADK app wiring for the LinkedIn agent."""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.apps import App

from app.tools import run_linkedin_login_service

DEFAULT_MODEL = os.getenv("LINKEDIN_AGENT_MODEL", "gemini-3.5-flash")

root_agent = Agent(
    name="linkedin_agent",
    model=DEFAULT_MODEL,
    description="A LinkedIn workflow assistant for drafting, planning, and review support.",
    instruction=(
        "You help with LinkedIn workflow planning and review. "
        "Use the `run_linkedin_login_service` tool only when the user wants to "
        "sign in to LinkedIn or verify their OAuth configuration. "
        "If the tool reports `pending_auth` and provides an `authorization_url`, "
        "respond with a short, user-friendly message that includes the URL as a "
        "Markdown link and explains that the user should approve LinkedIn access "
        "before trying again. "
        "This tool is read-only and must not be treated as permission to publish, "
        "message, invite, or modify LinkedIn data."
    ),
    tools=[run_linkedin_login_service],
)

app = App(name="app", root_agent=root_agent)
