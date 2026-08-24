---
description: Use when minting planning seats or birthing an execution goal through the supervised materialize door.
---

# planning

The planning-door lock and supervised-materialize wrapper. Not a CLI — later seats import `lock.py`, `wrapper.py`, and `failure.py` from this folder.

| Part | One line |
|---|---|
| `lock.py` `take_lock` | Exclusive flock on `<goal>/planning/current/.materialize.lock`; same pass-id re-enters; distinct trigger refuses `lock-collision`; dead pid is stolen |
| `wrapper.py` `supervised_materialize` | Shared path-A/path-B wrapper: validate → scaffold (B) → lock → mint → release; five failure classes; no Slack |
| `failure.py` | Record fields `origin`/`origin-id`/`class`/`code`/`subject`/`reason`; D12 approval-thread; D13 gate-lane `incomplete: materialize-failed` |
