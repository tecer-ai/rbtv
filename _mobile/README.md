# RBTV `_mobile` — Nanobot Integration

This folder contains the RBTV integration layer for Nanobot: bootstrap files, operational docs, config helpers, systemd service definition, and website HTML.

---

## Architecture

Nanobot is a Slack bot runtime. RBTV integrates with it through two mechanisms:

1. **Bootstrap files** — Markdown files loaded into Nanobot's system prompt on every call. They define agent routing, behavioral rules, tool reference, and user preferences. These live in the workspace GitHub repo (not deployed by RBTV — the workspace IS the repo).
2. **Config** — `_config/install-rbtv.py --mode sync` patches BMAD configs to integrate RBTV output paths and help catalog entries.

There is no TypeScript harness, no shell automation scripts, and no source patches. The integration is pure markdown.

---

## VPS Layout

```
/opt/robotville/
├── BMAD/                          # Workspace repo root (private GitHub repo)
│   ├── AGENTS.md                  # ← bootstrap: agent routing
│   ├── SOUL.md                    # ← bootstrap: behavioral contract
│   ├── TOOLS.md                   # ← bootstrap: command routing + tool reference
│   ├── USER.md                    # ← bootstrap: user preferences
│   ├── entry_points.md            # ← manually maintained workflow index
│   ├── skills/                    # ← bootstrap: Nanobot skills
│   │   ├── doc/SKILL.md
│   │   ├── quality-review/SKILL.md
│   │   └── web-research/SKILL.md
│   └── _bmad/
│       └── rbtv/                  # ← RBTV repo (this repo)
│           └── _mobile/           # ← this folder
└── .venv/                         # Nanobot virtualenv (root-owned)

/srv/nanobot/                      # Nanobot service user home
└── .nanobot/config.json           # Nanobot config (workspace, model, allowlist)

/etc/robotville/
└── nanobot-gateway.env            # Secrets and credentials (root:nanobot, 640)

/etc/systemd/system/
└── nanobot-gateway.service        # Systemd unit (sourced from ops/systemd/)
```

---

## Server Access

| Field | Value |
|-------|-------|
| Provider | Hetzner Cloud |
| Server | `rbtv-nanobot-gateway` |
| IPv4 | `89.167.21.172` |
| SSH | `ssh root@89.167.21.172` |
| Nanobot status | `systemctl status nanobot-gateway` |
| Nanobot logs | `journalctl -u nanobot-gateway -f` |

Full access details, recovery procedures, and secrets inventory: `_docs/robotville-vps-access.md`.

---

## Update Flows

### Bootstrap file changes (workspace repo)

When `AGENTS.md`, `SOUL.md`, `TOOLS.md`, or `USER.md` change:

```bash
# Push from workstation → pull on VPS
sudo -u nanobot git -C /opt/robotville/BMAD pull --ff-only
sudo systemctl restart nanobot-gateway
```

### RBTV changes (agents, workflows, config)

```bash
sudo -u nanobot git -C /opt/robotville/BMAD/_bmad/rbtv pull --ff-only
sudo -u nanobot python3 /opt/robotville/BMAD/_bmad/rbtv/_config/install-rbtv.py --mode sync
sudo systemctl restart nanobot-gateway
```

### First-time VPS setup

See `_docs/workspace-repo-setup.md` for the full bootstrap sequence.

---

## Directory Index

| Path | Contents |
|------|---------|
| `AGENTS.md` | Agent routing — commands to agent files |
| `SOUL.md` | Behavioral contract — inviolable rules for all agents |
| `TOOLS.md` | Command routing table, deploy commands, tool reference |
| `USER.md` | User preferences and session behavior |
| `_docs/` | Operational docs — see table below |
| `ops/helpers/` | Admin helper scripts (allowlist, memory window, model) |
| `ops/systemd/` | Systemd service unit definition |
| `skills/` | Nanobot skill files |
| `web/` | Website HTML (robotville.ai Netlify placeholder pages) |

### Operational Docs (`_docs/`)

| Doc | Purpose |
|-----|---------|
| `workspace-repo-setup.md` | New VPS bootstrap sequence, workspace repo template |
| `deploy-runbook.md` | Full deployment runbook — update, config, Netlify credentials |
| `robotville-vps-access.md` | Server inventory, SSH access, recovery procedures |
| `server-env-template.md` | Env file template and Nanobot config template |
| `slack-troubleshooting-checklist.md` | Bot not answering? Start here |
| `smoke-checklist.md` | Post-deployment validation checklist |
| `hetzner-p1-1-provisioning-guide.md` | Initial VPS provisioning guide |

---

## Nanobot Configuration Notes

- **Workspace:** Set `agents.defaults.workspace` to `/opt/robotville/BMAD` in `config.json`.
- **Allowlist:** Use `dm.policy: "allowlist"` and `dm.allow_from` in `config.json` for DM access control.
- **Prompt caching & retries:** Native to Nanobot since Feb 2026. No source patches required. Use `LITELLM_NUM_RETRIES` env var for custom retry counts.
- **Memory window:** Set via `_mobile/ops/helpers/update-nanobot-memory-window.py`. Target: `20`.
