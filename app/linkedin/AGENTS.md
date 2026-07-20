# AGENTS.md

## Package rules

- Keep reusable typing aliases and protocol contracts for `app/linkedin` in [`typing.py`](./typing.py).
- When a LinkedIn module needs shared type literals, JSON aliases, or transport protocols, define or extend them in `typing.py` instead of re-declaring them in runtime modules.
- When the official LinkedIn Python client dependency must be added, refreshed, or changed for this package, use `uv add linkedin-api-client` so `pyproject.toml` and `uv.lock` stay in sync.
- Keep direct `linkedin-api-client` construction and session customization in [`restli.py`](./restli.py) or a small typed transport adapter. Do not scatter raw `RestliClient` setup across domain, storage, tool, or orchestration modules.
