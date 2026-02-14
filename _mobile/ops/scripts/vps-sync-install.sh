#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/robotville/BMAD}"
RBTV_REPO="${RBTV_REPO:-${WORKSPACE_ROOT}/_bmad/rbtv}"
MIRROR_ROOT="${RBTV_REPO}/_admin/docs/BMAD-mirror"
INSTALLER="${RBTV_REPO}/_config/install-rbtv.py"
MOBILE_DIR="${RBTV_REPO}/_mobile"

log() {
  printf '[vps-sync-install] %s\n' "$1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[vps-sync-install] ERROR: missing command: %s\n' "$1" >&2
    exit 1
  fi
}

restore_mirror_if_needed() {
  if [ -d "${MIRROR_ROOT}/_bmad" ]; then
    return
  fi

  # If sparse checkout hid the mirror, restore full checkout for sync.
  log "BMAD mirror not present in working tree. Restoring checkout view."
  git -C "${RBTV_REPO}" sparse-checkout disable || true
}

sync_mirror_into_workspace() {
  if [ ! -d "${MIRROR_ROOT}/_bmad" ]; then
    printf '[vps-sync-install] ERROR: mirror source missing at %s/_bmad\n' "${MIRROR_ROOT}" >&2
    exit 1
  fi

  mkdir -p "${WORKSPACE_ROOT}/_bmad"
  require_cmd rsync
  log "Syncing BMAD mirror into ${WORKSPACE_ROOT}/_bmad"
  rsync -a --exclude "rbtv/" "${MIRROR_ROOT}/_bmad/" "${WORKSPACE_ROOT}/_bmad/"
}

run_rbtv_installer() {
  if [ ! -f "${INSTALLER}" ]; then
    printf '[vps-sync-install] ERROR: installer not found at %s\n' "${INSTALLER}" >&2
    exit 1
  fi

  if command -v python3 >/dev/null 2>&1; then
    log "Running RBTV installer with python3"
    python3 "${INSTALLER}"
  elif command -v python >/dev/null 2>&1; then
    log "Running RBTV installer with python"
    python "${INSTALLER}"
  else
    printf '[vps-sync-install] ERROR: neither python3 nor python found\n' >&2
    exit 1
  fi
}

deploy_bootstrap_files() {
  # Copy Nanobot bootstrap files from _mobile/ into the workspace root.
  # Nanobot loads AGENTS.md, SOUL.md, TOOLS.md, USER.md from its
  # WorkingDirectory on every call. These files configure RBTV agent
  # identity, behavioral rules, command routing, and user context —
  # without them Nanobot uses its own defaults instead of RBTV workflows.
  #
  # Idempotent: cp -f overwrites existing files unconditionally.

  local bootstrap_files=("AGENTS.md" "SOUL.md" "TOOLS.md" "USER.md")
  local missing=0

  for f in "${bootstrap_files[@]}"; do
    if [ ! -f "${MOBILE_DIR}/${f}" ]; then
      printf '[vps-sync-install] WARNING: bootstrap source missing: %s/%s\n' "${MOBILE_DIR}" "${f}" >&2
      missing=$((missing + 1))
    fi
  done

  if [ "${missing}" -eq "${#bootstrap_files[@]}" ]; then
    printf '[vps-sync-install] ERROR: no bootstrap files found in %s — skipping bootstrap deploy\n' "${MOBILE_DIR}" >&2
    return 1
  fi

  log "Deploying bootstrap files from ${MOBILE_DIR} into ${WORKSPACE_ROOT}"
  for f in "${bootstrap_files[@]}"; do
    if [ -f "${MOBILE_DIR}/${f}" ]; then
      cp -f "${MOBILE_DIR}/${f}" "${WORKSPACE_ROOT}/${f}"
      log "  Deployed ${f}"
    fi
  done
}

deploy_skills() {
  # Sync Nanobot-compatible skill files from _mobile/skills/ into
  # workspace/skills/. Nanobot auto-summarizes skills from
  # skills/{name}/SKILL.md and loads them on demand.
  #
  # Uses rsync --delete so skills removed from _mobile/skills/ are also
  # removed from the workspace, keeping the two trees in lockstep.
  #
  # Idempotent: rsync only transfers changed files.

  local src="${MOBILE_DIR}/skills"
  local dest="${WORKSPACE_ROOT}/skills"

  if [ ! -d "${src}" ]; then
    log "No skills directory at ${src} — skipping skills deploy"
    return 0
  fi

  # Check if the source directory has any content.
  if [ -z "$(ls -A "${src}" 2>/dev/null)" ]; then
    log "Skills directory at ${src} is empty — skipping skills deploy"
    return 0
  fi

  require_cmd rsync
  mkdir -p "${dest}"
  log "Syncing skills from ${src}/ into ${dest}/"
  rsync -a --delete "${src}/" "${dest}/"
  log "  Skills deploy complete ($(ls -1d "${dest}"/*/ 2>/dev/null | wc -l) skill(s))"
}

hide_mirror_after_sync() {
  # Keep repository lean on VPS while preserving commit state.
  log "Applying sparse-checkout to hide BMAD mirror folder"
  git -C "${RBTV_REPO}" sparse-checkout init --no-cone
  git -C "${RBTV_REPO}" sparse-checkout set --no-cone "/*" "!/_admin/docs/BMAD-mirror/"
  git -C "${RBTV_REPO}" sparse-checkout reapply
}

main() {
  require_cmd git

  if [ ! -d "${RBTV_REPO}/.git" ]; then
    printf '[vps-sync-install] ERROR: git repo not found at %s\n' "${RBTV_REPO}" >&2
    exit 1
  fi

  log "Repository: ${RBTV_REPO}"
  restore_mirror_if_needed
  sync_mirror_into_workspace
  run_rbtv_installer
  deploy_bootstrap_files
  deploy_skills
  hide_mirror_after_sync
  log "Completed BMAD/RBTV reinstall + bootstrap deploy + mirror cleanup."
}

main "$@"
