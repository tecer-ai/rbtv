# Robotville Deployment Smoke Checklist

> Use this checklist immediately after deployment to validate routing, allowlist behavior, state continuity, and FR25 restart resilience.

---

## How to Use

- Mark each item as `[ ]` before test, `[x]` when passed.
- Record evidence (command output snippets, timestamps, Slack message links) in your smoke report.
- Stop on any critical failure and run rollback/recovery from `deploy-runbook.md`.

---

## A) Service and Runtime Baseline

- [ ] `systemctl status nanobot-gateway --no-pager` shows `active (running)`.
- [ ] `journalctl -u nanobot-gateway -n 50 --no-pager` shows no crash loop.
- [ ] `sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot status` succeeds.
- [ ] Env file exists with restricted permissions (`root:nanobot`, `640`).
- [ ] Canonical workspace path exists: `/opt/robotville/BMAD/_bmad/rbtv`.
- [ ] Private repo access works from VPS (`sudo -u nanobot git fetch origin --prune` succeeds).
- [ ] Config helpers exist in `_mobile/ops/helpers/`.

Commands:

```bash
systemctl status nanobot-gateway --no-pager
journalctl -u nanobot-gateway -n 50 --no-pager
sudo -u nanobot env HOME=/srv/nanobot /usr/local/bin/nanobot status
ls -l /etc/robotville/nanobot-gateway.env
ls -la /opt/robotville/BMAD/_bmad/rbtv
sudo -u nanobot git -C /opt/robotville/BMAD/_bmad/rbtv fetch origin --prune
ls /opt/robotville/BMAD/_bmad/rbtv/_mobile/ops/helpers/
```

---

## B) Allowlist Gate Validation

- [ ] Allowlisted user can DM bot and receive response.
- [ ] Non-allowlisted user in DM is blocked (no workflow execution / unauthorized behavior as configured).
- [ ] Channel behavior respects policy (`mention` mode requires @mention).

Test messages:

1. Allowlisted user sends `mentor` in DM.
2. Non-allowlisted user sends `mentor` in DM.
3. In channel: plain `mentor` (no @mention).
4. In channel: `@BotName mentor`.

---

## C) Command Routing Validation

- [ ] `mentor` routes correctly.
- [ ] `domcobb` routes correctly.
- [ ] `doc` routes correctly.
- [ ] Unsupported token returns safe/explicit unsupported-command behavior.

Suggested sequence:

1. `mentor`
2. `domcobb`
3. `doc`
4. `unknown-command`

---

## D) Project-Memo Continuity Validation

- [ ] `project-memo.md` remains readable after interactions.
- [ ] Frontmatter still contains canonical keys:
  - `projectName`
  - `currentMilestone`
  - `currentFramework`
  - `stepsCompleted`
- [ ] No frontmatter corruption after command switching.

Check:

```bash
ls -la /opt/robotville/BMAD/_bmad/rbtv/_admin/docs/mobile/robotville-v4.0-business-innovation-run/founder/project-memo.md
# Note: project-memo path is project-specific — adjust to actual project output location
```

Then open and inspect frontmatter integrity.

---

## E) FR25 Auto-Restart Validation

- [ ] Controlled kill of gateway process triggers automatic restart.
- [ ] Service returns to `active (running)` without manual restart.
- [ ] Logs show restart event and resumed stability.

Commands:

```bash
MAIN_PID="$(systemctl show -p MainPID --value nanobot-gateway)"
echo "Main PID: ${MAIN_PID}"
sudo kill -9 "${MAIN_PID}"
sleep 3
systemctl status nanobot-gateway --no-pager
journalctl -u nanobot-gateway -n 60 --no-pager
```

---

## F) Token Budget & Optimization Validation

- [ ] `config.json` shows `memory_window: 20`.
- [ ] Multi-turn conversation (e.g., `mentor` → `N` → follow-up) completes without `litellm.RateLimitError`.

Commands:

```bash
# Verify config
sudo -u nanobot python3 -c "
import json; c = json.load(open('/srv/nanobot/.nanobot/config.json'))
d = c.get('agents',{}).get('defaults',{})
print(f\"memory_window: {d.get('memory_window')}\")
"
```

> **Note:** Prompt caching and retry logic are native to Nanobot (no source patches needed). If rate limit errors occur, set `LITELLM_NUM_RETRIES` in the env file.

---

## G) Final Pass/Fail Decision

- [ ] PASS - all critical checks passed.
- [ ] FAIL - at least one critical check failed.

If FAIL:

1. Capture failing step and evidence.
2. Apply fix.
3. Re-run only affected section(s), then final pass.

---

## Result Summary Template

- Date/Time (UTC):
- Operator:
- Environment (server/IP):
- Overall result (PASS/FAIL):
- Failed checks (if any):
- Follow-up actions:

---

## Change Log

| Date | Change | By |
|---|---|---|
| 2026-02-14 | Initial smoke checklist created for p4-2 | AI |
| 2026-02-14 | Added canonical workspace path verification to baseline checks | AI |
| 2026-02-14 | Added private GitHub fetch verification for deploy-key flow | AI |
| 2026-02-14 | Added VPS pull/reinstall automation script verification | AI |

