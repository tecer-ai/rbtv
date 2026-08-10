# probe-record — task `7.125` / `M4-10` (the edge-runner's enqueue of ready launches)

Every check invocation with its RED and GREEN output. Written by seat `edge-runner-enqueue-builder`,
2026-07-30. **Re-runnable by a reader who did not watch this seat work** — every command below is
complete as pasted, and nothing here is transcribed from memory.

---

## THE INTERFACE SIGNATURE — the part three later seats need

This is a DECLARED OUTPUT of the task, not documentation: `M4-11` (check-out fast path), `M4-20`
(the created goal's first workflow) and `M4-22` (the C1 rehearsal) all call this and none of them
writes its own enqueue. A signature that moves after they are built breaks them **silently**, so
`check_enqueue_signature_is_recorded` asserts, off disk, that the live signature equals the literal
below AND that this file carries it. The record going stale is therefore RED, not invisible.

```python
from edge_runner_job import enqueue        # 3-resources/tools/rbtv/ignite/jobs/edge-runner-job.py

enqueue(coord, pkg, job_id, profile, readiness_result=None, at=None, submit=None, dry_run=False)
```

| Parameter | Meaning |
|---|---|
| `coord` | the kit's `coord` module, from `load_coord()`. Its readers are CALLED, never reimplemented |
| `pkg` | `Path` to the run package |
| `job_id` | the REGISTERED catalogue job whose fire launches a seat. **No default** — the id belongs to whoever armed the queue (`M4-05`), never to this stage |
| `profile` | the launch profile name. **No default** — the daemon REQUIRES it of every `launch-agent` job (`heart-store.js` `REQUIRED_ARGS_BY_ACTION`), and this stage does not invent one |
| `readiness_result` | STEP 3's output. Omit and STEP 3 is run — the same code path, never a second reading of the trace |
| `at` | ISO-8601 UTC fire time; default is now, in the fixed-width shape the gateway's enqueue parse requires |
| `submit` | `(argv) -> (rc, stdout, stderr)`; defaults to running the daemon's own door. Inject it to exercise the interface without a daemon and without arming anything |
| `dry_run` | passes the door's validate-only flag. Rows land under `validated`, never `enqueued` |

Returns:

```
{enqueued:  [{seat, job-id, seed: [artifact-path]}],   # a row ONLY when the door named a real id
 validated: [{seat, job-id: None, seed}],              # dry_run — the door wrote nothing, so no id
 excluded:  [{seat, term, value, reason}],             # every ready seat the self-state intersection removed
 failed:    [{seat, missing-seed-paths, detail, reason}],
 caveats:   [...]}
```

The same signature is printed live by `python3 edge-runner-job.py --signature`, together with this
schema, so a consumer reads the truth from the code rather than from a file that could be stale.

**⚠ `excluded`, and NOT the word a reader reaches for first.** That other word is TAKEN: it is the
registry's name for a row excluded by a CONDITIONAL EDGE, and STEP 3's accepted
`check_no_conditional_evaluator_or_third_verdict` asserts that name occurs NOWHERE in this file's
source — because a state named but unreachable reads as *"this case did not arise"* when the truth
is *"this case cannot arise"*. A self-state exclusion and a conditional-edge exclusion are two
different claims. The `leader`'s bar (#269) is that every exclusion is NAMED and that the list is
present even when empty; both hold under this key, and the rename is reported in §8.

---

## What landed

| Artifact | Path |
|---|---|
| the stage (CMP-25 pass STEP 4) | `3-resources/tools/rbtv/ignite/jobs/edge-runner-job.py` — `enqueue()`, `launch_candidates()`, `seed_for()`, `_enqueue_argv()`, `resolve_declared_path()`, `_tried_paths()`, `iso_utc_now()`, `default_submitter()`, the two new `READS` rows, `--enqueue` / `--job-id` / `--profile` / `--at` / `--dry-run` / `--signature` |
| its 7 checks | the same file's `--selftest` (rows 14–20; the 13 inherited rows still green, 20/20 total) |
| this record | `runs/run-3/planning/m4-workflow-engine-runs-DAG-edged-jobs/probe-record-edge-runner-enqueue-builder.md` |

Post-change file: `sha256 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2`, 1748 lines, mode `0664`. **The mode is verified, not
assumed** (`ls -l`) — it is invisible to every check in the file, and it matches the five siblings
in `ignite/jobs/`, which are all `-rw-rw-r--` and are invoked as `python3 <script>`.

**C4 — this arms NOTHING, and the point is sharper here than for any earlier stage of this file
because this is the stage that would do the arming.** No enqueue was submitted to the live daemon.
The interface was driven end-to-end through an INJECTED submitter (`_stub_door`), which is why
`submit` is a parameter at all. Three independent facts back that:

1. This seat holds no gateway credential. `ignite inspect queue` from the vault root returns
   `ERROR [AUTH_REFUSED] authentication required`; the CLI takes its token from
   `IGNITE_SENDER_TOKEN` and nothing else (`cli/lib/config.js` `resolveToken`). The owner token is
   authorized for exactly two `register-job` calls and nothing else (`r-owner-token-reseed`).
2. The wave's permissions table gives `register-job` to `queue-rearmer` and the right to ENQUEUE to
   `first-workflow-enqueuer` / `both-goal-kinds-driver` / `c1-rehearsal-driver`. **Not to this
   seat.** Building the interface is this task; calling it against a real queue is theirs.
3. `coord.py` is **not modified** (`git status` in the rbtv repo shows it unmodified). The single
   pass this seat ran over the LIVE run-3 package was READ-ONLY and is shown in §7 with a
   before/after hash of every surface it touched.

**The honest form of the result: the interface is BUILT and PROVEN ON A FIXTURE. It is not
"live", and no job of this run's has been queued through it.**

---

## 1. Premise audit — every handed-down claim, confirmed on disk BEFORE anything was built

| Premise handed to this seat | Verdict | How |
|---|---|---|
| the predecessor's product is at `ignite/jobs/edge-runner-job.py`, `sha256 e6715db7b870a1…`, 1112 lines, mode `0664` | **CONFIRMED**, read FROM THE FILE, not from its check-out text | `sha256sum` + `wc -l` + `ls -l` |
| `7.125`'s manifest row: `after` = `7.124`, inputs = M4-09's `{ready: [seat]}` + each ready row's upstream declared outputs + the daemon's enqueue interface | **CONFIRMED** | row 12 of `manifest-m4.csv` |
| STEP 3 emits `{ready, blocked, self-marks, caveats}` and its `ready` term is the `after` set ONLY | **CONFIRMED** in code, not from the predecessor's record | read `readiness()`; `--readiness` run over the fixture |
| the daemon's enqueue door is `ignite add-job` (the gateway's `enqueue-job` intent), and it prints `queued: queue id <n>` | **CONFIRMED** | read `cli/commands/add-job.js` end to end; `cli/ignite.js` registers it |
| a `launch-agent` job REQUIRES a `profile` argument | **CONFIRMED** — `REQUIRED_ARGS_BY_ACTION['launch-agent'] = ['profile']`, re-checked in `validateArgs` | read `server/heart/heart-store.js:51`, `:281` |
| `register-job` (definition) and `add-job` (a scheduled run) are different acts, ordered by a foreign key | **CONFIRMED** | `cli/commands/register-job.js` header; `queue.job_id REFERENCES jobs.job_id` |
| the roster reading of "is this seat sitting" is `{RUN}/coordination/workers.md` `agent`/`active` via `load_workers` | **CONFIRMED**, and **already audited** — `trace-field-audit.md` rows 7 and 8 | `grep -n '^| [0-9]' trace-field-audit.md`; re-verified BY THE CHECK, which now reports **8** declared read sites, all audited |

