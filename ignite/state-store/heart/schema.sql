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
  -- Both NULL = UNHOMED. Firing an unhomed launch-agent is a refusal: the flat
  -- `.rbtv/sessions/<exec-id>/` path is retired and every daemon spawn homes as a seat
  -- (`r-seats-only-architecture`, completing `r-711-staged-retirement` / G-122).
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
  -- Task 7.389 (G-leader-0805-0625) — the enqueuing SEAT, the column G-137 named as its own
  -- precondition (b). `enqueued_by` is a SENDER-ID (a device/bridge identity); this is a SEAT
  -- address, written only when the ingress PROVED one (CMP-13 `attachProvenSeat`). NULLABLE by
  -- construction and not a defect: a remote sender, a bridge, and every row written before this
  -- column existed hold no seat, and a NULL here must never read as "some seat" — the
  -- `creator-seat` grant in internal-api/authz.js refuses NULL on both sides for exactly that
  -- reason. No default: absence is the honest value.
  enqueuing_seat TEXT,
  enqueued_at  TEXT NOT NULL,
  CHECK ((trigger_kind = 'periodic') = (interval_seconds IS NOT NULL)),
  CHECK (trigger_kind = 'scheduled' OR repeat_rule IS NULL),
  CHECK (max_fires IS NULL OR trigger_kind = 'periodic' OR repeat_rule IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_queue_due ON queue(run_at);

CREATE TABLE IF NOT EXISTS messages (
  msg_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  -- W4 closed the vocabulary at SEVEN; D2's routed types (owner ruling, 2026-08-19) make it EIGHT
  -- with `stuck`. Unlike jobs_log.status below, this CHECK IS moved on migrated stores too
  -- (migration 5 `message-types-seven-w4`, then migration 7 `message-types-eight-stuck`) — a table
  -- rebuild each time, because SQLite cannot alter a CHECK. Fresh and migrated therefore enforce
  -- the SAME constraint, which is the property the jobs_log note below could not buy and had to
  -- reason around.
  type         TEXT NOT NULL CHECK (type IN ('completion','ask','answer','verdict','note','queue-request','escalation','stuck')),
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
  -- Task 7.389 — the enqueuing SEAT, denormalized at fire from `queue.enqueuing_seat` exactly as
  -- `enqueued_by` is (heart-store.js § fireQueueRow). Nullable for the same reasons stated on the
  -- queue column; `canKillSession` reads it through the same resolver `canRemoveQueueRow` does.
  enqueuing_seat TEXT,
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
  -- 7.787 (`#d-abolish-profile-names`): UNCHANGED COLUMN, NEW CONTENT, NO MIGRATION.
  -- It records WHICH LAUNCH SPEC actually ran, written from the RESOLVED value at spawn and never
  -- from a request (the caller no longer has one to make). Since 2026-08-12 that value is the
  -- launch-spec KEY `<harness>/<model>` (`claude/claude-opus-5`); rows written before it hold the
  -- retired profile NAME (`claude-opus`). Neither form is ever re-read as a launch instruction —
  -- this is an audit column — so the two coexisting cost nothing and a rewrite of history would
  -- have been a fabrication. Its ONE parser (`bridges/chat/reply-leg.js#normalizeLog`) takes the
  -- first `/` segment as the harness and degrades a legacy row to its plain-text arm.
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
-- (job_id, fired_at) serves the two per-cadence lookups that otherwise SCAN the whole table per
-- probe row: listEnqueueUnfired's correlated NOT EXISTS (measured 1.5 s PER GOAL PER CADENCE at
-- 31k rows on 2026-08-21 — half the event-loop stall that took the gateway down) and
-- consecutiveFailures' newest-first walk. schema.sql runs at every boot, so an existing store
-- gains it on the next restart.
CREATE INDEX IF NOT EXISTS idx_jobslog_jobid_firedat ON jobs_log(job_id, fired_at);

-- enqueue_log — the enqueue→launch record (enqueue-record, 2026-08-19). jobs_log is fired
-- executions only; a suppressed or not-yet-fired enqueue has no row there. This sibling is
-- written inside heart-store.js#enqueue() for both outcomes so every caller is recorded.
-- ponytail: the table is never pruned. Upgrade path if it ever matters: delete rows older
-- than N days in the same pass. Do not build the pruner.
CREATE TABLE IF NOT EXISTS enqueue_log (
  enq_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id      TEXT NOT NULL,
  goal        TEXT,
  seat        TEXT,
  seat_key    TEXT,
  -- D52/D66 (2026-08-22) — 'braked' is the admission-brake door's own refusal outcome, recorded
  -- for the SAME reason 'suppressed' is: every enqueue() caller is recorded, and a refusal that
  -- left no trace is indistinguishable from a caller that never tried (heart-store.js § enqueue).
  outcome     TEXT NOT NULL CHECK (outcome IN ('enqueued','suppressed','braked')),
  because     TEXT,
  queue_id    INTEGER,
  exec_id     INTEGER,
  held_status TEXT,
  at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_enqueue_log_goal_at ON enqueue_log(goal, at);

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

-- reconcile_attempts — durable 3-strike counts for the goal watcher (D15, 2026-08-19).
-- Keyed on (goal, seat, reason), never a session id. A daemon restart must not reset the
-- bound: the measured freeze survived one. stuck_emitted suppresses repeat `stuck` rows
-- while the signature stands; a changed or cleared signature starts from zero.
CREATE TABLE IF NOT EXISTS reconcile_attempts (
  goal          TEXT NOT NULL,
  seat          TEXT NOT NULL,
  reason        TEXT NOT NULL,
  attempts      INTEGER NOT NULL DEFAULT 0,
  stuck_emitted INTEGER NOT NULL DEFAULT 0 CHECK (stuck_emitted IN (0,1)),
  signature     TEXT,
  updated_at    TEXT NOT NULL,
  PRIMARY KEY (goal, seat, reason)
);

CREATE TABLE IF NOT EXISTS reconcile_pass (
  goal    TEXT PRIMARY KEY,
  last_at TEXT NOT NULL
);
