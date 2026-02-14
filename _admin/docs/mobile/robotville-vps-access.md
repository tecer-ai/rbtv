# Robotville VPS Access Reference

> **Purpose:** Living operational document — server inventory, SSH access, access policy, and recovery procedures for the Robotville VPS.

---

## Server Inventory

| Field | Value |
|-------|-------|
| **Provider** | Hetzner Cloud |
| **Server name** | `rbtv-nanobot-gateway` |
| **Server ID** | `120963947` |
| **Region / Datacenter** | `hel1` (Helsinki) |
| **Image** | Ubuntu 24.04.3 LTS (Noble Numbat) |
| **vCPUs / RAM / Disk** | 2 vCPU / 4 GB / 80 GB |
| **Public IPv4** | `89.167.21.172` |
| **Public IPv6** | `2a01:4f9:c014:400e::/64` |
| **Private network** | none |
| **Backups enabled** | No |
| **Provisioned date** | 2026-02-14 |

---

## SSH Endpoint

### Connection Command

```bash
ssh root@89.167.21.172
```

> **Windows note:** If SSH prompts for a passphrase each time, load the key into the agent first: `ssh-add $env:USERPROFILE\.ssh\id_ed25519` (requires `ssh-agent` service running).

### SSH Key Details

| Field | Value |
|-------|-------|
| **Key type** | Ed25519 |
| **Public key path** | `~/.ssh/id_ed25519.pub` |
| **Private key path** | `~/.ssh/id_ed25519` |
| **Passphrase** | Set (do NOT record the passphrase here) |

### SSH Configuration (applied p1-3)

| Setting | Value |
|---------|-------|
| **Root login** | Key-only (`prohibit-password`) |
| **Password auth** | Disabled |
| **Port** | `22` (default) |
| **Max auth tries** | 3 per connection |
| **Idle timeout** | 5 min (300s interval, 2 retries) |
| **X11 / Agent forwarding** | Disabled |
| **Config file** | `/etc/ssh/sshd_config.d/99-robotville-hardening.conf` |
| **fail2ban** | Enabled — bans IP for 2h after 3 failed SSH attempts |

---

## API Access

| Field | Value |
|-------|-------|
| **Permissions** | Read & Write |
| **Storage location** | Password manager / local env var `HCLOUD_TOKEN` (never in repo) |
| **CLI verify command** | `hcloud server list` (with `HCLOUD_TOKEN` set) |

> **Security rule:** The API token is NEVER stored in this file or in any committed file. Store it in a password manager and reference it via environment variable `HCLOUD_TOKEN` when needed.

---

## Workspace Path Contract

| Item | Canonical Path |
|------|----------------|
| Workspace root | `/opt/robotville/BMAD` |
| RBTV repo root | `/opt/robotville/BMAD/_bmad/rbtv` |
| Systemd unit source in repo | `/opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/systemd/nanobot-gateway.service` |

> Operational rule: do not deploy from ad-hoc alternate layouts. Normalize the VPS to these canonical paths first.

---

## Private Repo Pull Access (Deploy Key)

| Item | Value |
|------|-------|
| GitHub repo | `git@github.com:hlealt/rbtv.git` |
| Access mode | Read-only deploy key |
| Service account | `nanobot` |
| Private key path (VPS) | `/srv/nanobot/.ssh/rbtv_deploy_key` |
| Public key path (VPS) | `/srv/nanobot/.ssh/rbtv_deploy_key.pub` |
| SSH config path | `/srv/nanobot/.ssh/config` |
| Known hosts path | `/srv/nanobot/.ssh/known_hosts` |

Validation commands:

```bash
sudo -u nanobot ssh -T git@github.com
sudo -u nanobot git -C /opt/robotville/BMAD/_bmad/rbtv remote -v
sudo -u nanobot git -C /opt/robotville/BMAD/_bmad/rbtv fetch origin --prune
```

---

## Automated Pull/Reinstall Contract

RBTV updates on VPS must run through automation scripts under:

- `/opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/`

Scripts:

- `vps-install-git-hooks.sh` — installs `post-merge` hook to auto-run reinstall/cleanup after `git pull`.
- `vps-pull-rbtv.sh` — canonical pull entrypoint (fetch/pull + reinstall + mirror cleanup).
- `vps-sync-install.sh` — reinstall + cleanup routine (called by hook and pull script).

First-time setup:

```bash
chmod +x /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/*.sh
sudo -u nanobot bash /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/vps-install-git-hooks.sh
```

Operational update command:

```bash
sudo -u nanobot bash /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/vps-pull-rbtv.sh
```

Result expected after update:

- BMAD and RBTV instance content is reinstalled from current RBTV state.
- Local `_admin/docs/BMAD-mirror/` is hidden from VPS working tree after reinstall.

---

## Access Policy

### Who Has Access

| Person | Access Type | Purpose |
|--------|-------------|---------|
| Henri | SSH + API + Hetzner Console | Full admin — provisioning, security, operations |

### Access Rules

1. **SSH key only** — No password-based SSH authentication (enforced in sshd config).
2. **Firewall deny-all** — UFW denies all inbound traffic except SSH (port 22). No HTTP, no HTTPS, no other ports. IP-level restriction can be added via `ufw delete allow ssh` + `ufw allow from <IP> to any port 22` if needed.
3. **No inbound services** — VPS has no public-facing ports besides SSH. Slack Socket Mode is outbound-only (NFR5, NFR6).
4. **API token discipline** — API tokens stored only in password managers or local `.env` files with `chmod 600`. Never committed to version control.
5. **Allowlist for users** — End-user (Slack) access is controlled via Nanobot allowlist configuration, not VPS-level access (FR20-FR22).
6. **Principle of least privilege** — Only grant the minimum access needed. Admin SSH access is for operations only.

