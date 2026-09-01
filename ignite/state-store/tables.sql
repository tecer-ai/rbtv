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

-- `closed` (d-goal-closed-word, 2026-09-01, `redesign-continue-1`) — a FOURTH terminal word,
-- owner-stamped like `paused`, for a goal the owner gave up on via the close-or-keep ask
-- (`d-recovery-last-lane-asks`). Widening this CHECK in source is a no-op on an EXISTING
-- `heart.db` — `open.js` runs this file as `CREATE TABLE IF NOT EXISTS`, so a live workspace's
-- CHECK constraint stays exactly what it was created with. `state-store/open.js#migrateGoalStatesClosed`
-- is the non-destructive rebuild that brings an existing store forward (rename-out, create-fresh
-- with this exact shape, copy rows, drop the old table — SQLite cannot ALTER a CHECK).
CREATE TABLE IF NOT EXISTS goal_states (
  goal TEXT PRIMARY KEY,
  stored TEXT NOT NULL CHECK (stored IN ('running','paused','finished','closed')),
  who_stamped TEXT NOT NULL CHECK (who_stamped IN ('owner','system')),
  evidence_pointer TEXT NOT NULL CHECK (evidence_pointer != ''),
  stamped_at TEXT NOT NULL,
  CHECK (stored != 'paused' OR who_stamped = 'owner'),
  CHECK (stored != 'finished' OR who_stamped = 'system'),
  CHECK (stored != 'closed' OR who_stamped = 'owner')
);

-- `kind`/`subject`/`options_json` (`d-owner-ask-shape`, 2026-09-01, `redesign-continue-1`) — the
-- ask's kind (`recovery`/`goal-disposition`/…), the composer's plain-sentence subject (R-A3's
-- reserved first line), and its lettered options table (R-A5, JSON, `[{letter,arm,text,…}]`). ADDED
-- via plain `ALTER TABLE … ADD COLUMN` (`state-store/open.js#migrateOpenAsksShape`) — no CHECK on
-- any of the three, so (unlike `goal_states.stored` gaining `closed`) the rename-rebuild dance
-- `migrateGoalStatesClosed` needed does not apply here: SQLite adds a plain column in place. All
-- three default to '' — the empty value a pre-existing row reads as, and what every caller writes
-- today (the crossing that would fill them on a live post is outside this file's custody; see
-- `state-store/heart/ask-record.js#openAsk`'s own header).
CREATE TABLE IF NOT EXISTS open_asks (
  ask_id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  seat TEXT NOT NULL,
  label TEXT NOT NULL CHECK (label IN ('work-content','recovery')),
  state TEXT NOT NULL CHECK (state IN ('open','answered','closed')),
  posted INTEGER NOT NULL CHECK (posted IN (0,1)),
  posted_at TEXT,
  authorized_reply_at TEXT,
  evidence_pointer TEXT NOT NULL CHECK (evidence_pointer != ''),
  kind TEXT NOT NULL DEFAULT '',
  subject TEXT NOT NULL DEFAULT '',
  options_json TEXT NOT NULL DEFAULT ''
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

-- ── ABANDONMENT — a lane's second terminal outcome, and deliberately NOT a value on `ending` ─────
--
-- WHAT IT IS. `drop-lane` (a recovery reply the owner can send on a stuck lane,
-- `d-recovery-drop-is-one-lane-permanent`) retires ONE lane — the `(goal, seat)` pair — forever,
-- with no undo. `d-recovery-abandoned-is-an-ending` puts the record where a lane's normal
-- completion is already recorded: beside `done`, as a second terminal outcome, so the checks that
-- already ask "does this lane have an outcome?" inherit the answer without new machinery.
--
-- WHY A SIBLING TABLE AND NOT A THIRD/FOURTH VALUE ON `seat_endings.ending`. The ruling's own words
-- put abandonment "where completion is already recorded" — that reads as `seat_endings`, but two
-- facts rule it out, both measured against the LIVE store rather than assumed:
-- (1) `seat_endings.ending`'s CHECK clause is `IN ('done','incomplete','failed')` and `open.js` runs
-- `tables.sql` with `CREATE TABLE IF NOT EXISTS` — a no-op on a table that already exists. Widening
-- the CHECK in this file changes nothing on a live `heart.db`; a live workspace's CHECK constraint
-- stays exactly what it was `CREATE`d with, and stamping `ending='abandoned'` against it raises
-- `SQLITE_CONSTRAINT`. A sibling table is the one migration path this store has (declare it here,
-- new home creates it, existing home gains it, `seat_holds` is the precedent).
-- (2) Every re-stamp of `seat_endings` ARCHIVES the current row into `seat_endings_log` (`writers
-- .js#archiveCurrent`) — so an `ending` value could be superseded away by a later `done`/`failed`
-- stamp, and "abandoned forever" cannot live somewhere a later write erases it.
-- It IS in this file, and therefore in the ONE workspace-scoped ending store
-- (`<workspace>/.rbtv/runtime/ignite/heart.db`), for the same reason `seat_holds` is: the readers
-- that must inherit this answer (`owed.js`, `owed-from-endings.js`, and the reconcile/lane-watch
-- pass) already read this store.
--
-- NO RELEASE CONDITION, ON PURPOSE. Unlike `seat_holds.until`, there is no vocabulary of ways this
-- row stops applying — the ruling's whole point is that dropping a lane has NO undo path, from
-- Slack or from a terminal. The writer (`writers.js#abandonSeat`) never deletes or replaces a row
-- here; a second call on the same `(goal, seat)` returns the first row unchanged (idempotent on a
-- retried write, e.g. the drop's own two-step stop-then-mark sequence), never a second ruling.
CREATE TABLE IF NOT EXISTS seat_abandonments (
  goal TEXT NOT NULL,
  seat TEXT NOT NULL,
  -- Free text: why the lane was dropped, an owner-supplied reason or the recovery ask's comment.
  anchor TEXT NOT NULL CHECK (anchor != ''),
  abandoned_by TEXT NOT NULL CHECK (abandoned_by != ''),
  abandoned_at TEXT NOT NULL,
  -- The recovery ask this drop answered, when there was one — traceable, never verified.
  ask_id TEXT,
  PRIMARY KEY (goal, seat)
);
CREATE INDEX IF NOT EXISTS idx_seat_abandonments_goal ON seat_abandonments(goal);
