CREATE TABLE IF NOT EXISTS seat_endings (
  goal TEXT NOT NULL,
  seat TEXT NOT NULL,
  ending TEXT NOT NULL CHECK (ending IN ('done','incomplete','failed')),
  armed INTEGER CHECK (armed IS NULL OR armed IN (0,1)),
  reason_class TEXT,
  who_stamped TEXT NOT NULL CHECK (who_stamped IN ('seat','system')),
  evidence_pointer TEXT NOT NULL CHECK (evidence_pointer != ''),
  diagnostic TEXT NOT NULL DEFAULT '',
  named_event TEXT CHECK (
    named_event IS NULL OR named_event IN ('ask-answered','materialize-resolved','named-external-input')
  ),
  stamped_at TEXT NOT NULL,
  recovery_relaunch_count INTEGER NOT NULL DEFAULT 0 CHECK (recovery_relaunch_count >= 0),
  failure_strike_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_strike_count >= 0),
  leader_attempt_used INTEGER NOT NULL DEFAULT 0 CHECK (leader_attempt_used IN (0,1)),
  PRIMARY KEY (goal, seat),
  CHECK (
    ending != 'failed' OR (
      who_stamped = 'system'
      AND reason_class IN (
        'provider-error','configuration-error','crash','killed-no-progress',
        'outputs-missing','inputs-missing','launch-refused'
      )
      AND armed IS NULL
    )
  ),
  CHECK (ending != 'incomplete' OR (armed IN (0,1) AND reason_class IS NULL)),
  CHECK (NOT (ending = 'incomplete' AND armed = 0) OR (named_event IS NOT NULL AND named_event != '')),
  CHECK (NOT (ending = 'incomplete' AND armed = 1) OR named_event IS NULL),
  CHECK (ending != 'done' OR (armed IS NULL AND reason_class IS NULL AND who_stamped = 'seat'))
);
CREATE INDEX IF NOT EXISTS idx_seat_endings_goal ON seat_endings(goal);

CREATE TABLE IF NOT EXISTS seat_endings_log (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  goal TEXT NOT NULL,
  seat TEXT NOT NULL,
  ending TEXT NOT NULL,
  armed INTEGER,
  reason_class TEXT,
  who_stamped TEXT NOT NULL,
  evidence_pointer TEXT NOT NULL,
  diagnostic TEXT NOT NULL DEFAULT '',
  named_event TEXT,
  stamped_at TEXT NOT NULL,
  recovery_relaunch_count INTEGER NOT NULL DEFAULT 0,
  failure_strike_count INTEGER NOT NULL DEFAULT 0,
  leader_attempt_used INTEGER NOT NULL DEFAULT 0,
  superseded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_seat_endings_log_goal_seat ON seat_endings_log(goal, seat);

CREATE TABLE IF NOT EXISTS goal_states (
  goal TEXT PRIMARY KEY,
  stored TEXT NOT NULL CHECK (stored IN ('running','paused','finished')),
  who_stamped TEXT NOT NULL CHECK (who_stamped IN ('owner','system')),
  evidence_pointer TEXT NOT NULL CHECK (evidence_pointer != ''),
  stamped_at TEXT NOT NULL,
  CHECK (stored != 'paused' OR who_stamped = 'owner'),
  CHECK (stored != 'finished' OR who_stamped = 'system')
);

CREATE TABLE IF NOT EXISTS open_asks (
  ask_id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  seat TEXT NOT NULL,
  label TEXT NOT NULL CHECK (label IN ('work-content','recovery')),
  state TEXT NOT NULL CHECK (state IN ('open','answered','closed')),
  posted INTEGER NOT NULL CHECK (posted IN (0,1)),
  posted_at TEXT,
  authorized_reply_at TEXT,
  evidence_pointer TEXT NOT NULL CHECK (evidence_pointer != '')
);
CREATE INDEX IF NOT EXISTS idx_open_asks_goal_state ON open_asks(goal, state);
CREATE INDEX IF NOT EXISTS idx_open_asks_seat ON open_asks(goal, seat);