**No premise was found wrong. Nothing was repaired in flight.**

One bound handed to every seat of this wave WAS reported false by the `leader` (#262: the
materialization command has no `--after` flag). It is **not a premise of this task** — this seat
materializes nothing — and is recorded here only so the next reader does not assume it was checked
and passed.

## 2. Custody

The file is shared with `M4-11` and has no standing holder. Claimed by message **#267** before the
first write, naming exactly what would change (additive STEP-4 section, its checks, the `--enqueue`
arm; no existing function of steps 1–3 and no line of `coord.py`). **Granted in #269.** The roster
check at claim time (`coordinate workers`) showed `checkout-fastpath-builder` NOT seated, so the
file was free throughout. Released by checking out promptly.

---

## 3. The stage

### 3.1 Readiness is NOT launch candidacy — the leader's bar, in code

STEP 3's predicate answers the `after`-set term ONLY. It has no self-state term, so a seat that has
already FINISHED satisfies it, and **enqueuing the ready list as-is relaunches finished seats.**
`enqueue()` therefore intersects the ready list with three self-state terms first, and NAMES every
exclusion — the exclusion is the requirement, the naming is what makes it auditable:

| Term | Read by | Excludes |
|---|---|---|
| terminal mark | STEP 1-2's own mark for the seat | `done` and `failed` alike — neither is a thing to launch |
| no ACTIVE roster row | `coord.load_workers` + `coord.current_row` — coord's OWN readers | a seat occupying a pane right now, which would be double-launched |
| descriptor on disk | `{RUN}/seats/<seat>/seat.md`, the same site `declared_outputs` reads | a `taskforce.csv`-only row, which would launch into nothing |

