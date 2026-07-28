PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS jobs (
  job_id       TEXT PRIMARY KEY,
  action_type  TEXT NOT NULL
               CHECK (action_type IN ('launch-agent','fire-tool','start-workflow','send-message')),
  function     TEXT NOT NULL,
  args_schema  TEXT NOT NULL DEFAULT '{}',
  description  TEXT,
  enabled      INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  -- task 7.12 · the job->seat pointer (owner ruling `r-job-seat-home`, 2026-07-27).
  -- A job is only the TRIGGER; its action is always homed as a SEAT in a goal. The pointer names
  -- the goal and the seat and DELIBERATELY NOT THE RUN: goal-serving jobs are seats of the goal's
  -- LIVE run and retire with it, so the run is resolved at FIRE time. Storing it would pin the
  -- pointer to a run that later closes.
  -- Both NULL = the interim `.rbtv/sessions/<exec-id>/` path, which is still what the ticker
  -- branch uses for an unhomed job (the staged retirement of `r-711-staged-retirement` / G-122).
  goal_name    TEXT,
  seat_name    TEXT,
  -- Both or neither. A half-pointer resolves to nothing and would fail at fire time — the one
  -- moment there is no operator watching — so it is refused at rest instead.
  CHECK ((goal_name IS NULL) = (seat_name IS NULL))
);

