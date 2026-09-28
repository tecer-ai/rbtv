---
description: "Use for owner administration: inspect or switch AI provider accounts and usage, list or install rbtv components, run rbtv selftests, or view and update the rbtv control panel. Assigned to the master agent only."
exposes-cli:
  - core/providers/acct
  - meta/rbtv-cli/rbtv
  - meta/control-panel/rbtv-control-panel
---

# admin

This skill belongs to the master agent. Run the named command's `--help` before choosing flags.

| Request | Tool |
|---|---|
| Inspect provider accounts, usage, or login health; switch an account | `acct` — see `core/providers/capabilities/acct/acct.md` for account-slot behavior |
| List available or installed components; install, remove, or diagnose one | `rbtv install` — use `ls`, `li`, `add`, `rm`, or `doctor` as the request requires |
| Check rbtv mechanics | `rbtv selftest` or `rbtv install selftest` for the installer |
| Inspect or refresh the control panel | `rbtv-control-panel status|update|selftest` |

Use the tool's result to report what changed or what is installed.
