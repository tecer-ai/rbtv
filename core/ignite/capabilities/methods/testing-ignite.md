# Testing Ignite after a change

Show that a change to Ignite left its behaviour intact, and report what was shown at each layer: the test programs on Linux, the same programs on Windows, and the deployed service.

Required inputs, supplied by the caller:

- the list of changed files and the commit the change starts from;
- whether a deploy and live checks are in scope, the installation they target, and who authorized them;
- the name of the session that runs Windows checks, or the statement that none is reachable.

When the list of changed files is missing, stop and ask for it. When a deploy or a Windows run is not authorized or not reachable, run the layers you can and report the others as not run; do not infer one layer from another.

## 1. Find what the change obliges

| The change touches | Run |
|---|---|
| Any file under `core/ignite/` | The 18 Ignite test programs |
| `turn.js`, `store.js`, or a file under `core/cast/capabilities/tools/cast/lib/` (Ignite imports `agent`, `core`, `handles`, `launch`, `optional` and `win-exec` from there) | The 18 programs and also `test_cast.js`, `test_route.js` and `test_spark.js` |
| A file the installer scans (a skill, rule, pack, agent, hook, component record or tool record, or the first line of a tool's program; [rbtv CLI](../../../rbtv/capabilities/glossary/rbtv-cli.md) owns the list) or rbtv's install code | The installer selftest, on Linux and on Windows |
| Code the waking service runs, `deploy.sh` or the systemd unit | All of the above, then deploy and live checks when the caller put them in scope |

Rows add up: a change that matches several rows runs every suite those rows name. A change to a test program obliges that program and the proof in section 3 that it can still fail.

## 2. Run the suites

Run from the repository root of the copy that holds the change. Commands on PATH (`ignite`, `cast`, `spark`) run the installed copy, so start each program by path as shown. Run the programs one at a time, never two at once: `test_daemon.js` starts real child processes and waits 4 seconds for each, and under parallel load its tests `lock-refusal` and `sigterm-clean` time out.

Save the outputs before the first edit, in a folder outside the repository, then again after the change. `$OUT` is that folder.

```
cd core/ignite/capabilities/tools/ignite
for t in audio board cli config connect daemon deploy dreamer ingress manage memory memory_write outbox prompt slack store turn turn_loop; do
  node test_$t.js > "$OUT/test_$t.out" 2> "$OUT/test_$t.err"; echo "test_$t $?"
done
```

```
cd core/cast/capabilities/tools/cast
node test_cast.js > "$OUT/test_cast.out" 2> "$OUT/test_cast.err"; echo "test_cast $?"
node test_route.js > "$OUT/test_route.out" 2> "$OUT/test_route.err"; echo "test_route $?"
cd ../spark
node test_spark.js > "$OUT/test_spark.out" 2> "$OUT/test_spark.err"; echo "test_spark $?"
```

```
python3 core/rbtv/capabilities/tools/rbtv/install.py selftest > "$OUT/selftest.out" 2> "$OUT/selftest.err"; echo "selftest $?"
```

On Windows the commands are the same with `python` in place of `python3`; run each program on its own line when the shell has no `for` loop.

The pass signal is exit 0 for every program, plus the line named here. Seconds were measured on Linux, serially, with Node v24.18.0 and Python 3.14.4; they show which programs are slow, not a limit.

| Program | Pass signal besides exit 0 | Seconds |
|---|---|---|
| `test_audio.js`, `test_config.js`, `test_ingress.js`, `test_manage.js`, `test_memory.js`, `test_outbox.js`, `test_prompt.js`, `test_slack.js` | One line `PASS <name>` per test, no line starting `FAIL` | under 1 each |
| `test_board.js`, `test_store.js` | Same | 1 and 2 |
| `test_memory_write.js`, `test_turn_loop.js` | Same | 5 each |
| `test_connect.js`, `test_cli.js`, `test_deploy.js` | Same, and the last line is `ok` | 17, 29 and 3 |
| `test_dreamer.js` | Same | 20 |
| `test_daemon.js` | Same. It also prints the service's log lines, each starting with `{`; ignore them, and do not read its last line as the result | 25 |
| `test_turn.js` | Its only line: `test_turn: ok` | 1 |
| `test_cast.js` | Its only line: `all cast tests passed` | 52 |
| `test_route.js` | Its only line: `all route tests passed` | 7 |
| `test_spark.js` | Its only line: `test_spark: ok` | 3 |
| Installer selftest | Last line `selftest: PASS`, no line containing `[FAIL]` | 30 |

A failing test prints `FAIL <name>: <error>` and the program exits non-zero. The four one-line programs name no tests: their exit code and that line are all they show. The selftest's count of `[PASS]` and `[SKIP]` lines depends on the folder it runs in and on what the surrounding installation holds, so compare it only with a run from the same place.

A Node version that still marks SQLite as experimental prints `ExperimentalWarning: SQLite is an experimental feature` on stderr. That is not a failure; with Node v24.18.0 stderr was empty.

## 3. What counts as proof

All four hold, or the report says which does not:

1. **Linux.** Every obliged program exits 0, and the names that passed are the same before and after the change. Compare with:

   ```
   grep -h '^PASS' "$OUT"/test_*.out | LC_ALL=C sort > "$OUT/names.txt"
   grep -E '^\s*\[(PASS|SKIP|FAIL)\]' "$OUT/selftest.out" | LC_ALL=C sort > "$OUT/selftest-names.txt"
   ```

   and `diff` the two files against the ones saved before the edit. Every added or removed name is explained by the change. `LC_ALL=C` keeps the order identical between runs. The selftest line `D2-scope` carries a temporary folder name and differs on every run; it is the one expected difference. Never count on a total alone: one removed test and one added test leave the total unchanged.
2. **Each touched test can fail.** For every test the change adds or edits, break the behaviour it checks once, see that test print `FAIL` and the program exit non-zero, then restore the file. A test never seen red proves nothing about its subject.
3. **Windows.** Every obliged program exits 0 there, and every skipped test prints `skip: <name> is Linux-only: <reason>`. Exactly fifteen Ignite tests are skipped, each for something Windows does not have: in `test_daemon.js`, `sigterm-clean`, `unit-path-filled` and `unit-path-has-link-bin`; in `test_turn_loop.js`, `old colon history folder is found`; in `test_deploy.js`, the eleven tests that run a deploy, which is every test except `help-needs-nothing`, `refuses-off-linux` and `unknown-words-refused`. `test_cast.js` prints one more skip, for the `setsid` launch check. Any other skip, or a sixteenth, is a finding.
4. **Who ran what.** The report names each system, the commit, and who ran it: you, or the Windows session whose reply you quote.

Never skip a whole program, delete or weaken a test, or loosen an assertion to make a run pass. The repository's [Linux and Windows rule](../../../../CLAUDE.md) states what a change must respect on both systems.

## 4. The Windows run

The waking service runs on Linux only; every other part of Ignite, cast, spark and the installer runs on both systems. A Linux machine cannot produce the Windows result, and a Windows result is never inferred from a Linux one.

Send the session the caller named a message with literal steps and the expected output of each; it may run a smaller model. It works in its own scratch worktree and commits and pushes nothing.

1. Name the commit the change starts from, which the session checks out in its scratch worktree.
2. Paste the change as a plain-text `git diff` in the message. Do not compress or encode it: an encoded patch is refused as unreadable code from another session.
3. The session applies it with `git apply --3way`, which also handles a checkout with Windows line endings.
4. A pasted diff does not keep its exact bytes. For every changed file the session runs `git hash-object <file>` and checks that the result starts with the second id on that file's `index <a>..<b>` line in the diff. A checksum of the patch text is not that check.
5. The session runs the obliged programs of section 2, one at a time, and returns each exit code, each `skip:` line and the selftest's last line.

A message to that session returns no delivery receipt, and its reply arrives minutes later. Wait for the reply inside the same piece of work, or report the Windows layer as not run with the exact message that was sent.

## 5. Deploy and live checks

These apply only when the caller put them in scope, and only on the Linux machine that runs the service. Follow the [operator runbook](../tools/ignite/documentation/runbook.md) for every command; this section states the order and what each check observes.

1. **Commit**, then **deploy at that commit** (runbook, Deploy). Observe: the commit `ignite deploy` prints as the commit now is the commit that was tested, and the service state it prints is active. A deploy restarts the service for every agent of the installation; it needs the authority of section 6.
2. **Status** (runbook, Status). Observe: the unit is active, and its log shows a `ready` event after the restart and no `error` event for an agent that was launchable before.
3. **Per-agent state** (runbook, Inspect). Observe: `work status` answers for each agent the change can affect, with no hold the change introduced.
4. **The changed behaviour itself.** Name, before acting, the clause to show, the stimulus and the stored state that will show it: a `turn` log event, the outbox row, the board or memory diff. The runbook gives no pass criteria for a live Slack turn, so a live turn is its own claim with its own authority; when it is not run, report it as not exercised.
5. **Dreamer**, when the change touches memory, the board, schedules or consolidation (runbook, Dreamer). A timer wake must show a new threadless conversation and harness session, input equal to its schedule id, and all five checked memory files in its prompt. `ignite dreamer run` prints one JSON line; classify the run and check the state its kind requires:

| Run kind | State it must show |
|---|---|
| Changed | The expected filing or removal, a bounded diff or a commit, the cursor advanced, and a queued digest (`changed` and `digestQueued` true) |
| Quiet | Files, commit and cursor unchanged, no digest, no model call, and the success time advanced |
| Duplicate-only | The duplicate line removed and the success time advanced; no commit is required, and no new record was written for the duplicate |
| Refused | Memory and cursor unchanged, a non-null `alert`, a queued failure notice (`noticeQueued` true) and exit 1 |

`delivered` is always false for the manual command, and a stored `delivered` on an outbox row is delivery evidence, not an observation of the Slack interface. Check lock contention separately when the change covers concurrency.

## 6. Authority, observation and the report

**Authority.** Before an action outside your own scratch copy (a deploy, a restart, a send, clearing a hold, enabling a schedule or the Dreamer), identify the exact operation, its destination, the identity and credentials it uses, its side effects and who owns recovery. Use the authorization the caller gave and the actions the assignment necessarily includes; ask only when authority is missing or the action goes beyond it. Reads and reversible local actions need no approval. When a required action is refused, record it as blocked and route that exact step to the owner or an authorized operator. Never change the wrapper, the credential or the route to get past a refusal.

**Observation.** Judge each clause from a source independent of the command that acted: the stored state, a diff, a log event, the destination itself. A command's acceptance, an exit 0 or a `PASS` summary is not that source for a live clause. After each step that changes state, confirm its result before the next. When a send has an uncertain outcome, inspect its destination and the store before any retry. Record six things separately for a live clause: approval, execution, delivery, the agent's response, the state change, and the verdict.

**The report.** Give each clause one outcome:

| Outcome | When |
|---|---|
| passed | The specified stimulus and the independent source agree |
| partial | Some of the clause is shown; say which part |
| not exercised | The path the clause needs never occurred |
| blocked | Missing authority or environment prevented the run |
| failed | The observed behaviour contradicts the clause |

A fixture result, a Windows result and a live result each approve only their own layer and time window. State every command with its exit code, the system and commit it ran on and who ran it, and the names that changed between the two saved outputs. State what remains unverified, in words, and what state was restored or deliberately left changed.

At a failed live check, stop every related change and hand the evidence and the options to the named recovery owner. Do not roll back or fix forward on your own, and do not clean up an input that may explain the failure.
