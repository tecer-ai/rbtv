# Slack "Bot Not Answering" Troubleshooting Checklist

> **Purpose:** Diagnose why Nanobot does not respond in Slack after p2-3 configuration. Run these checks on the VPS via SSH.

---

## Quick Diagnostic Order

1. **Gateway running?** → Service + command
2. **Config found?** → HOME + config path
3. **Slack handshake OK?** → Logs
4. **User allowed?** → allowlist schema
5. **Interaction type** → @mention vs DM

---

## 1. Gateway Process

### 1.1 Is the service running?

```bash
systemctl status nanobot-gateway
```

- **Active (running)** → Proceed to 1.2
- **Failed / inactive** → Check `journalctl -u nanobot-gateway -n 50` for errors

### 1.2 Is NANOBOT_GATEWAY_CMD set?

The systemd unit runs `bash -lc "$NANOBOT_GATEWAY_CMD"`. If that variable is empty, the service will fail.

```bash
grep NANOBOT_GATEWAY_CMD /etc/robotville/nanobot-gateway.env
```

**Required value:** `NANOBOT_GATEWAY_CMD='nanobot gateway'` (or equivalent for your setup)

If missing, add to `/etc/robotville/nanobot-gateway.env`:

```bash
NANOBOT_GATEWAY_CMD='nanobot gateway'
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart nanobot-gateway
```

---

## 2. Config Path and HOME

Nanobot reads `~/.nanobot/config.json`. For the `nanobot` service user, `~` must resolve to the directory containing `.nanobot/`.

### 2.1 Where does Nanobot look?

```bash
sudo -u nanobot bash -c 'echo HOME=$HOME; ls -la $HOME/.nanobot/config.json 2>/dev/null || echo "Config not found"'
```

- If `HOME` is `/home/nanobot` but config is at `/srv/nanobot/.nanobot/config.json` → **Config will not be found.**

### 2.2 Fix: Set HOME in systemd

Add to the `[Service]` block of the systemd unit (before `ExecStart`):

```ini
Environment=HOME=/srv/nanobot
```

Or ensure `/etc/robotville/nanobot-gateway.env` has:

```bash
HOME=/srv/nanobot
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart nanobot-gateway
```

### 2.3 Verify config loads

```bash
sudo -u nanobot env HOME=/srv/nanobot nanobot status
```

You should see providers, channels, and model info. If you see errors about missing config or invalid JSON, fix the config file.

---

## 3. Slack Allowlist Schema (Common Bug)

The HKUDS Nanobot Slack config uses **different fields** than a single `allowFrom`:

| What you want | Correct config |
|---------------|----------------|
| Restrict DMs to specific users | `dm.policy: "allowlist"` and `dm.allow_from: ["U01234567", ...]` |
| Restrict channels to specific channels | `group_policy: "allowlist"` and `group_allow_from: ["C01234567", ...]` |
| Respond only when @mentioned in channels | `group_policy: "mention"` (default) |

**A top-level `allowFrom` in the Slack config is ignored** — Nanobot does not use it. If you put user IDs there, they have no effect.

### 3.1 Correct Slack config for user allowlist (DMs)

```json
"channels": {
  "slack": {
    "enabled": true,
    "bot_token": "xoxb-...",
    "app_token": "xapp-...",
    "group_policy": "mention",
    "dm": {
      "enabled": true,
      "policy": "allowlist",
      "allow_from": ["U01234567", "U08999999"]
    }
  }
}
```

- Replace `U01234567` with **your** Slack user ID.
- Get your ID: Slack → Profile → … → Copy member ID, or from a Slack API call.

### 3.2 If you want open DMs (no allowlist)

```json
"dm": {
  "enabled": true,
  "policy": "open"
}
```

`policy: "open"` (default) allows any user to DM the bot.

---

## 4. @Mention vs DM

With `group_policy: "mention"`:

- **In a channel:** You **must @mention the bot** (e.g. `@Robotville hello`). Plain messages are ignored.
- **In a DM:** The bot responds to all messages (unless `dm.policy` is `allowlist` and your ID is not in `dm.allow_from`).

**Check:** Are you DMing the bot or messaging in a channel? If in a channel, did you @mention it?

---

## 5. Slack App Configuration (Critical: Event Subscriptions)

**If logs show "Slack bot connected" but the bot never receives messages**, the WebSocket is up but Slack is not sending events. This almost always means **Event Subscriptions** are missing or incomplete.

### 5.1 Event Subscriptions — MUST configure

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → select your **robotville** app
2. Open **Event Subscriptions** in the left sidebar
3. Toggle **Enable Events** to **ON**
4. Under **Subscribe to bot events**, add:
   - `message.im` — required for DMs
   - `message.channels` — for channel messages (when @mentioned)
   - `app_mention` — for @mentions in channels
5. Click **Save Changes**
6. **Reinstall the app** if prompted: **Install App** → **Reinstall to Workspace** (events often require a fresh install)

### 5.2 Full checklist

| Setting | Required |
|---------|----------|
| **Socket Mode** | Toggle ON; App-Level Token with `connections:write` scope |
| **OAuth & Permissions** | Bot scopes: `chat:write`, `reactions:write`, `app_mentions:read` |
| **Event Subscriptions** | Toggle ON; subscribe to: `message.im`, `message.channels`, `app_mention` |
| **App Home** | Messages Tab enabled; "Allow users to send Slash commands and messages from the messages tab" checked |
| **Install to Workspace** | App installed; Bot Token (`xoxb-...`) and App Token (`xapp-...`) copied into config |

---

## 6. Logs

```bash
journalctl -u nanobot-gateway -f
```

Look for:

- `Slack bot connected as U...` → Handshake OK
- `Slack bot/app token not configured` → Tokens missing or wrong
- `auth_test failed` → Invalid bot token
- Any traceback or `Error` lines

---

## 7. LLM Provider

If Slack connects but the bot never replies, the LLM call may be failing:

- Check that the configured provider has a valid API key in config.
- Check logs for provider/auth errors after a message is received.

---

## Summary: Most Likely Fixes

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| **Connected but no events (no ping/responses)** | **Event Subscriptions not configured** | Enable Events, add `message.im`, `message.channels`, `app_mention`; reinstall app |
| Service fails immediately | `NANOBOT_GATEWAY_CMD` not set | Add to env file |
| Service runs but no Slack | Config not found | Set `HOME=/srv/nanobot` |
| Handshake fails | Wrong tokens / Slack app setup | Fix tokens and Slack app settings |
| DMs ignored | User not in `dm.allow_from` | Add your ID to `dm.allow_from` or use `dm.policy: "open"` |
| Channel messages ignored | Not @mentioning | Use `@BotName your message` |
| Receives but no reply | LLM provider error | Check API key and logs |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-14 | Initial creation after p2-3 Slack connectivity issues |
