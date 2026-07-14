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
  updated_at   TEXT NOT NULL
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
  status       TEXT NOT NULL DEFAULT 'launching'
               CHECK (status IN ('launching','running','done','blocked','failed','stalled','killed')),
  session_id   TEXT,
  pid          INTEGER,
  exit_code    INTEGER,
  thread       TEXT NOT NULL,
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