### Secrets Inventory (references only — no values)

| Secret | Location | Rotation Policy |
|--------|----------|-----------------|
| SSH private key | Local workstation `~/.ssh/id_ed25519` | Rotate if compromised |
| VPS deploy key (private) | `/srv/nanobot/.ssh/rbtv_deploy_key` | Revoke deploy key in GitHub and reissue on compromise |
| Hetzner API token | Password manager | Rotate if compromised; regenerate via Console |
| Slack bot token | VPS `.env` file | Rotate via Slack app settings if compromised |
| Slack app token | VPS `.env` file | Rotate via Slack app settings if compromised |
| LLM provider API key | VPS `.env` file | Rotate via provider dashboard if compromised |

---

## Recovery Notes

### Scenario: Cannot SSH into VPS

1. **Check your IP** — Firewall may be restricting to specific IPs. If your IP changed (e.g. ISP, VPN), update the firewall rule via Hetzner Console or API.
2. **Check SSH key** — Ensure you're using the correct private key: `ssh -i ~/.ssh/id_ed25519 -v root@89.167.21.172` (verbose mode for debugging).
3. **Check server status** — In Hetzner Console, confirm the server is running. If stopped, start it.
4. **Hetzner Console rescue** — If locked out:
   - Go to Console → Server → **Rescue** tab.
   - Enable rescue mode (sets a temporary root password).
   - Reboot the server (it boots into rescue).
   - SSH in with the rescue password.
   - Mount the filesystem and fix SSH config / firewall rules.
   - Disable rescue mode and reboot normally.
5. **Rebuild as last resort** — If the server is unrecoverable, create a new server from the same project with your SSH key. Re-run setup from p1-3 onward. Project data on the old server will be lost unless backed up.

### Scenario: Nanobot Process Crashed

1. **FR25 auto-restart** — The systemd service (configured in p1-4) should auto-restart the process. Check with:
   ```bash
   systemctl status nanobot-gateway
   ```
2. **Manual restart** — If the service is stopped or failed:
   ```bash
   systemctl restart nanobot-gateway
   ```
3. **Check logs** — Review recent output for crash cause:
   ```bash
   journalctl -u nanobot-gateway --since "10 minutes ago"
   ```
4. **Verify Slack connectivity** — After restart, send a test message in Slack to confirm the bot responds.

### Scenario: VPS Is Unreachable (not just SSH)

1. **Check Hetzner status page** — [https://status.hetzner.com/](https://status.hetzner.com/) for provider outages.
2. **Check via API** — If you have `hcloud` CLI configured:
   ```bash
   hcloud server describe rbtv-nanobot-gateway
   ```
3. **Power cycle via Console/API** — In Hetzner Console: Server → Power → **Reset** (hard reboot). Or via API:
   ```bash
   hcloud server reboot rbtv-nanobot-gateway
   ```
4. **If still unreachable** — Open a Hetzner support ticket.

### Scenario: Need to Rebuild From Scratch

If the VPS must be rebuilt (e.g. corrupted OS, unrecoverable config):

1. Create a new server in the same Hetzner project with the same SSH key.
2. Follow the provisioning guide: `hetzner-p1-1-provisioning-guide.md`.
3. Apply security baseline: p1-3 task.
4. Install Nanobot and configure integrations: Phase 2 tasks.
5. Deploy RBTV `_mobile` harness: Phase 3 tasks.
6. **Data recovery** — Project data (`project-memo` files, framework outputs) is only on the VPS filesystem. If not backed up, it is lost. Consider periodic backups (see below).

### Backup Recommendations (Post-Prototype)

| Method | Frequency | What It Covers |
|--------|-----------|---------------|
| Hetzner snapshots | Weekly or before major changes | Full disk image — OS + data + config |
| `rsync` to local machine | Daily or on-demand | Project output files and `.env` backup |
| Hetzner automated backups | If enabled at server creation | Provider-managed weekly snapshots |

> **Prototype phase:** Manual `rsync` or Hetzner snapshots before risky operations is sufficient. Automated backups can be added post-prototype.

---

## Quick Reference Card

| Action | Command / Location |
|--------|--------------------|
| SSH in | `ssh root@89.167.21.172` |
| Check server status | Hetzner Console or `hcloud server describe rbtv-nanobot-gateway` |
| Check Nanobot status | `systemctl status nanobot-gateway` |
| Restart Nanobot | `systemctl restart nanobot-gateway` |
| View Nanobot logs | `journalctl -u nanobot-gateway -f` |
| Bot not answering on Slack | See `slack-troubleshooting-checklist.md` |
| Reboot VPS | `hcloud server reboot rbtv-nanobot-gateway` or Console |
| Power off VPS | `hcloud server shutdown rbtv-nanobot-gateway` or Console |
| Update RBTV code | SSH in → `sudo -u nanobot bash /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/scripts/vps-pull-rbtv.sh` |
| Check fail2ban | `fail2ban-client status sshd` |
| Hetzner status page | [https://status.hetzner.com/](https://status.hetzner.com/) |

---

## Change Log

| Date | Change | By |
|------|--------|----|
| 2026-02-14 | Initial creation with placeholder values (p1-2) | Henri |
| 2026-02-14 | Filled real server values; applied p1-3 security baseline (SSH hardening, UFW, fail2ban) | AI |
| 2026-02-14 | Added canonical workspace path contract for deployment operations | AI |
| 2026-02-14 | Added deploy-key private repo pull contract for VPS operations | AI |
| 2026-02-14 | Added automated pull/reinstall/cleanup script contract for VPS updates | AI |
