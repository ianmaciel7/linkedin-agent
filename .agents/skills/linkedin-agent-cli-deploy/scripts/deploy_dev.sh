#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID=""
REGION=""
SERVICE_ACCOUNT=""
SERVICE_NAME="linkedin-agent"
EXECUTE="false"
ENV_FILE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./.agents/skills/linkedin-agent-cli-deploy/scripts/deploy_dev.sh \
    --project-id my-dev-project \
    --region us-central1 \
    --service-account agent-runtime@my-dev-project.iam.gserviceaccount.com \
    [--service-name linkedin-agent] \
    [--env-file .env.local] \
    [--execute]

Notes:
  - Defaults to dry-run mode.
  - Loads `.env.local` first when present, otherwise `.env`, unless `--env-file` is passed.
  - CLI flags override values loaded from env files.
  - Pass --execute only after explicit human approval.
EOF
}

load_env_file() {
  local env_file="$1"

  if [[ ! -f "${env_file}" ]]; then
    echo "Env file not found: ${env_file}" >&2
    exit 1
  fi

  set -a
  # shellcheck disable=SC1090
  source <(sed 's/\r$//' "${env_file}")
  set +a
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id)
      PROJECT_ID="${2:-}"
      shift 2
      ;;
    --region)
      REGION="${2:-}"
      shift 2
      ;;
    --service-account)
      SERVICE_ACCOUNT="${2:-}"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="${2:-}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --execute)
      EXECUTE="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -n "${ENV_FILE}" ]]; then
  load_env_file "${ENV_FILE}"
elif [[ -f "${REPO_ROOT}/.env.local" ]]; then
  load_env_file "${REPO_ROOT}/.env.local"
elif [[ -f "${REPO_ROOT}/.env" ]]; then
  load_env_file "${REPO_ROOT}/.env"
fi

PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${REGION:-${GOOGLE_CLOUD_LOCATION:-}}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-${LINKEDIN_AGENT_SERVICE_ACCOUNT:-${GOOGLE_CLOUD_SERVICE_ACCOUNT:-}}}"
SERVICE_NAME="${SERVICE_NAME:-${LINKEDIN_AGENT_SERVICE_NAME:-linkedin-agent}}"

if [[ -z "${PROJECT_ID}" || -z "${REGION}" || -z "${SERVICE_ACCOUNT}" ]]; then
  echo "Missing required deploy configuration." >&2
  usage >&2
  exit 1
fi

if command -v agents-cli >/dev/null 2>&1; then
  runner=(agents-cli)
elif command -v uvx >/dev/null 2>&1; then
  runner=(uvx --from google-agents-cli agents-cli)
else
  echo "Neither agents-cli nor uvx is available on PATH." >&2
  exit 1
fi

command_args=(
  deploy
  --project "${PROJECT_ID}"
  --region "${REGION}"
  --service-account "${SERVICE_ACCOUNT}"
  --service-name "${SERVICE_NAME}"
  --deployment-target cloud_run
  --no-confirm-project
)

if [[ "${EXECUTE}" != "true" ]]; then
  command_args+=(--dry-run)
fi

echo "Prepared command:"
printf '%q ' "${runner[@]}" "${command_args[@]}"
printf '\n'

if [[ "${EXECUTE}" != "true" ]]; then
  echo
  echo "Dry run only. Re-run with --execute after explicit approval."
  exit 0
fi

"${runner[@]}" "${command_args[@]}"
