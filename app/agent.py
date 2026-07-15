"""ADK app wiring for the LinkedIn agent."""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.apps import App

from app.tools import run_linkedin_api_test

DEFAULT_MODEL = os.getenv("LINKEDIN_AGENT_MODEL", "gemini-2.0-flash")

root_agent = Agent(
    name="linkedin_agent",
    model=DEFAULT_MODEL,
    description="A LinkedIn workflow assistant for drafting, planning, and review support.",
    instruction=(
        "You help with LinkedIn workflow planning and review. "
        "Use the `run_linkedin_api_test` tool only when the user wants to verify "
        "their LinkedIn API token, OAuth configuration, or endpoint configuration. "
        "This tool is read-only and must not be treated as permission to publish, "
        "message, invite, or modify LinkedIn data."
    ),
    tools=[run_linkedin_api_test],
)

app = App(name="app", root_agent=root_agent)
