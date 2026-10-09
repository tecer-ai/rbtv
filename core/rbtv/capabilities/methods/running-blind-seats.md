# Running blind seats

The result: for one task, the count of headless seats that selected a skill, opened a page or wrote a block, out of the seats run, with what each seat did first. The caller's page states which observation counts and the passing rate; this page states how the seats are run and read.

Inputs: the task file, written as a user would write it and naming no skill or page; the installation whose installed files the seats must see; the harness and model, the weakest the installation selected (`cast models list`); the count of seats (ten per task unless the caller states another); the time limit, about two minutes; and, when the task touches files, a fixture folder holding them. When the task names no fixture and touches files, write one before launching: a seat given a real repository acts on it.

## Launch

1. Make one folder per seat inside the installation, so that the harness lists the installed skills and rules from the folder's ancestors, and copy the fixture into each. Write the task's file paths relative to that folder.
2. Launch each seat with `cast HARNESS MODEL EFFORT <seat folder> -f <task file>`, all seats at once, each launch as a background job the harness keeps tracked and each launch's output kept in a file of its own; `cast` refuses a launch detached from its caller (`&`, `nohup` or `setsid` in a command that returns before the seat ends). When the operator's shell runs inside tmux, launch with the `TMUX` variable unset, so that a seat cannot act on the operator's session.
3. `cast` prints one line `cast: handle {…}` on standard error for each launch: `pid` is the seat's process, `folder` its launch folder and, for Claude Code, `transcript` the path of the session record. Keep that line.
4. After the time limit, end each seat whose `pid` is still alive (terminate, then kill); a seat that ended on its own needs nothing. Record which seats were stopped: a stopped seat may have been about to act.

## Read each seat

Read the seat's transcript, not its final message: the message reports what the seat says it did. A Claude Code transcript is a `.jsonl` file; each line is a record, and a record whose `type` is `assistant` carries `message.content`, a list of parts; a part whose `type` is `tool_use` is one tool call, with `name` and `input`. Collect the calls in order:

| Call | What to record |
|---|---|
| `Skill` | `input.skill`: a skill opened |
| `Read` | `input.file_path`: a page or file read |
| `Edit`, `Write` | `input.file_path`: an edit |
| `Bash` | `input.command`: a command run |

From that list, for each seat: the skills opened, in order; the pages read under the repository's `capabilities/`; the first call; whether the named skill was opened before the first edit; and, where the caller looks for a block, whether the block's tag appears in a text part of an assistant record before the first edit. A seat with no transcript, or one on a harness whose record this page does not describe, is reported as unread, not as a miss; the record formats of Codex and OpenCode are not described here.

## Report

One line per seat with those observations, then the tally: the count that met the caller's observation, the count that opened no skill, the count stopped at the limit, the count unread, each out of the seats run. Keep the transcripts and the seat folders as the evidence. Then check the installation for anything a seat changed outside its folder (`git status`), and restore it before the next run.

A miss is read before the description or page is changed: what the seat did first says what the listing made it believe. A change is then tested with a fresh set of seats, never by rereading the ones that missed.
