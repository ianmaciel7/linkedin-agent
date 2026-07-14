#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="${SCRIPT_DIR}/skills.lock.json"

usage() {
  cat <<'EOF'
Usage:
  ./.agents/skills/skill.sh list
  ./.agents/skills/skill.sh sync

Commands:
  list  Show locked skills and their pinned source metadata.
  sync  Materialize every locked skill into .agents/skills/<name>.

Notes:
  - The lock file is the versioned source of truth for repo-local skills.
  - Each skill is fetched from a Git repository at a pinned ref.
  - The script requires: bash, git, and python3.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

ensure_lock_file() {
  if [[ ! -f "${LOCK_FILE}" ]]; then
    echo "Lock file not found: ${LOCK_FILE}" >&2
    exit 1
  fi
}

list_skills() {
  ensure_lock_file
  python3 - "${LOCK_FILE}" <<'PY'
import json
import sys

lock_file = sys.argv[1]
data = json.load(open(lock_file, "r", encoding="utf-8"))
skills = data.get("skills", [])

if not skills:
    print("No repo-local skills are locked yet.")
    raise SystemExit(0)

for skill in skills:
    name = skill["name"]
    repo = skill["repo"]
    path = skill["path"]
    ref = skill["ref"]
    print(f"{name}\n  repo: {repo}\n  path: {path}\n  ref:  {ref}")
PY
}

sync_skills() {
  ensure_lock_file
  require_cmd git
  require_cmd python3

  python3 - "${LOCK_FILE}" "${SCRIPT_DIR}" <<'PY'
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

lock_file = Path(sys.argv[1])
skills_dir = Path(sys.argv[2])
data = json.load(lock_file.open("r", encoding="utf-8"))
skills = data.get("skills", [])

if not skills:
    print("No repo-local skills are locked yet.")
    raise SystemExit(0)

for skill in skills:
    name = skill["name"]
    repo = skill["repo"]
    ref = skill["ref"]
    path = skill["path"]
    dest = skills_dir / name
    version_file = dest / ".skill-version.json"

    with tempfile.TemporaryDirectory(prefix=f"skill-{name}-") as tmp:
        tmp_path = Path(tmp)
        checkout = tmp_path / "checkout"

        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                ref,
                "--filter=blob:none",
                "--sparse",
                repo,
                str(checkout),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "sparse-checkout", "set", "--no-cone", path],
            check=True,
        )

        source = checkout / path
        if not source.exists():
            raise SystemExit(f"Locked path not found for {name}: {path}")

        if dest.exists():
            shutil.rmtree(dest)

        shutil.copytree(source, dest)

        commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        version_payload = {
            "name": name,
            "repo": repo,
            "path": path,
            "ref": ref,
            "commit": commit,
        }
        version_file.write_text(
            json.dumps(version_payload, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Synced {name} @ {commit[:12]}")
PY
}

main() {
  local command="${1:-}"

  case "${command}" in
    list)
      list_skills
      ;;
    sync)
      sync_skills
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: ${command}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