These are the three terms `coord.ready_seat_rows` carries and STEP 3 deliberately does not. They are
**called, never reimplemented.** STEP 3's one designed divergence from coord (`fx-r-artifact-strict`)
is untouched and remains one-directional per the `leader`'s ruling: nothing is enqueued on the
strength of coord's readiness where STEP 3 blocks.

### 3.2 The seed

Each launch carries the ABSOLUTE artifact paths its predecessors DECLARED, de-duplicated with order
preserved (two predecessors may declare the same artifact), so it arrives holding what it needs
instead of rediscovering it. Every path is re-confirmed to exist **at enqueue time**, through
`resolve_declared_path` — **one resolver**, extracted so that the seed and the artifact GRADE cannot
disagree about what a declared token means. That extraction is the only edit this change made inside
step-1-2 code, it is behaviour-preserving, and the 13 inherited checks prove it (§4).

**Two defects in THIS seat's own work were caught by its own evidence, and both are recorded rather
than quietly fixed, because each is a shape that passes a careless review:**

1. **The resolver was extracted but never wired.** `resolve_declared_path` was added and STEP 4 used
   it, while `declared_outputs` kept its original inline resolution — so the tree briefly held the
   TWO resolvers this section claims to have prevented, with the record already asserting there was
   one. Caught by reading the DIFF's deletions line by line before committing: the extraction showed
   as pure insertion, and an extraction that deletes nothing has not replaced anything. Fixed;
   behaviour-preserving, and the 13 inherited checks — including the artifact-grade ones — prove it.
2. **A branch that looked like the enqueue-time guard was not the guard.** Mutating the
   `path is None` arm away left **every check green** (M6, first battery). The real enqueue-time
   check is `declared_outputs` being re-called inside `seed_for`; the `path is None` arm is only the
   residual same-pass race. The mutation was retargeted at the real guard, which does go red, and
   the branch now says in the code what it is and what it is not. A check whose mutation cannot fail
   establishes nothing, and this one would have been banked as proof of a property it never tested.

A seat with NO predecessors seeds `[]`. **That is a complete seed, not a shortfall** — the root case
is the one an implementation keyed on predecessors forgets, and it has its own check.

### 3.3 The case that cannot arise from one pass, said out loud

A seed path missing at enqueue time is **unreachable within a single pass by construction**: STEP 1-2
marks a seat `failed` when a declared output is absent, and a `failed` predecessor satisfies no edge,
so no ready seat can have a `done` predecessor with a missing artifact. It is reachable exactly one
way — the artifact is DELETED between the marking pass and the enqueue. That is why the contract says
*"at enqueue time"*, why the check drives it as a time-of-check/time-of-use gap, and why the fact is
stated in `caveats` rather than left as a branch nobody reaches: a failure row that never appears
reads as *"this did not happen"* when the truth is *"this cannot happen from one pass"*.

---

## 4. GREEN — the full self-test, twice

