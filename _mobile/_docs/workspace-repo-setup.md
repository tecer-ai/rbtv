# Workspace Repo Setup Guide

> **Purpose:** Instructions for creating and configuring the nanobot workspace GitHub repo, and bootstrapping a new VPS from scratch.

The nanobot workspace is a private GitHub repository that serves as the working directory for nanobot on the VPS. It contains version-controlled bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`, `skills/`) that define agent behavior.

---

## Workspace Repo Structure

```
workspace-repo/
├── .gitignore            # Whitelist: tracks only bootstrap files
├── AGENTS.md             # Agent routing definitions
├── SOUL.md               # Behavioral contract
├── TOOLS.md              # Command routing + tool reference
├── USER.md               # User preferences and context
├── SLACK.md              # Slack mrkdwn formatting rules (loaded on demand)
├── entry_points.md       # Manually maintained workflow entrypoints
└── skills/               # Nanobot skills (tracked when ready)
    ├── doc/SKILL.md
    ├── quality-review/SKILL.md
    └── web-research/SKILL.md
```

Bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) and the on-demand file `SLACK.md` are sourced from `_bmad/rbtv/_mobile/` in the RBTV repo — copy them to the workspace repo root and update as RBTV evolves.

---

## Template `.gitignore`

Use a whitelist strategy: ignore everything by default, then explicitly un-ignore the bootstrap files.

```gitignore
# Workspace repo .gitignore — whitelist strategy
# Ignore everything by default
*

# Un-ignore bootstrap files
!.gitignore
!AGENTS.md
!SOUL.md
!TOOLS.md
!USER.md
!SLACK.md
!entry_points.md

# Un-ignore skills directory
!skills/
!skills/**

# Un-ignore this guide
!README.md
```

---

## `entry_points.md` Template

Manually maintained index of RBTV workflow entry points. Update after adding or removing RBTV agents or workflows.

```markdown
# RBTV Entry Points

> Manually maintained. Update after adding or removing agents or workflows.

## Agents

| Command | Agent File | Description |
|---------|------------|-------------|
| `mentor` | `_bmad/rbtv/agents/mentor.md` | YC Mentor — business innovation lifecycle |
| `domcobb` | `_bmad/rbtv/agents/domcobb.md` | Problem Architect — structured thinking |
| `doc` | `_bmad/rbtv/agents/ana.md` | Ana — documentation and handoffs |

## Config

| File | Purpose |
|------|---------|
| `_bmad/rbtv/_config/config.yaml` | RBTV module config (user_name, language, output paths) |

## Output

| Path | Contents |
|------|---------|
| `_bmad-output/{project-name}/` | Project outputs (framework docs, project-memo) |
```

---

## Bootstrap Sequence (New VPS)

Follow this sequence when provisioning a new VPS from scratch.

### Prerequisites

- Hetzner VPS running Ubuntu 24.04 LTS
- SSH key access configured (see `robotville-vps-access.md`)
- GitHub deploy key for RBTV repo (read-only, owned by `nanobot` user)
- GitHub deploy key or HTTPS access for workspace repo

### Step 1 — System baseline

Apply security baseline and create service user:

```bash
# Create nanobot user and home
useradd -m -d /srv/nanobot -s /bin/bash nanobot

# Apply UFW firewall (deny all, allow SSH)
ufw default deny incoming
ufw allow ssh
ufw enable

# Install required packages
apt update && apt install -y git python3 python3-pip curl nodejs npm fail2ban
```

### Step 2 — Install Nanobot

```bash
# Install nanobot (check nanobot docs for latest install command)
pip install nanobot

# Initialize nanobot config as nanobot user
sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot init
```

### Step 3 — Install BMAD

Clone or install BMAD at the workspace root:

```bash
mkdir -p /opt/robotville/BMAD
# Clone BMAD or install via its installer
# Refer to BMAD installation docs for the current method
```

### Step 4 — Clone workspace repo

```bash
# Clone workspace repo as nanobot user (workspace becomes BMAD root)
sudo -u nanobot git clone <workspace-repo-url> /opt/robotville/BMAD
```

After cloning, workspace root `/opt/robotville/BMAD` contains the bootstrap files (`AGENTS.md`, `SOUL.md`, etc.) from the workspace repo.

### Step 5 — Clone RBTV repo

```bash
# Set up deploy key for RBTV (owned by nanobot user)
# See robotville-vps-access.md → Private Repo Pull Access section

# Clone RBTV into BMAD _bmad slot
sudo -u nanobot git clone git@github.com:hlealt/rbtv.git \
  /opt/robotville/BMAD/_bmad/rbtv
```

### Step 6 — Run RBTV sync installer

```bash
cd /opt/robotville/BMAD/_bmad/rbtv
sudo -u nanobot python3 _config/install-rbtv.py --mode sync
```

This patches BMAD configs (output paths, help catalog) without generating IDE artifacts.

### Step 7 — Configure Nanobot

Populate the env file and Nanobot config. Use templates from:
- `_mobile/_docs/server-env-template.md` — env file template and config.json template

```bash
mkdir -p /etc/robotville
sudoedit /etc/robotville/nanobot-gateway.env
sudo chown root:nanobot /etc/robotville/nanobot-gateway.env
sudo chmod 640 /etc/robotville/nanobot-gateway.env
```

Set `workspace` in `/srv/nanobot/.nanobot/config.json` to `/opt/robotville/BMAD`.

### Step 8 — Install systemd service

```bash
sudo cp /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/systemd/nanobot-gateway.service \
  /etc/systemd/system/nanobot-gateway.service
sudo systemctl daemon-reload
sudo systemctl enable nanobot-gateway
sudo systemctl start nanobot-gateway
```

### Step 9 — Verify

```bash
systemctl status nanobot-gateway --no-pager
journalctl -u nanobot-gateway -f
```

Then run the smoke checklist: `_mobile/_docs/smoke-checklist.md`.

---

## Update Flows

### Bootstrap file changes (workspace repo)

When `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`, or `SLACK.md` change in the workspace repo:

```bash
# Push from workstation
git push

# Pull on VPS (as nanobot)
sudo -u nanobot git -C /opt/robotville/BMAD pull --ff-only

# Restart nanobot to pick up new bootstrap files
sudo systemctl restart nanobot-gateway
```

### RBTV code changes

When agents, workflows, tasks, or config change in the RBTV repo:

```bash
# Pull on VPS (as nanobot)
sudo -u nanobot git -C /opt/robotville/BMAD/_bmad/rbtv pull --ff-only

# Re-run sync to update BMAD configs
sudo -u nanobot python3 /opt/robotville/BMAD/_bmad/rbtv/_config/install-rbtv.py --mode sync

# Restart nanobot
sudo systemctl restart nanobot-gateway
```

### BMAD updates

When upgrading the BMAD CLI or installation:

```bash
# Reinstall BMAD (follow BMAD upgrade docs)
# Then re-run RBTV sync installer
sudo -u nanobot python3 /opt/robotville/BMAD/_bmad/rbtv/_config/install-rbtv.py --mode sync
sudo systemctl restart nanobot-gateway
```

---

## Change Log

| Date | Change | By |
|------|--------|----|
| 2026-02-23 | Initial creation — workspace setup guide for nanobot standard architecture | AI |
