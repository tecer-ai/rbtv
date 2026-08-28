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

-- ── THE LEADER'S HOLD — a ruling ON a row, and deliberately NOT a column on it ─────────────────
--
-- WHAT IT IS. `supervise hold <seat> --until <change> --anchor <ref>` records that the leader has
-- RULED on a non-terminal row and that the row must not re-drive the lane until a NAMED change
-- happens. Before it, the leader's only two acts were `accept` and `instruct`; a deliberate
-- "hold, this is waiting on the owner" verdict existed only as a message, invisible to
-- `supervisor/owed-from-endings.js`, and so was indistinguishable from a sitting that did nothing
-- (nine identical HOLD verdicts on `goal-memory-management`, 2026-08-28, each one a paid sitting).
--
-- WHY A SIBLING TABLE AND NOT A COLUMN ON `seat_endings`. Three reasons, each fatal on its own.
-- (1) A `failed` row's CHECK clauses above pin it to `who_stamped = 'system'`, a `reason_class`
-- from the closed seven and `armed IS NULL` — a leader's ruling fits none of those slots.
-- (2) Every re-stamp of an ending ARCHIVES the current row into `seat_endings_log`, so a hold
-- carried on the ending would be superseded away by the very re-stamp it is waiting for.
-- (3) The hold's own lifetime is not the ending's: it survives a code-deploy re-arm (a hold is a
-- ruling, not a counter) and is released by a change the ending row cannot express.
-- It IS in this file, and therefore in the ONE workspace-scoped ending store
-- (`<workspace>/.rbtv/runtime/ignite/heart.db`, `state-store/open.js`), because the reader that
-- must honour it is the reconcile pass's ending read and a second store is the defect
-- `ending-reads.js`'s header exists to end.
--
-- ⚠ THIS IS NOT THE DELETED `hold-anchor`. That was a thirteenth COLUMN ON `sessions.csv`, part of
-- the grant-store authority model deleted whole [T2-R12, T1-R9]; `HELD` and `hold-anchor` are
-- refused words at this store's own door and neither is written here. The word that was killed was
-- a SECOND work-state writer beside the ending store. This is a row IN the ending store.
--
-- `until` is a CLOSED vocabulary (`vocabulary.js#HOLD_UNTIL`): `new-ending` (the held row is
-- re-stamped after the hold — witnessed by `ending_stamped_at` below), `ask-answered` (the named
-- `open_asks` row leaves `open`, the same mechanism §2.1 already watches), `release` (an explicit
-- `supervise release`). A fourth would be a release condition nobody ruled.
CREATE TABLE IF NOT EXISTS seat_holds (
  goal TEXT NOT NULL,
  seat TEXT NOT NULL,
  until TEXT NOT NULL CHECK (until IN ('new-ending','ask-answered','release')),
  ask_id TEXT,
  anchor TEXT NOT NULL CHECK (anchor != ''),
  held_by TEXT NOT NULL CHECK (held_by != ''),
  held_at TEXT NOT NULL,
  -- The `new-ending` witness: the `stamped_at` of the ending row this hold was placed over, or ''
  -- when there was none. The hold is live while the current ending still carries that same stamp.
  ending_stamped_at TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (goal, seat),
  CHECK (until != 'ask-answered' OR (ask_id IS NOT NULL AND ask_id != ''))
);
CREATE INDEX IF NOT EXISTS idx_seat_holds_goal ON seat_holds(goal);
