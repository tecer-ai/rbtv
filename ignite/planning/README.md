# `ignite/planning/` — planning-door lock + supervised-materialize wrapper

Replacement splice door (spec-planning-door §1–§4). Path A (this seat) is the goal-wide planning-seat mint. Path B (birth) reuses argv + wrapper. Does not Slack-post. Does not touch `materialize-seats.py` KEEP bodies.

| Module | Responsibility |
|---|---|
| `lock.py` | `<goal>/planning/current/.materialize.lock` — exclusive flock, same inode, holder pid + planning-pass id |
| `wrapper.py` | `supervised_materialize` — validate → uncast → (B) scaffold → lock → mint → release |
| `argv.py` | Path A argv builder — one `--workflow` invocation, no `--milestone-id`, no `--nested` |
| `path_a.py` | Path A mint through the wrapper |
| `door.js` | Goal-wide trigger the daemon tick calls |
| `failure.py` | six-field failure record + origin routing + gate-lane stamp |

`GOAL_LOCAL_SOURCE` stays `("planning", "current")`. A planning goal is a `goal.md` whose frontmatter carries `role: planning`. Minted = the five seats in `pipeline-seats.json` are rows on that goal's `taskforce.csv`.
