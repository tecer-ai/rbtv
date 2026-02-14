# Robotville Deployment Smoke Report

Date (UTC): 2026-02-14  
Operator: AI (executed directly over SSH)  
Server: `rbtv-nanobot-gateway` (`89.167.21.172`)

---

## Scope

This report captures live validation evidence for:

- service deployment and startup baseline
- FR25 auto-restart after controlled process kill
- FR25 persistence after full VPS reboot

---

## Evidence Collected

### 1) Connectivity and host access

- SSH connectivity confirmed:
  - `connected`
  - host: `rbtv-nanobot-gateway`
  - UTC timestamp: `Sat Feb 14 03:28:40 AM UTC 2026`

### 2) Runtime baseline

- `nanobot` service user present:
  - `uid=999(nanobot) gid=988(nanobot)`
- binary responds:
  - `nanobot v0.1.0`
- service restarted and active:
  - `Loaded: ... enabled`
  - `Active: active (running)`
- config load check as service user succeeded:
  - `Config: /srv/nanobot/.nanobot/config.json ✓`
  - provider and model status printed without failure

### 3) Slack handshake/operation signals in logs

- Recent logs show successful Slack socket connect:
  - `Slack bot connected as U0AFD71DRFT`
- logs include inbound user events and responses, confirming runtime activity.

### 4) FR25 controlled termination test

Action:

- Captured `MainPID` from `nanobot-gateway`
- Sent `kill -9` to main process

Observed sequence:

- service entered `activating (auto-restart)` state
- systemd reported:
  - `Scheduled restart job, restart counter is at 1`
- service returned to:
  - `Active: active (running)` with new main PID

Result: PASS

### 5) FR25 reboot persistence test

Action:

- Triggered full `systemctl reboot`
- waited and reconnected over SSH

Observed sequence after reconnect:

- host reachable (`reboot-ok`)
- service auto-started on boot:
  - `Loaded: ... enabled`
  - `Active: active (running) since ...`

Result: PASS

---

## Issues Found

1. **Service unit Documentation warning**
   - systemd warned: `Invalid URL, ignoring` for the `Documentation=` value.
   - Cause: unit used a plain filesystem path where URL format is expected.
   - Fix applied in repo unit file:
     - changed to `Documentation=file:///opt/robotville/BMAD/_bmad/rbtv/_mobile/_docs/robotville-vps-access.md`

2. **Workspace path mismatch on VPS** (RESOLVED)
   - Initial condition: `/opt/robotville/BMAD` existed but did not contain the expected `_bmad/rbtv` tree.
   - Permanent remediation executed:
     - provisioned canonical repository path `/opt/robotville/BMAD/_bmad/rbtv`
     - restored working-tree + `.git` metadata at canonical path
     - redeployed systemd unit from canonical repo source path
   - Post-remediation verification:
     - `nanobot-gateway` returned `active (running)`
     - FR25 controlled kill/restart was re-validated (`restart counter is at 1`)

3. **Private repo auth gap on VPS** (RESOLVED)
   - Initial condition: direct `git clone`/`git pull` against `https://github.com/hlealt/rbtv.git` was blocked in server context due missing repository credentials.
   - Permanent remediation executed:
     - generated dedicated `nanobot` deploy key (`/srv/nanobot/.ssh/rbtv_deploy_key`)
     - added read-only GitHub deploy key access and `github.com` SSH trust
     - switched repository `origin` to `git@github.com:hlealt/rbtv.git`
   - Post-remediation verification:
     - `sudo -u nanobot ssh -T git@github.com` authenticated successfully
     - `sudo -u nanobot git fetch origin --prune` succeeded from canonical repo path
     - VPS repo was replaced with a clean origin clone (previous local-bootstrapped tree retained as backup)

4. **Manual post-pull reinstall dependency** (RESOLVED)
   - Initial condition: pulling RBTV updates depended on manual reinstall/cleanup steps, with risk of drift between RBTV repo state and BMAD instance state.
   - Permanent remediation executed:
     - added VPS scripts for pull + reinstall + mirror cleanup under `_mobile/ops/scripts/`
     - added hook installer script so `post-merge` triggers reinstall/cleanup automatically after `git pull`
     - updated runbook/access docs to standardize script-first operation
   - Post-remediation verification target:
     - use `sudo -u nanobot bash .../vps-pull-rbtv.sh` as the only update path
     - confirm mirror directory is hidden from VPS working tree after sync

---

## Smoke Checklist Outcome

- Service baseline: PASS
- Runtime/config readability: PASS
- FR25 kill/restart behavior: PASS
- FR25 reboot/startup behavior: PASS
- Overall verdict: **PASS** (canonical path contract now enforced on VPS)

---

## Follow-ups

1. Re-run full smoke checklist once more at next maintenance window (including reboot persistence) after path normalization.
2. Keep deployment operations canonical-path only (`/opt/robotville/BMAD/_bmad/rbtv`) and deploy-key auth only (no local bootstrap path).
3. Enforce script-first updates (`vps-pull-rbtv.sh`) and keep git hooks installed for automatic post-pull reinstall.
4. Continue with `p4-refs` and final checkpoint.

---

## Change Log

| Date | Change | By |
|---|---|---|
| 2026-02-14 | Initial smoke report with live FR25 evidence | AI |
| 2026-02-14 | Updated after canonical VPS path normalization and FR25 re-validation | AI |
| 2026-02-14 | Added deploy-key auth remediation and GitHub-origin sync verification | AI |
| 2026-02-14 | Added automated pull/reinstall/mirror-cleanup operating model | AI |

