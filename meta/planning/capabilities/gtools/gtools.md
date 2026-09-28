---
description: "Use for the owner's Google Workspace requests: search or read Gmail, draft or send mail, check or change Calendar events, find or move Drive files, and retrieve Meet records or transcripts through gtools."
exposes-cli:
  - gtools
---

# gtools

`gtools` is the workspace's Google mail, calendar, Drive, and Meet CLI. Run `gtools accounts` to identify the requested account, then `gtools <service> <verb> --help` for the exact flags. Every service command needs `--account`; never guess an account or flag.

| Request | Command family |
|---|---|
| Search or read mail; download or export it | `gtools gmail read|download|export` |
| Draft or send mail; change labels | `gtools gmail draft|send|label` |
| Check or change calendar events | `gtools cal read|create|create-batch|update|delete` |
| Find, download, upload, organize, or trash Drive files | `gtools drive list|search|download|list-drives|upload|create-folder|move|trash` |
| Find or download Meet records or transcripts | `gtools meet records|transcripts|download` |
| Inspect setup or token state | `gtools doctor` or `gtools auth --status` |

Confirm the recipient, destination, or event identity from the request before a write. Read the command's result before reporting completion.
