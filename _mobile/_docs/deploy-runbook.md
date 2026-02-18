# Robotville Mobile Deployment Runbook

> Purpose: Execute and verify the VPS-side deployment for Nanobot gateway + RBTV `_mobile` harness in a safe, repeatable order.

---

## Scope

- Applies to the live Hetzner VPS documented in `robotville-vps-access.md`.
- Covers deployment and verification for current scoped features (including FR25 auto-restart).
- Excludes deferred scope: FR23, FR24, FR26.

---

## Prerequisites

1. SSH access works:
   - `ssh root@89.167.21.172`
2. RBTV repo is present on VPS:
   - expected repo root: `/opt/robotville/BMAD/_bmad/rbtv`
3. Service user exists:
   - `id nanobot`
4. Nanobot binary is installed:
   - `sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot --version`
5. GitHub deploy-key access is configured for private repo pulls:
   - `sudo -u nanobot ssh -T git@github.com`
6. VPS automation scripts are executable:
   - `chmod +x /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/*.sh`

If any prerequisite fails, stop and resolve before continuing.

---

## Deployment Paths (Resolve First)

| Item | Path |
|---|---|
| Workspace root (canonical) | `/opt/robotville/BMAD` |
| RBTV repo root (canonical) | `/opt/robotville/BMAD/_bmad/rbtv` |
| Env file | `/etc/robotville/nanobot-gateway.env` |
| Nanobot config | `/srv/nanobot/.nanobot/config.json` |
| Systemd unit | `/etc/systemd/system/nanobot-gateway.service` |
| Unit source in repo | `/opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/systemd/nanobot-gateway.service` |

The deployment contract is canonical-path only. If canonical paths are missing, stop and normalize the VPS layout before proceeding.

---

## Step 1 - Preflight Snapshot

Run before making changes:

```bash
set -euo pipefail
date -u
hostnamectl --static
systemctl --version | head -n 1
sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot --version
ls -la /opt/robotville
ls -la /opt/robotville/BMAD
ls -la /opt/robotville/BMAD/_bmad/rbtv
test -f /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/systemd/nanobot-gateway.service
```

Record current service state:

```bash
systemctl status nanobot-gateway --no-pager || true
journalctl -u nanobot-gateway -n 30 --no-pager || true
```

---

## Step 2 - Update Code and Verify Harness Files

```bash
chmod +x /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/*.sh
sudo -u nanobot bash /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/vps-install-git-hooks.sh
sudo -u nanobot bash /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/vps-pull-rbtv.sh
```

What this automates on every pull:

1. Restores full checkout view.
2. Pulls latest `origin/master` with fast-forward only.
3. Reinstalls BMAD + RBTV instance state from mirror + installer.
4. Deploys Nanobot bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) from `_mobile/` into workspace root.
5. Syncs Nanobot skills from `_mobile/skills/` into `workspace/skills/`.
6. Re-applies sparse checkout to remove local `_admin/docs/BMAD-mirror/` from VPS working tree.

Confirm phase-3 harness files are present:

```bash
ls -la /opt/robotville/BMAD/_bmad/rbtv/_mobile/integration/nanobot-gateway-bridge.ts
ls -la /opt/robotville/BMAD/_bmad/rbtv/_mobile/routing/command-router.ts
ls -la /opt/robotville/BMAD/_bmad/rbtv/_mobile/security/allowlist-gate.ts
ls -la /opt/robotville/BMAD/_bmad/rbtv/_mobile/state/project-memo-adapter.ts
```

Confirm bootstrap files deployed to workspace root:

```bash
ls -la /opt/robotville/BMAD/AGENTS.md
ls -la /opt/robotville/BMAD/SOUL.md
ls -la /opt/robotville/BMAD/TOOLS.md
ls -la /opt/robotville/BMAD/USER.md
ls -la /opt/robotville/BMAD/skills/
```

If the repo path above does not exist, stop and normalize the VPS workspace to the canonical contract before any deployment action.

If GitHub auth fails in this step, restore VPS deploy-key access first (see `robotville-vps-access.md`) before continuing.

---

## Step 3 - Apply Environment and Config

Populate env file using template guidance:

- `server-env-template.md`
- `slack-troubleshooting-checklist.md`

Edit env file:

```bash
sudoedit /etc/robotville/nanobot-gateway.env
```

Set secure permissions:

```bash
sudo chown root:nanobot /etc/robotville/nanobot-gateway.env
sudo chmod 640 /etc/robotville/nanobot-gateway.env
```

Ensure required keys exist:

```bash
sudo grep -E '^(NANOBOT_SLACK_BOT_TOKEN|NANOBOT_SLACK_APP_TOKEN|NANOBOT_PROVIDER|HOME)=' /etc/robotville/nanobot-gateway.env
```

Validate Nanobot can read config as service user:

```bash
sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot status
```

---

## Step 4 - Deploy/Refresh Systemd Unit

Copy unit from repository:

```bash
sudo cp /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/systemd/nanobot-gateway.service /etc/systemd/system/nanobot-gateway.service
sudo chown root:root /etc/systemd/system/nanobot-gateway.service
sudo chmod 644 /etc/systemd/system/nanobot-gateway.service
```

