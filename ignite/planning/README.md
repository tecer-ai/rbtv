# `ignite/planning/` — planning-door lock + supervised-materialize wrapper

Replacement splice door (spec-planning-door §1–§4). Path A is the goal-wide planning-seat mint. Path B is execution-goal birth via `rbtv-goal scaffold` then Path-A-style mint. Does not Slack-post. Does not touch `materialize-seats.py` KEEP bodies.

| Module | Responsibility |
|---|---|
| `lock.py` | `<goal>/planning/current/.materialize.lock` — exclusive flock, same inode, holder pid + planning-pass id |
| `wrapper.py` | `supervised_materialize` — validate → uncast → (B) scaffold → lock → mint → release |
| `argv.py` | Path A argv builder — one `--workflow` invocation, no `--milestone-id`, no `--nested` |
| `path_a.py` | Path A mint through the wrapper |
| `path_b.py` | Path B: approve-package → validate → scaffold → mint; reclaim on half-goal |

WHO CALLS PATH B. The approval thread's `approve` (D12). It crosses the daemon boundary as the fourteenth gateway intent `start-execution` (owner ruling 2026-08-24, option (b)); `server/heart/start-execution.js` validates the approval binding, stamps the package fields the daemon owns (`planning_goal`, `goals_root`, `origin_id` = the approval thread) and runs `path_b.py --package`. The planning goal's own `planning/approve-package.json` is the plan it reads — a birth with a guessed package is a birth of something nobody read.
| `door.js` | Goal-wide trigger the daemon tick calls |
| `failure.py` | six-field failure record + origin routing + gate-lane stamp |

`GOAL_LOCAL_SOURCE` stays `("planning", "current")`. A planning goal is a `goal.md` whose frontmatter carries `role: planning`. Minted = the five seats in `pipeline-seats.json` are rows on that goal's `taskforce.csv`. That json is a MIRROR, not a source: the seat ids belong to the workflow manifest `meta/planning/workflows/plan-console/plan-console.csv` (`Seat/workflow` column), which is what the mint writes onto `taskforce.csv`. If the two diverge, every planning goal reads unminted and the door re-mints every cadence forever — leg M of `engine/probes/probe-queue-request-pass.js` is the alarm.
