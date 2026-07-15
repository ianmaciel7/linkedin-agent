# Asset Structure Rules

Keep durable rules for checked-in agent assets in `.agents/rules/`.

Keep reusable checked-in skills in `.agents/skills/`.

Apply the same single-responsibility rule to agent asset files under `.agents/`
and `.agents/skills/`.

Do not mix shared project policy, generated agent artifacts, reusable skill
instructions, lock data, and helper-script behavior in the same file.

Prefer this split:

* policy in `.agents/rules/`
* instructions in `SKILL.md`
* reusable patterns in `references/`
* automation helpers in `scripts/` or shell helpers
* versioned skill source metadata in lock files