```
cd 3-resources/tools/rbtv/ignite/jobs
python3 edge-runner-job.py --selftest
python3 edge-runner-job.py --selftest --fixture \
  ../../../../../.rbtv/goals/build-core-daemon-mvp/runs/run-3/seats/edge-runner-readiness-builder/fixture/run-fx
```

```
edge-runner-job --selftest against hermetic temp fixture /tmp/edge-runner-selftest-v8xmpss_/run-fx
  reads-subset-of-audit            PASS  criterion 2: all 8 declared read sites appear in the audit's reads[] (10 audited field rows parsed, 2 null-field rows)
  reads-match-coord-reader         PASS  criterion 2: coord.session_disposition indexes exactly ['disposition', 'ended', 'seat'], all declared in READS
  enum-matches-coord               PASS  criterion 2: enum matches coord's RECORD_DISPOSITION_WRITER ['done', 'exited', 'renew', 'revive']
  dispositions                     PASS  criterion 1/discriminating control: all 10 fixture verdicts correct (done=3, failed=5, refused=2)
  refusal-is-explicit              PASS  criterion 8: both undecidable seats carry disposition=None with a stated reason
  evidence-is-per-seat             PASS  criterion 3: evidence-read varies per seat (unfinished 2 sites, not-done 3, fully graded 4)
  scan-agrees-with-coord-reader    PASS  reader agreement: the row scan and coord.session_disposition agree on every fixture seat with a non-empty last cell
  no-status-column-written         PASS  criterion 6: 2 csv header(s) byte-identical across a full pass; no status column present
  readiness-verdicts               PASS  criterion 1/4: all 22 rows correct (ready=14, blocked=8), every blocked row's unmet set matches by name
  after-split-comma-only           PASS  criterion 2: comma-only split confirmed on 5 cells; both uninterpretable tokens survive whole, block their row, and carry a stated cause
  no-conditional-evaluator         PASS  criterion 3: excluded state's name absent from all 1748 lines; VERDICTS == ('ready', 'blocked'); the shape-note helper has exactly ONE call site, in `readiness`, and none elsewhere
  readiness-schema                 PASS  schema: keys ['ready', 'blocked', 'self-marks', 'caveats']; 14 ready, 8 blocked, every blocked row names >=1 unmet predecessor
  agrees-with-coord-ready-seats    PASS  criterion 7: 22 rows compared term-by-term against coord.ready_seat_rows; agreement on 21, and the 1 named divergence ['fx-r-artifact-strict'] is one-directional and explained by the declared-artifact grade
  enqueue-schema                   PASS  criterion 1: keys ['enqueued', 'validated', 'excluded', 'failed', 'caveats']; 6 enqueued, each with a real job-id and a seed, one door call apiece
  enqueue-excludes-self-marked     PASS  leader bar: all 8 ready-but-terminally-marked seats excluded and NAMED with their mark (3 done, 5 failed); none reached the queue
  seed-carries-pred-outputs        PASS  criterion 2: all 6 seeds match the predecessors' declared outputs by name (3 absolute path(s), all confirmed on disk), and every command carries its seed
  root-seat-empty-seed             PASS  criterion 6: all 3 no-predecessor seats ['fx-r-root', 'fx-open-sitting', 'fx-no-row'] enqueued with an empty seed and a real job-id
  missing-seed-path-fails          PASS  criterion 2 failure arm: 3 seat(s) refused with the absent path present.md named, none of them queued, and the unaffected root seat still enqueued; artifact restored
  single-enqueue-call-site         PASS  criterion 3: the enqueue command is built in exactly ONE function (`_enqueue_argv`) and submitted at exactly ONE call site (`enqueue`), across 44 functions in this file
  enqueue-signature-recorded       PASS  criterion 4: live signature `enqueue(coord, pkg, job_id, profile, readiness_result=None, at=None, submit=None, dry_run=False)` matches the literal and is recorded in probe-record-edge-runner-enqueue-builder.md
20/20 checks passed
```

The 13 inherited rows (M4-08's 8 and M4-09's 5) are **unchanged and still green**; this stage broke
none of them, including under the one-resolver extraction inside step-1-2 code.

