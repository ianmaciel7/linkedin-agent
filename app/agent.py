"""ADK app wiring for the LinkedIn agent."""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.apps import App

DEFAULT_MODEL = os.getenv("LINKEDIN_AGENT_MODEL", "gemini-2.0-flash")

root_agent = Agent(
    name="linkedin_agent",
    model=DEFAULT_MODEL,
    description="A LinkedIn workflow assistant for drafting, planning, and review support.",
)

app = App(root_agent=root_agent)

