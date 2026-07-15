# Skill Authoring Rules

Files under `.agents/skills/` may be repository-specific and can mention the
local project, agent package, or repo conventions.

Any new repo-local skill that should exist across environments must have an
equivalent checked-in version under `.agents/skills/`.

Keep each `.agents/skills/*/SKILL.md` focused on one primary capability or
workflow.

Do not mix multiple unrelated workflows into one skill just because they share
the same ecosystem or toolchain.

When a skill grows beyond one main job, split it into multiple skills or move
reusable material into `references/` or helper scripts.

Keep scripts and automation helpers separate from instructional Markdown.