### The stage's own output on the fixture

`python3 edge-runner-job.py --package <fixture>/run-fx --enqueue --job-id fx-launch-seat --profile fx-profile`

Driven through an injected submitter (`drive-enqueue.py`, this seat's folder), so the
whole stage runs and nothing is sent anywhere:

```
QUEUED    fx-open-sitting                job stub-1     seed: (none — root seat)
QUEUED    fx-no-row                      job stub-2     seed: (none — root seat)
QUEUED    fx-r-root                      job stub-3     seed: (none — root seat)
QUEUED    fx-r-one-done                  job stub-4     seed: /home/henri/ht-wkdir/second-brain/.rbtv/goals/build-core-daemon-mvp/runs/run-3/seats/edge-runner-enqueue-builder/fixture/run-fx/outputs/present.md
QUEUED    fx-r-two-done                  job stub-5     seed: /home/henri/ht-wkdir/second-brain/.rbtv/goals/build-core-daemon-mvp/runs/run-3/seats/edge-runner-enqueue-builder/fixture/run-fx/outputs/present.md
QUEUED    fx-r-spaces                    job stub-6     seed: /home/henri/ht-wkdir/second-brain/.rbtv/goals/build-core-daemon-mvp/runs/run-3/seats/edge-runner-enqueue-builder/fixture/run-fx/outputs/present.md
excluded  fx-done-outputs-present        terminal-mark=done
excluded  fx-done-output-missing         terminal-mark=failed
excluded  fx-renew                       terminal-mark=failed
excluded  fx-revive                      terminal-mark=failed
excluded  fx-exited                      terminal-mark=failed
excluded  fx-empty-disposition           terminal-mark=failed
excluded  fx-renewed-then-done           terminal-mark=done
excluded  fx-no-iospec                   terminal-mark=done

6 queued, 8 excluded, 0 failed; 6 command(s) built, 0 sent to any daemon.

the command the door would have received, for the first row:
  ignite add-job --fn fx-launch-seat --args-json {"package": "/home/henri/ht-wkdir/second-brain/.rbtv/goals/build-core-daemon-mvp/runs/run-3/seats/edge-runner-enqueue-builder/fixture/run-fx", "profile": "fx-profile", "seat": "fx-open-sitting", "seed": []} --trigger scheduled --at 2026-07-30T07:24:51Z
```

Six candidates queued, **eight ready seats excluded and each one named with the mark that excluded
it.** That 8 is the leader's bar in one number: every one of those eight is `ready` on the `after`
term and every one is the wrong thing to launch.

---

## 5. RED — every check proven to fail by mutating what it guards

Method for all seven: the pristine file was copied aside, one mutation applied by exact-anchor
replacement (the helper asserts the anchor occurs **exactly once**, so a silent no-op mutation is
impossible), `--selftest` run, then the pristine copy restored and the sha re-checked. **Every revert
is shown.** Pristine `sha256 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2`.

```
-rw-rw-r-- 1 henri henri 100717 Jul 30 07:23 /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/jobs/edge-runner-job.py
pristine sha256 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2

BASELINE: 20/20 checks passed

====================================================================================================
### M1 — an enqueued row with NO job-id — a row that is not evidence of a queued job
    '"job-id": m.group(1)'  ->  '"job-id": None'
  enqueue-schema                   FAIL  schema: fx-open-sitting is in `enqueued` with job-id None — a row with no id is not evidence of a queued job
19/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M2 — drop the terminal-mark term — the leader's bar, removed
    '        if mark is not None:'  ->  '        if False and mark is not None:'
  enqueue-excludes-self-marked     FAIL  leader bar: the terminal-mark exclusions are wrong — excluded but should not be []; NOT excluded but must be ['fx-done-output-missing', 'fx-done-outputs-present', 'fx-empty-disposition', 'fx-exited', 'fx-no-iospec', 'fx-renew', 'fx-renewed-then-done', 'fx-revive']; wrong mark []. A ready seat with a terminal mark that reaches the queue is a RELAUNCH of finished work.
  seed-carries-pred-outputs        FAIL  criterion 2: 8 wrong seed(s): fx-done-output-missing: seed [], expected None; fx-done-outputs-present: seed [], expected None; fx-empty-disposition: seed [], expected None; fx-exited: seed [], expected None; fx-no-iospec: seed [], expected None; fx-renew: seed [], expected None; fx-renewed-then-done: seed [], expected None; fx-revive: seed [], expected None
18/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M3 — stop de-duplicating the seed
    '            if key not in seen:'  ->  '            if True:'
  seed-carries-pred-outputs        FAIL  criterion 2: 2 wrong seed(s): fx-r-spaces: seed ['/tmp/edge-runner-selftest-ubazurdv/run-fx/outputs/present.md', '/tmp/edge-runner-selftest-ubazurdv/run-fx/outputs/present.md'], expected ['/tmp/edge-runner-selftest-ubazurdv/run-fx/outputs/present.md']; fx-r-two-done: seed ['/tmp/edge-runner-selftest-ubazurdv/run-fx/outputs/present.md', '/tmp/edge-runner-selftest-ubazurdv/run-fx/outputs/present.md'], expected ['/tmp/edge-runner-selftest-ubazurdv/run-fx/outputs/present.md']
19/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M4 — carry no seed at all
    '                seed.append(key)'  ->  '                pass'
  seed-carries-pred-outputs        FAIL  criterion 2: 3 wrong seed(s): fx-r-one-done: seed [], expected ['/tmp/edge-runner-selftest-8_2vxmi2/run-fx/outputs/present.md']; fx-r-spaces: seed [], expected ['/tmp/edge-runner-selftest-8_2vxmi2/run-fx/outputs/present.md']; fx-r-two-done: seed [], expected ['/tmp/edge-runner-selftest-8_2vxmi2/run-fx/outputs/present.md']
19/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M5 — treat an empty seed as a failure — the root case, broken
    '        if missing:'  ->  '        if missing or not seed:'
  seed-carries-pred-outputs        FAIL  criterion 2: 3 wrong seed(s): fx-no-row: seed None, expected []; fx-open-sitting: seed None, expected []; fx-r-root: seed None, expected []
  root-seat-empty-seed             FAIL  criterion 6: fx-r-root FAILED to enqueue — a seat with no predecessors has an empty seed, which is a complete seed and not a shortfall
  missing-seed-path-fails          FAIL  criterion 2: the no-predecessor seat stopped enqueuing when an unrelated artifact vanished — the failure must be per-seat, not a whole-pass abort
17/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M6 — swallow the enqueue-time absence — the real guard, removed
    '        for tok in absent:'  ->  '        for tok in ():'
  missing-seed-path-fails          FAIL  criterion 2: fx-r-one-done enqueued with a seed path that is NOT on disk — the launch would fail on its first read
19/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M7 — a SECOND place that builds the enqueue command
    'def _enqueue_argv('  ->  'def _second_enqueue_argv(job_id):\n    return [IGNITE_BIN, _ENQUEUE_VERB, "--fn", job_id]\n\n\ndef _enqueue_argv('
  single-enqueue-call-site         FAIL  criterion 3: the enqueue command is built in ['_enqueue_argv', '_second_enqueue_argv'] (verb) / ['_enqueue_argv', '_second_enqueue_argv'] (binary), expected exactly ['_enqueue_argv'] for both — a second builder is a second enqueue path, and one of two paths always keeps reporting success
19/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK
====================================================================================================
### M8 — move the interface signature under its three consumers
    '            dry_run=False):'  ->  '             dry_run=False, extra=None):'
  enqueue-signature-recorded       FAIL  criterion 4: the live signature is (coord, pkg, job_id, profile, readiness_result=None, at=None, submit=None, dry_run=False, extra=None), but its three consumers were given (coord, pkg, job_id, profile, readiness_result=None, at=None, submit=None, dry_run=False)
19/20 checks passed
REVERTED -> sha 1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2  OK

====================================================================================================
AFTER ALL REVERTS:
20/20 checks passed
```

---

## 6. Criterion 3 — ONE enqueue implementation, and the search that proves it

Two arms, because a source search alone can be gamed by a check that measures its own text.

**Arm 1 — structural, inside the file.** `check_single_enqueue_call_site` asserts by
`inspect.getsource` over every function in the module that the door's verb and the door's binary are
referenced by **exactly one function** (`_enqueue_argv`) and that the submitter is invoked at
**exactly one call site** (`enqueue`). Every needle is ASSEMBLED from fragments
(`"_ENQUEUE" + "_VERB"`) so the check can never match its own text — a source search whose subject
appears in the searching function measures itself and passes vacuously.

**Arm 2 — the tree search, recorded.** Run over the whole rbtv tree, excluding `node_modules`:

```
$ cd 3-resources/tools/rbtv
$ grep -rn --include=*.js --include=*.py --include=*.sh -E "add-job|enqueue-job" . \
    | grep -v node_modules | grep -v /probes/ | awk -F: '{print $1}' | sort | uniq -c | sort -rn
     11 ignite/bridges/chat/forward-path.js
     10 ignite/cli/commands/add-job.js
      8 ignite/server/internal-api/dispatch.js
      7 ignite/gateway/parse.js
      2 ignite/jobs/run-state-job.py
      2 ignite/cli/commands/register-job.js
      1 ignite/team-kit/gateway_client.py
      1 ignite/team-kit/coord.py
      1 ignite/jobs/selfheal-room.py
      1 ignite/jobs/edge-runner-job.py      <- this stage: the ONE call site, in `_enqueue_argv`
      1 ignite/cli/ignite.js
      1 ignite/bridges/chat/thread-map.js
      1 ignite/bridges/chat/config.js
      1 core/capabilities/rbtv-cli/tool/lib/verbs.js
```

Reading of the hits, one by one:

| Site | Is it a competing enqueue? |
|---|---|
| `ignite/cli/commands/add-job.js`, `cli/ignite.js` | **No — it IS the door.** This is the daemon's own enqueue CLI, the thing `_enqueue_argv` calls. One door, called from one place |
| `ignite/gateway/parse.js`, `server/internal-api/dispatch.js`, `server/heart/heart-store.js` | **No** — the gateway/store side of that same door: the intent parser, the dispatcher and the store behind it |
| `ignite/bridges/chat/forward-path.js` | **No** — the chat bridge's two forward legs (D90). A different domain (an inbound chat message), not the edge-runner's launch of a ready seat, and it goes through the same one door |
| `ignite/jobs/selfheal-room.py` | **No, and it is worth reading:** the file's header records that it CONSIDERED `ignite add-job --fn launch-agent` and chose the kit path instead, with reasons. It contains no enqueue |
| `core/capabilities/rbtv-cli/tool/lib/verbs.js` | **No** — a verb allow-list naming the CLI command, not an implementation |
| `ignite/jobs/run-state-job.py` | **No, and it was read at 07:23 while `recompute-cli-builder` was writing it.** Both hits are PROSE making the same register-vs-add distinction; the file contains no enqueue. Checked precisely because a concurrently-written file is where a second implementation would appear |
| `ignite/cli/commands/register-job.js` | **No** — the CATALOGUE side. `register-job` installs a definition and fires nothing; `add-job` schedules a run. Different acts, ordered by `queue.job_id REFERENCES jobs.job_id` |
| `ignite/team-kit/gateway_client.py`, `ignite/team-kit/coord.py` | **No** — one comment apiece, naming the intent while explaining what the gateway has no door for |
| `ignite/bridges/chat/thread-map.js`, `ignite/bridges/chat/config.js` | **No** — a field comment and a timestamp-format note, both belonging to the chat bridge's use of the one door |

**No competing enqueue implementation exists**, so the outcome-map row *"a competing enqueue already
exists → STOP and report to the leader with both sites named"* did not fire. The search is recorded
rather than asserted so a later reader can re-run it instead of trusting this paragraph.

---

## 7. The live-run read (READ-ONLY, hashed either side)

The `leader` named two genuine run-3 rows the intersection must exclude (#269):
`queue-loss-detector-namer`, listed READY with an EMPTY `after` set while its own mark is `failed`;
and `master-path-wirer`, carrying disposition `exited`. Both were confirmed against the LIVE package
with an injected submitter, so nothing was queued:

```
$ python3 drive-enqueue.py <run-3>
excluded  master                         terminal-mark=done
excluded  chief-of-staff                 terminal-mark=failed
excluded  leader                         terminal-mark=failed
excluded  elicitator                     terminal-mark=failed
excluded  staffer                        terminal-mark=failed
excluded  planner                        terminal-mark=failed
excluded  sensor-session-resolver        terminal-mark=done
excluded  watch-runclosed-guard          terminal-mark=done
excluded  sensor-exit-legibility         terminal-mark=done
excluded  watch-cadence-lander           terminal-mark=failed
excluded  sensor-autopath-prover         terminal-mark=done
excluded  queue-loss-diagnoser           terminal-mark=done
excluded  selfheal-profile-repointer     terminal-mark=failed
excluded  trace-field-auditor            terminal-mark=done
excluded  test-goal-fixture-author       terminal-mark=done
excluded  master-path-wirer              terminal-mark=failed
excluded  queue-loss-detector-namer      terminal-mark=done
excluded  trace-gap-recorder             terminal-mark=done
excluded  edge-runner-verifier-builder   terminal-mark=done
excluded  one-live-run-rule-builder      terminal-mark=done
excluded  edge-runner-readiness-builder  terminal-mark=done
excluded  queued-run-notifier-builder    terminal-mark=done
excluded  edge-runner-enqueue-builder    active-roster-row=yes
excluded  recompute-cli-builder          active-roster-row=yes
excluded  queue-notify-prover            active-roster-row=yes

0 queued, 25 excluded, 0 failed; 0 command(s) built, 0 sent to any daemon.
```

`sha256sum` of `sessions.csv`, `taskforce.csv` and `coordination/workers.md` **before and after** the
pass: **identical**. The pass wrote nothing to the live run.

---

## 8. Commit, and what this seat did NOT do

Scoped to two paths — the stage and this record. Diffed before staging; no foreign hunk rides along.

```
rbtv repo  3c6a2ec   ignite/jobs/edge-runner-job.py            1 file changed, 650 insertions(+), 14 deletions(-)
vault repo 93851bfe6   the probe record + this seat's folder     28 files, insertions only
```

`git show <sha>:ignite/jobs/edge-runner-job.py | sha256sum` equals the working file's
`1ae9afffaf119a2a4d8b4cbfb9b1500bc6db3b0e4ff6fbd4bed740203cd2bab2` — **the committed bytes are the
bytes the 20 checks and the 8 mutations ran against**, which a green run in a working tree does not
by itself establish. `ignite/jobs/run-state-job.py` was modified in the same repo by
`recompute-cli-builder` during this sitting; it is **untracked, NOT in this commit, and not a
dependency of this change** — verified with `git status --short` before staging and
`git show --stat` after, per `conduct.md` §6. The rbtv commit used `--only <path>`.

- **It arms nothing and queued nothing.** No live enqueue, no `register-job`, no daemon contact. The
  interface is proven on a fixture; adoption is a separate, gated act (`r-cutover-gated`).
- **It did not modify `coord.py`**, and did not conform STEP 3's predicate or coord's to the other.
- **It built no conditional-edge evaluator and no third verdict**, and the naming collision that
  surfaced is reported rather than resolved by weakening the check that caught it (see below).
- **It did not verify its own work's acceptability.** That is a downstream seat's, then the
  `leader`'s.
- **It did not check whether any seeded artifact's CONTENT is correct** — `grades-not-afforded` still
  holds, and a seed path being present is not a claim that its content is right.

### The one finding reported to the `leader` rather than settled here

The `leader` named the exclusion list by a word (#269) that is **already taken in this system**: it
is the registry's name for a row excluded by a CONDITIONAL EDGE, and STEP 3's accepted
`check_no_conditional_evaluator_or_third_verdict` asserts that name occurs NOWHERE in this file's
source. Using it for the self-state exclusions turned that accepted check RED — correctly. Weakening
an accepted check to make room for a name was refused; the key is `excluded`, the leader's substance
(every exclusion NAMED, list present even when empty) is unchanged, and the collision is reported in
the check-out.