CREATE TABLE IF NOT EXISTS queue (
  queue_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id       TEXT NOT NULL REFERENCES jobs(job_id),
  args         TEXT NOT NULL DEFAULT '{}',
  session_mode TEXT NOT NULL DEFAULT 'headless' CHECK (session_mode IN ('headless','headed')),
  trigger_kind TEXT NOT NULL CHECK (trigger_kind IN ('scheduled','periodic')),
  run_at       TEXT NOT NULL,
  repeat_rule  TEXT,
  interval_seconds INTEGER CHECK (interval_seconds IS NULL OR interval_seconds > 0),
  max_fires    INTEGER CHECK (max_fires IS NULL OR max_fires > 0),
  enqueued_by  TEXT NOT NULL,
  enqueued_at  TEXT NOT NULL,
  CHECK ((trigger_kind = 'periodic') = (interval_seconds IS NOT NULL)),
  CHECK (trigger_kind = 'scheduled' OR repeat_rule IS NULL),
  CHECK (max_fires IS NULL OR trigger_kind = 'periodic' OR repeat_rule IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_queue_due ON queue(run_at);

CREATE TABLE IF NOT EXISTS messages (
  msg_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  type         TEXT NOT NULL CHECK (type IN ('completion','ask','answer','verdict','note')),
  sender       TEXT NOT NULL,
  thread       TEXT NOT NULL,
  corpus       TEXT NOT NULL,
  status       TEXT,
  created_at   TEXT NOT NULL,
  routed_at_tick    INTEGER,
  broadcast_at_tick INTEGER,
  CHECK ((type = 'completion') = (status IS NOT NULL)),
  CHECK (status IS NULL OR status IN ('done','blocked','failed'))
);
CREATE INDEX IF NOT EXISTS idx_messages_unrouted    ON messages(msg_id) WHERE routed_at_tick IS NULL;
CREATE INDEX IF NOT EXISTS idx_messages_unbroadcast ON messages(msg_id) WHERE broadcast_at_tick IS NULL;
-- Task 7.19: backs the ticker's bounded Advance fetch (unrouted COMPLETIONS
-- only) — per-tick scan work tracks in-flight completions, never the
-- accumulated unrouted-note history.
CREATE INDEX IF NOT EXISTS idx_messages_unrouted_completion
  ON messages(msg_id) WHERE routed_at_tick IS NULL AND type = 'completion';

-- Task 7.46 — SESSION and TURN are two levels, and this table is the SESSION one.
--
-- Before it existed, a `jobs_log` row was rigidly BOTH: one spawned process AND one unit of work,
-- 1:1, always. That conflation is what made session liveness (is the process there?) an answer
-- read out of turn status (did the work report?) — the ticker's crash sweep, stall ladder and
-- agent cap all asked a session question of a turn column. The registry settled the two terms
-- (`concepts/session.md`, `concepts/turn.md`, R16); this is the store learning to speak them.
--
-- A SECOND TABLE rather than a `level` column on `jobs_log`: a polymorphic `status` would make
-- every existing `status = 'done'` filter silently span both levels unless someone remembered a
-- `level` predicate, and a forgotten filter returns a WRONG ANSWER instead of an error. Here a
-- forgotten join is a SQL error. (The third candidate — deriving session state from turn rows —
-- cannot represent idle-alive-between-turns at all, which is the entire content of R16.)
--
-- The 1:1 degeneracy stays TRUE of every session the daemon spawns today: a headless one-shot is a
-- session with exactly one turn. This does not make a process outlive its turn (that is the tmux
-- path, 7.30/7.32) — it makes the store able to REPRESENT one that does.
CREATE TABLE IF NOT EXISTS sessions (
  session_pk    INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    TEXT,
  status        TEXT NOT NULL DEFAULT 'alive'
                CHECK (status IN ('alive','closed','killed','crashed')),
  session_mode  TEXT NOT NULL DEFAULT 'headless' CHECK (session_mode IN ('headless','headed')),
  opened_at     TEXT NOT NULL,
  closed_at     TEXT,
  close_reason  TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

CREATE TABLE IF NOT EXISTS jobs_log (
  exec_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_exec_id INTEGER REFERENCES jobs_log(exec_id),
  queue_id     INTEGER,
  job_id       TEXT NOT NULL,
  action_type  TEXT NOT NULL,
  args         TEXT NOT NULL,
  enqueued_by  TEXT NOT NULL,
  session_mode TEXT NOT NULL DEFAULT 'headless' CHECK (session_mode IN ('headless','headed')),
  fired_tick   INTEGER NOT NULL,
  fired_at     TEXT NOT NULL,
  -- Task 7.46: a jobs_log row is a TURN. `status` is the TURN's state; the SESSION's state lives
  -- on sessions.status and is never derived from this column.
  --
  -- ⚠ The CHECK deliberately keeps the legacy 7-value superset, INCLUDING the session-level
  -- `killed`, and it is IDENTICAL on fresh and migrated stores. Two measured reasons:
  --   1. SQLite can only change a CHECK by REBUILDING the table, whose documented procedure needs
  --      `PRAGMA foreign_keys=OFF` — but heart-store.js sets it ON, `parent_exec_id` is a
  --      self-reference, and the pragma is a NO-OP inside the transaction migrate() always opens.
  --      A rebuild would fail at the one restart the owner performs, carrying other work with it.
  --   2. Tightening it on fresh stores only would make fresh and migrated stores enforce DIFFERENT
  --      constraints — green on every fixture, divergent on the real store. That is G-135's exact
  --      shape reintroduced by the fix for it.
  -- The turn enum is enforced at the store API instead (heart-store.js § TURN_STATUSES), which
  -- refuses every session-level value. `killed` remains writable because the live kill path
  -- (spawn/spawn.js) writes it and dispatch.js reads it; that residual is filed, not hidden.
  status       TEXT NOT NULL DEFAULT 'launching'
               CHECK (status IN ('launching','running','done','blocked','failed','stalled','killed')),
  -- The turn's owning session. NULL only on rows written before 7.46 and not yet migrated.
  session_pk   INTEGER REFERENCES sessions(session_pk),
  session_id   TEXT,
  pid          INTEGER,
  exit_code    INTEGER,
  profile      TEXT,
  carrier      TEXT CHECK (carrier IS NULL OR carrier IN ('systemd','setsid')),
  unit_name    TEXT,
  pid_starttime INTEGER,
  session_ref  TEXT,
  workdir      TEXT,
  started_at   TEXT,
  completion_msg_id INTEGER REFERENCES messages(msg_id),
  log_path     TEXT,
  ended_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobslog_status ON jobs_log(status);

CREATE TABLE IF NOT EXISTS ticks (
  tick         INTEGER PRIMARY KEY,
  ts           TEXT NOT NULL,
  actions_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS warnings (
  warning_id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind                TEXT NOT NULL,
  subject             TEXT NOT NULL,
  raised_at_tick      INTEGER NOT NULL,
  last_announced_tick INTEGER,
  snoozed_until_tick  INTEGER,
  cleared_at_tick     INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_warnings_standing_kind_subject
  ON warnings(kind, subject) WHERE cleared_at_tick IS NULL;
