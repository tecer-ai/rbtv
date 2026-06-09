---
name: google-tools
description: Access Gmail, Google Calendar, and Google Drive via Python scripts. Read emails, search messages, manage calendar events, and interact with Drive files across multiple Google accounts (pessoal, tecer). Use when the user asks to check email, read messages, look at calendar, manage events, search Drive, or any Google Workspace interaction.
---

# Google Tools

Python scripts at `3-resources/tools/google/scripts/` for Gmail, Calendar, and Drive API access.

## Execution

All scripts MUST be run using the venv Python:

```bash
"3-resources/tools/google/.venv/Scripts/python.exe" "3-resources/tools/google/scripts/{script}.py" --account {account} [args]
```

**Accounts:** `pessoal` (personal Gmail), `tecer` (work)

All scripts support `--json` flag for structured output. Prefer `--json` when parsing results programmatically.

## Gmail

### gmail_read.py — Search and read emails

| Arg | Required | Description |
|-----|----------|-------------|
| `--account` | yes | Account name |
| `--query, -q` | no | Gmail search query (same syntax as Gmail search bar) |
| `--message-id` | no | Read specific message by ID |
| `--thread-id` | no | Read all messages in a thread |
| `--max-results` | no | Max results (default: 10) |
| `--json` | no | JSON output |

```bash
# Unread emails
--account pessoal --query "is:unread" --max-results 20

# From specific sender
--account tecer --query "from:someone@example.com"

# Date range
--account tecer --query "after:2026/03/01 before:2026/03/25 from:bhub"

# Read specific message
--account pessoal --message-id 19d08ad50fd8d1e3

# Read full thread
--account tecer --thread-id 19d08ad50fd8d1e3
```

### gmail_download.py — Download attachments

| Arg | Required | Description |
|-----|----------|-------------|
| `--account` | yes | Account name |
| `--message-id` | no | Message ID(s) to download from (direct mode) |
| `--hours` | no | Look-back window in hours (default: 24, search mode) |
| `--output` | yes | Output folder |
| `--sender` | no | Filter by sender (search mode) |
| `--dry-run` | no | List without downloading |

### gmail_draft.py — Create drafts (new or reply)

| Arg | Required | Description |
|-----|----------|-------------|
| `--account` | yes | Account name |
| `--to` | yes | Recipient(s), comma-separated |
| `--cc` | no | CC recipients |
| `--bcc` | no | BCC recipients |
| `--subject` | for new | Subject line |
| `--body` | no | Message body text |
| `--body-file` | no | Read body from file |
| `--thread-id` | for reply | Thread ID to reply in |
| `--reply-to-message-id` | for reply | Message ID to reply to |
| `--attach` | no | File path(s) to attach |
| `--dry-run` | no | Preview without creating |

### gmail_send.py — Send existing draft

| Arg | Required | Description |
|-----|----------|-------------|
| `--account` | yes | Account name |
| `--draft-id` | yes | Draft ID to send |
| `--dry-run` | no | Preview without sending |

**Workflow:** ALWAYS create draft first (`gmail_draft.py`), show to user, then send (`gmail_send.py`) only after explicit confirmation.

### gmail_label.py — Manage labels

| Arg | Required | Description |
|-----|----------|-------------|
| `--account` | yes | Account name |
| `--message-id` | no | Message to modify |
| `--add` | no | Label to add (repeatable) |
| `--remove` | no | Label to remove (repeatable) |
| `--list` | no | List all labels |
| `--json` | no | JSON output |

## Calendar

### calendar_read.py — List and search events

| Arg | Required | Description |
|-----|----------|-------------|
| `--account` | yes | Account name |
| `--today` | no | Show today's events |
| `--start` | no | Start date (YYYY-MM-DD) |
| `--end` | no | End date (YYYY-MM-DD) |
| `--days` | no | Days ahead (default: 7) |
| `--query, -q` | no | Search text |
| `--calendar-id` | no | Calendar ID (default: primary) |
| `--list-calendars` | no | List all calendars |
| `--max-results` | no | Max events (default: 50) |
| `--json` | no | JSON output |

```bash
# Today's events
--account pessoal --today

# This week
--account tecer --start 2026-03-30 --end 2026-04-05

# Search
--account pessoal --query "dentist"

# List all calendars
--account tecer --list-calendars
```

### calendar_write.py — Create, update, delete events

Global args: `--account`, `--calendar-id`, `--timezone` (default: America/Sao_Paulo), `--dry-run`, `--json`

**create:**

| Arg | Required | Description |
|-----|----------|-------------|
| `--summary` | yes | Event title |
| `--start` | yes | Start (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD) |
| `--end` | yes | End |
| `--all-day` | no | All-day event flag |
| `--location` | no | Location |
| `--description` | no | Description |
| `--attendees` | no | Comma-separated emails |

**update:** `--event-id` (required) + any of: `--summary`, `--start`, `--end`, `--location`, `--description`

**delete:** `--event-id` (required)

## Drive

### drive_read.py — List, search, download files

**list:** `--folder-id` (optional), `--max-results` (default: 50)
**search:** `--query, -q` (required), `--max-results`
**download:** `--file-id` (required), `--output` (required)
**list-drives:** no extra args

```bash
# Search files
--account tecer search --query "invoice"

# Download
--account pessoal download --file-id 1ABC123 --output /tmp/file.pdf
```

### drive_write.py — Upload, organize files

Global: `--account`, `--dry-run`, `--json`

**upload:** `--file` (required), `--folder-id`, `--mime-type`
**create-folder:** `--name` (required), `--parent-id`
**move:** `--file-id` (required), `--to-folder-id` (required)
**trash:** `--file-id` (required)

## Common Gmail Search Queries

| Query | Purpose |
|-------|---------|
| `is:unread` | Unread messages |
| `is:starred` | Starred messages |
| `from:email@example.com` | From specific sender |
| `to:email@example.com` | Sent to specific address |
| `subject:keyword` | Subject contains keyword |
| `has:attachment` | Messages with attachments |
| `after:YYYY/MM/DD before:YYYY/MM/DD` | Date range |
| `label:LABEL` | Messages with label |
| `in:sent` | Sent messages |
| `newer_than:7d` | Last 7 days |
