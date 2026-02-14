#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/robotville/BMAD}"
RBTV_REPO="${RBTV_REPO:-${WORKSPACE_ROOT}/_bmad/rbtv}"
SYNC_SCRIPT="${RBTV_REPO}/_mobile/ops/scripts/vps-sync-install.sh"

log() {
  printf '[vps-pull-rbtv] %s\n' "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[vps-pull-rbtv] ERROR: missing command: %s\n' "$1" >&2
    exit 1
  fi
}

main() {
  require_cmd git

  if [ ! -d "${RBTV_REPO}/.git" ]; then
    printf '[vps-pull-rbtv] ERROR: git repo not found at %s\n' "${RBTV_REPO}" >&2
    exit 1
  fi

  log "Repository: ${RBTV_REPO}"
  log "Restoring full checkout before pull"
  git -C "${RBTV_REPO}" sparse-checkout disable || true

  log "Fetching and pulling latest origin/master"
  git -C "${RBTV_REPO}" fetch origin --prune
  RBTV_SKIP_POST_MERGE_SYNC=1 git -C "${RBTV_REPO}" pull --ff-only origin master

  log "Running post-pull BMAD/RBTV reinstall automation"
  bash "${SYNC_SCRIPT}"
}

main "$@"
