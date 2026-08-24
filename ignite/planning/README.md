# `ignite/planning/` — planning-door lock + supervised-materialize wrapper

Replacement splice door foundations (spec-planning-door §3–§4). Callers only: `impl-planning-door-mint` (path A) and `impl-planning-door-birth` (path B). Does not Slack-post. Does not touch `materialize-seats.py` KEEP bodies.

| Module | Responsibility |
|---|---|
| `lock.py` | `<goal>/planning/current/.materialize.lock` — exclusive flock, same inode, holder pid + planning-pass id |
| `wrapper.py` | `supervised_materialize` — validate → (B) scaffold → lock → mint → release |
| `failure.py` | six-field failure record + origin routing + gate-lane stamp |

`GOAL_LOCAL_SOURCE` stays `("planning", "current")`.
