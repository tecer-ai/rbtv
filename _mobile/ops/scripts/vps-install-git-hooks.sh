#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/robotville/BMAD}"
RBTV_REPO="${RBTV_REPO:-${WORKSPACE_ROOT}/_bmad/rbtv}"
HOOKS_DIR="${RBTV_REPO}/.git/hooks"
SYNC_SCRIPT="${RBTV_REPO}/_mobile/ops/scripts/vps-sync-install.sh"

log() {
  printf '[vps-install-git-hooks] %s\n' "$1"
}

main() {
  if [ ! -d "${RBTV_REPO}/.git" ]; then
    printf '[vps-install-git-hooks] ERROR: git repo not found at %s\n' "${RBTV_REPO}" >&2
    exit 1
  fi

  mkdir -p "${HOOKS_DIR}"

  cat > "${HOOKS_DIR}/post-merge" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [ "\${RBTV_SKIP_POST_MERGE_SYNC:-0}" = "1" ]; then
  exit 0
fi
bash "${SYNC_SCRIPT}"
EOF

  chmod +x "${HOOKS_DIR}/post-merge"
  log "Installed hook: ${HOOKS_DIR}/post-merge"
  log "Any git pull that merges new commits will trigger reinstall+cleanup automation."
}

main "$@"