Reload and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl cat nanobot-gateway
```

---

## Step 5 - Start and Enable Service (FR25 Baseline)

```bash
sudo systemctl enable nanobot-gateway
sudo systemctl restart nanobot-gateway
sudo systemctl status nanobot-gateway --no-pager
```

Follow logs for handshake:

```bash
journalctl -u nanobot-gateway -f
```

Expected signal:

- Slack connection line appears (for example: bot connected/auth OK)
- No repeated crash loop

---

## Step 6 - Functional Smoke (Live)

1. DM the bot from an allowlisted Slack user with:
   - `mentor`
2. In a channel, test mention behavior:
   - `@BotName mentor`
3. Confirm unsupported command behavior:
   - `@BotName unknown-command`

If bot does not answer, execute `slack-troubleshooting-checklist.md` in order.

---

## Step 7 - FR25 Auto-Restart Check

Controlled termination test:

```bash
MAIN_PID="$(systemctl show -p MainPID --value nanobot-gateway)"
echo "Main PID: ${MAIN_PID}"
sudo kill -9 "${MAIN_PID}"
sleep 3
systemctl status nanobot-gateway --no-pager
```

Pass criteria:

- Service returns to `active (running)` automatically.
- Logs show restart cycle without manual intervention.

---

## Step 8 - Apply Optimization Patches

After code update (Step 2) and config (Step 3), apply Nanobot source patches and config patches. These are idempotent — safe to re-run.

### 8.1 Config patches (run as nanobot)

```bash
cd /opt/robotville/BMAD/_bmad/rbtv
sudo -u nanobot python3 _mobile/ops/patches/update-nanobot-memory-window.py /srv/nanobot/.nanobot/config.json
```

### 8.2 Source patches (modify litellm_provider.py)

```bash
cd /opt/robotville/BMAD/_bmad/rbtv
sudo -u nanobot python3 _mobile/ops/patches/add-litellm-prompt-caching.py
sudo -u nanobot python3 _mobile/ops/patches/add-litellm-retries.py
```

### 8.3 Verify config values

```bash
sudo -u nanobot python3 -c "
import json; c = json.load(open('/srv/nanobot/.nanobot/config.json'))
d = c.get('agents',{}).get('defaults',{})
print(f\"model: {d.get('model')}\")
print(f\"memory_window: {d.get('memory_window')}\")
"
```

Expected: `memory_window: 20` and current model.

### 8.4 Restart service after patches

```bash
sudo systemctl restart nanobot-gateway
systemctl status nanobot-gateway --no-pager
```

> **After Nanobot upgrades:** Re-run Step 8.2 source patches. They will fail gracefully if the target pattern changed — review and update the patch scripts as needed.

---

## Step 9 - p6-2 Netlify Deploy Credentials (robotville.ai)

Run once after Netlify site is provisioned (p6-1) and you have the personal access token (A4). Site ID is in `netlify-site-info.md`.

**Prerequisites:** `NETLIFY_AUTH_TOKEN` from Netlify (User settings → Personal access tokens). Do not commit the token.

### 8.1 Add token to env file

```bash
sudoedit /etc/robotville/nanobot-gateway.env
```

Append (replace with your real token):

```bash
# Netlify deploy (p6-2)
NETLIFY_AUTH_TOKEN=nfp_YOUR_TOKEN_HERE
NETLIFY_SITE_ID=86ed1ff3-dd59-4428-a426-219518589906
```

Keep permissions:

```bash
sudo chown root:nanobot /etc/robotville/nanobot-gateway.env
sudo chmod 640 /etc/robotville/nanobot-gateway.env
```

### 8.2 Install Netlify CLI on VPS

```bash
sudo npm install -g netlify-cli
netlify --version
```

### 8.3 Link CLI to site (as nanobot, one-time)

Replace `nfp_YOUR_TOKEN_HERE` with the real token (or ensure it is already in env and source it):

```bash
sudo -u nanobot env HOME=/srv/nanobot bash -c '
  source /etc/robotville/nanobot-gateway.env 2>/dev/null || true
  export NETLIFY_AUTH_TOKEN
  netlify link --id 86ed1ff3-dd59-4428-a426-219518589906
'
```

When prompted for site name, press Enter to accept default.

### 8.4 Test deploy as nanobot

```bash
sudo -u nanobot env HOME=/srv/nanobot bash -c '
  source /etc/robotville/nanobot-gateway.env 2>/dev/null || true
  export NETLIFY_AUTH_TOKEN
  mkdir -p /tmp/netlify-test
  echo "<h1>Test deploy</h1>" > /tmp/netlify-test/index.html
  netlify deploy --dir=/tmp/netlify-test --prod
'
```

Pass criteria:

- Command completes without "Not logged in" or "Invalid token".
- Production URL is printed; https://robotville.ai shows updated or test content when Netlify finishes propagating.

---

## Rollback Procedure

If deployment causes regression:

1. Revert RBTV repo to previous known-good commit.
2. Re-copy prior systemd unit version (if changed).
3. Restart service:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl restart nanobot-gateway`
4. Confirm recovery:
   - `systemctl status nanobot-gateway --no-pager`
   - `journalctl -u nanobot-gateway -n 50 --no-pager`

---

## Operator Notes

- Keep secrets out of git and local screenshots.
- Always validate with `nanobot` service user context (`HOME=/srv/nanobot`).
- Do not add non-scoped features during deployment (FR23/24/26 remain deferred).
- Use `nanobot` account for repository operations to ensure deploy-key auth and consistent ownership.

---

## Change Log

| Date | Change | By |
|---|---|---|
| 2026-02-14 | Initial runbook created for p4-1 | AI |
| 2026-02-14 | Added workspace path resolution and SCP fallback from live validation | AI |
| 2026-02-14 | Enforced canonical VPS path contract and removed SCP fallback branch | AI |
| 2026-02-14 | Added deploy-key-based GitHub pull flow for private repo updates | AI |
| 2026-02-14 | Added automated pull+reinstall+mirror-cleanup scripts and git-hook install step | AI |
| 2026-02-14 | Added Step 8 — p6-2 Netlify deploy credentials (install CLI, env token, link, test deploy) | AI |

