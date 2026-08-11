'use strict';

// ═══ THE (harness, model) → PROFILE-NAME CATALOG — core-build task 7.54 ═══════════════════════
//
// Built HERE and nowhere else, for the reason four call sites spent years refusing to build it
// anywhere else: "a second interpreter of the one file is the same drift as a second file"
// (DEC-1 § Shared profile source, registry `decisions.md#d-profile-source-unification`). Until
// this module existed, `engine/seeding.js`, `engine/lane-watch.js`, `engine/attached-execution.js`
// and `bridges/chat/forward-path.js` each held a seat's cast harness·model and could not name the
// profile that runs it, so every one of them launched a caller-named profile instead — and a seat
// cast as a frontier model silently ran whatever the caller happened to pass. That is the defect
// this file closes (owner ruling D19, extending D16).
//
// ⚑ ONE DERIVATION LAW, SHARED WITH `capabilities/bindings/tool/bindings.py#catalog`. That tool
// answers the AUTHORING question — "which harness+model can this workspace cast?" — off this same
// document; this module answers the LAUNCH question — "which profile IS that cast?". The two MUST
// agree or a binding the author was allowed to write is a binding the daemon cannot run, so the
// law is stated once and implemented identically on both sides:
//
//     harness = basename(exec.argv[0])
//     model   = the token following the FIRST of `--model` / `-m` that appears in argv,
//               never the last token (a trailing flag has no value to read)
//
// The ONE intentional difference is the READER, not the law: `bindings.py` line-scans the YAML
// (its own `ponytail:` note names PyYAML as the upgrade path it never needed), while this side is
// handed the ALREADY-PARSED config by `loadConfig`, so it reads `profile.exec.argv` directly.
// Same law, better reader — not a second law. A change to the law belongs in BOTH files, in the
// same change.
//
// ⚑ AMBIGUITY IS A REFUSAL, NOT A PICK — the one place this side is deliberately STRICTER than
// `bindings.py#castable()`. That function builds a dict, so two profiles claiming one
// (harness, model) silently resolve to whichever came last; sound there, because its answer is
// only "castable or not". Here the answer LAUNCHES a process, and silently launching one of two
// profiles that both claim the pair is the same silent-wrong-model failure this catalog exists to
// kill. `profiles:` is documented one-per-harness+model, so a duplicate is a config defect and is
// reported as one.
//
// ⚑ THE MODEL VOCABULARY IS THE PROFILE'S PIN, VERBATIM (`bindings.md`, owner ruling 2026-08-10):
// `claude-fable-5`, not `fable`. Only the pinned literal joins a binding back to a profile row.
// NOTHING here rewrites one spelling into another — an alias is UNMAPPED and refused loudly, and
// the refusal prints the castable set so the author can see what it should have said.

const path = require('node:path');
const { SpawnError, E_UNKNOWN_EFFORT } = require('./errors');

// A seat declares a cast this workspace cannot spawn — an alias where the pinned literal belongs,
// a model that left `profiles:`, a harness that was never configured. FAIL LOUD: the alternative
// is launching the caller's profile instead, which is the defect (a seat cast `claude-fable-5`
// ran `claude-sonnet-5` and the record said otherwise).
const E_UNMAPPED_BINDING = 'E_UNMAPPED_BINDING';
// Two profiles claim one (harness, model). See the ambiguity note above.
const E_AMBIGUOUS_BINDING = 'E_AMBIGUOUS_BINDING';
// The seat declares no cast at all (owner ruling D2, 2026-08-11). Distinct from UNMAPPED on
// purpose: unmapped means "you named a pair this workspace cannot spawn", uncast means "you named
// nothing", and the two need different fixes — fix the spelling vs. cast the seat.
const E_UNCAST_SEAT = 'E_UNCAST_SEAT';

// The flags a profile pins its model with, in the order `bindings.py` searches them. The order is
// load-bearing where a profile carries both: whichever this list names first wins on BOTH sides.
const MODEL_FLAGS = ['--model', '-m'];

// The (harness, model) a profile RUNS, read off its own `exec:` argv — the profile's own pin is
// the only authority for what it launches. `null` when the profile declares no `exec:` half at
// all (it spawns nothing, so it casts nothing — `bindings.py` skips the same rows).
function bindingOf(profile) {
  const argv = profile && profile.exec && Array.isArray(profile.exec.argv) ? profile.exec.argv : null;
  if (!argv || argv.length === 0) return null;
  const harness = path.basename(String(argv[0]));
  let model = '';
  for (const flag of MODEL_FLAGS) {
    const at = argv.indexOf(flag);
    // `at < argv.length - 1` is `bindings.py`'s `flag in argv[:-1]`: a flag in the LAST position
    // pins nothing, and reading past it would make the model `undefined`.
    if (at >= 0 && at < argv.length - 1) {
      model = String(argv[at + 1]);
      break;
    }
  }
  return { harness, model };
}

// Every profile this config can cast, as rows — the JS twin of `bindings.py#catalog`, minus its
// effort-dial and `validate_seat` columns (those answer the AUTHORING question; a launch has
// already been authored by the time it reaches here).
function catalogOf(profiles) {
  const rows = [];
  for (const [name, profile] of Object.entries(profiles || {})) {
    const binding = bindingOf(profile);
    if (binding) rows.push({ profile: name, ...binding });
  }
  return rows;
}

// True when a seat declares a cast at all. The channel master declares NONE by design
// (`materialize-seats.py#open_binding` — "the master's harness and model are named by the chat
// bridge at spawn time"), and an unmaterialized seat has no descriptor yet; both mean "no cast",
// which is the FALLBACK case, never a refusal.
function declaresBinding(binding) {
  return Boolean(binding && String(binding.harness || '').trim() && String(binding.model || '').trim());
}

// THE catalog lookup. Returns the profile NAME that runs this cast.
//
// Throws rather than returning null on an unmappable or ambiguous cast — see both ⚑ notes above.
// The caller's own profile name is accepted only as `fallbackFor` context in the message, never as
// a silent substitute.
function profileForBinding(profiles, binding, { seat = null } = {}) {
  const harness = String((binding && binding.harness) || '').trim();
  const model = String((binding && binding.model) || '').trim();
  const rows = catalogOf(profiles);
  const hits = rows.filter((r) => r.harness === harness && r.model === model);

  if (hits.length === 1) return hits[0].profile;

  const castable = rows.map((r) => `${r.harness}+${r.model} [${r.profile}]`).sort().join(' · ');
  if (hits.length === 0) {
    throw new SpawnError(
      E_UNMAPPED_BINDING,
      `REFUSING TO LAUNCH: ${seat ? `seat '${seat}'` : 'this seat'} declares harness '${harness}' `
      + `model '${model}', which NO launch profile carries. The model must be the profile's pin `
      + `VERBATIM (\`claude-fable-5\`, never \`fable\`) — this catalog never rewrites one spelling `
      + `into another. Castable: ${castable || '(none — the config declares no exec: half anywhere)'}. `
      + 'Launching the caller-named profile instead is what this refusal exists to prevent: it is '
      + 'how a seat cast as one model silently ran another while its record said otherwise.',
      { harness, model, seat, castable: rows },
    );
  }
  throw new SpawnError(
    E_AMBIGUOUS_BINDING,
    `REFUSING TO LAUNCH: harness '${harness}' model '${model}' is claimed by ${hits.length} launch `
    + `profiles (${hits.map((h) => h.profile).join(', ')}) — \`profiles:\` is one-per-harness+model, `
    + 'so this is a config defect. Refused rather than picking one: silently launching either of two '
    + 'profiles that both claim a cast is the failure this catalog exists to prevent.',
    { harness, model, seat, profiles: hits.map((h) => h.profile) },
  );
}

// ── THE SEAT'S CAST → THE PROFILE THAT RUNS IT (task 7.54 · owner ruling D19, extending D16) ────
//
// The defect: two launch paths reached a seat and NEITHER read what the seat was cast as. The
// daemon lane passed one profile for every seat of a goal (`engine/seeding.js`), and the chat
// bridge passed a deployment-wide chat profile by surface (`bridges/chat/forward-path.js`) — so
// the planning interviewer, cast `claude-fable-5` in `taskforce.csv` AND in its own `seat.md`, was
// revived on `claude-sonnet-5` whenever the owner answered it in Slack, with `sessions.csv`
// recording the launch as if nothing had diverged.
//
// ⚑ IT LIVES HERE, IN THE ONE SHARED RESOLVER, AND THAT PLACEMENT IS THE FIX (owner ruling D27,
// 2026-08-11). It shipped inside `server/spawn/spawn.js`, which put profile knowledge — including
// the profile-name literals above — on the spawn path, where `probe-caged-settings`'s standing
// "no per-profile special case anywhere in `server/spawn/`" invariant reads it as a violation. The
// invariant is right: DEC-1 § Shared profile source is the same rule this whole file exists to
// serve, and a second home for profile knowledge is the drift it forbids. `spawn.js` now reads the
// seat's declaration (seat.md parsing is a spawn concern, and its reader lives there) and DELEGATES
// the resolution here; nothing about the behaviour below changed in the move.
//
// ⚑ RESOLVED IN THE ONE FUNCTION EVERY LAUNCH ROUTES THROUGH — which is THIS one, not `spawn()`.
// ⚠ CORRECTED 2026-08-11 (launch-cast unification): this paragraph used to say `spawn()` was
// "downstream of the ticker, the chat bridge, the daemon lane, the attached lane and the
// WARM-SESSION LEG alike". That last clause was FALSE and it is why the warm door drifted for as
// long as it did — `live-sessions.js#launch()` never calls `spawn()`, it reuses only its composers,
// so a claim resting on `spawn()` being the single choke point was resting on nothing. The two
// doors now each call `castProfileFor` directly (see `live-sessions.js`'s own header), so the
// choke point is this function. It is also UPSTREAM of both records (`jobs_log.profile` and the
// at-dispatch `sessions.csv` row), so record and reality cannot drift apart by construction — they
// are written from the resolved value, not the requested one.
//
// ⚑ THE CAST OUTRANKS THE CALLER'S NAMED PROFILE, deliberately. A caller's profile is what runs a
// seat that declares NO cast; it is not a licence to override one that does. That is G-111's rule
// (an asserted value never outranks a declared one) applied to the model, and it is the whole
// content of ruling D16 — the record is the authority for what a seat runs.
//
// ⚑ A SEAT THAT DECLARES NO CAST REFUSES TO LAUNCH (owner ruling D2, launch-cast unification,
// 2026-08-11). This function used to return the caller's `profileName` untouched in that case, and
// that fallback is the whole failure this design closes: the transport's value could decide what
// an agent runs, so a seat reached over one surface ran a different model than the same seat
// reached over another. There is no longer any value to fall back TO — the chat bridge no longer
// names execution — and a fallback kept anywhere preserves the shape of the defect one level
// further away. Loud at launch beats quiet and wrong.
//
// The one seat this broke on arrival was the channel master, whose `open_binding` deliberately
// omitted the pair so the bridge could name it at spawn time. It is cast like every other seat now
// (its bindings file), which is the ruling "the master is just another agent" made mechanical.
function castProfileFor(profiles, binding, profileName, log, seat) {
  if (!declaresBinding(binding)) {
    // ⚑ D3(a), owner-ruled 2026-08-11: the refusal fires only where a MODEL IS ACTUALLY BEING
    // CHOSEN. A cast is derived by reading a profile's own command line for its model pin, so a
    // profile that pins none — the `sleep`-based stand-ins the probes launch to exercise spawning,
    // caging and killing without burning tokens — can be NAMED but can never be CAST TO. Demanding
    // a declaration that points at it demands something unwriteable, and D2 exists to stop a
    // transport deciding a MODEL, not to require a model where there is none to get wrong.
    //
    // The bound is exact and it is measured against the caller's profile, not assumed: if that
    // profile pins a model, a seat with no cast is a real gap and still refuses. Every production
    // profile pins one, so production behaviour is identical either way — this only readmits the
    // model-less case.
    const named = profiles && Object.hasOwn(profiles, profileName) ? profiles[profileName] : null;
    const namedCast = named ? bindingOf(named) : null;
    if (!namedCast || !declaresBinding(namedCast)) return profileName;
    throw new SpawnError(
      E_UNCAST_SEAT,
      `REFUSING TO LAUNCH: ${seat ? `seat '${seat}'` : 'this seat'} declares no cast — `
      + `\`harness:\` and \`model:\` must BOTH be present in its seat.md `
      + `(got harness ${JSON.stringify((binding && binding.harness) || null)}, `
      + `model ${JSON.stringify((binding && binding.model) || null)}). Cast it in the workflow's `
      + `bindings sheet (\`rbtv-bindings set\`) and re-materialize; the caller named `
      + `'${profileName}', and running that instead is what this refusal exists to prevent.`,
      { harness: (binding && binding.harness) || null, model: (binding && binding.model) || null, seat, requested: profileName },
    );
  }
  // Throws E_UNMAPPED_BINDING / E_AMBIGUOUS_BINDING — never falls back. A cast this workspace
  // cannot spawn must stop the launch: continuing on the caller's profile is precisely the silent
  // wrong-model launch being fixed.
  const cast = profileForBinding(profiles, binding, { seat });
  if (cast !== profileName) {
    log('info', 'launching the profile the seat is CAST as, not the one the caller named (D19)', {
      seat, requested: profileName, cast, harness: binding.harness, model: binding.model,
    });
  }
  return cast;
}

// ── THE SEAT'S DECLARED `effort:` WORD → THAT PROFILE'S RUNG NUMBER (owner-settled 2026-08-11) ──
//
// ⚑ STORAGE IS THE WORD, RESOLUTION IS THE NUMBER, AND THIS IS THE ONE JOINT BETWEEN THEM. A seat
// stores the HARNESS'S OWN WORD (`xhigh`, `--thinking`, `max`) — written by `bindings.py#set_seat`
// from a 1-based number it validated against this same ladder, rendered into `seat.md` and
// `taskforce.csv` by `materialize-seats.py`. `resolveEffort` downstream takes a NUMBER. Storing
// the number instead was considered and REFUSED: a rung INSERTED into a ladder silently
// reinterprets every stored number, with no diff anywhere and no check firing, whereas a stale
// WORD refuses loudly at every door that reads it, this one included.
//
// ⚑ IT LIVES HERE FOR THE REASON `castProfileFor` DOES. `spawn.js` reads the descriptor (seat.md
// parsing is a spawn concern) and delegates the MEANING of what it read, because
// `probe-caged-settings` holds `server/spawn/` to "no per-profile special case anywhere" and a
// ladder is per-profile knowledge by definition. Same split, same file, one law.
//
// ⚠ AND IT IS SEPARATE FROM `resolveEffort` ON PURPOSE — never widen that one to take a word.
// `probe-launch-profiles` leg 11 asserts it REFUSES the legacy word `'high'`, which is what keeps
// a caller left on the retired abstract vocabulary failing loudly instead of resolving to
// something plausible. Word→rung and rung→argv are two questions; one function each.
//
// Returns { rung, inert }. `inert` is REPORTED, never folded into the null rung: where no dial
// exists the seat's declaration is ACCEPTED and said so (G-270, owner ruling), and a caller that
// could only see `rung: null` could not tell accept-and-report from a silent drop.
function effortRungFor(profile, word, profileName, seatName = null) {
  const want = String(word || '').trim();
  if (!want) return { rung: null, inert: false };          // undeclared — the harness's own default
  const effort = profile && profile.effort;
  // ponytail: no `effort:` block reads as "no dial" rather than refusing. Ceiling: unreachable
  // from a loaded config today — every castable profile declares a block, and `validateEffort`
  // forces even a dial-less harness to say `inert: true` explicitly. Upgrade path if a profile
  // ever ships without one: make this a throw, since by then the silence would be a real gap.
  if (!effort) return { rung: null, inert: false };
  if (effort.inert === true) return { rung: null, inert: true };
  const rungs = Array.isArray(effort.rungs) ? effort.rungs : [];
  const at = rungs.indexOf(want);
  if (at < 0) {
    // ⚠ -1 MUST NOT FLOW ONWARD. `resolveEffort` would report "effort must be an INTEGER RUNG
    // >= 1, got 0" — true of the number it received, and useless: it sends the reader hunting a
    // rung nobody wrote instead of the stale word in the descriptor in front of them.
    throw new SpawnError(
      E_UNKNOWN_EFFORT,
      `REFUSING TO LAUNCH: ${seatName ? `seat '${seatName}'` : 'this seat'} declares effort `
      + `'${want}', which is not a rung of profile ${profileName}'s ladder `
      + `(${rungs.map((r, i) => `${i + 1}=${r}`).join(', ') || '(empty)'}). A seat stores the `
      + `HARNESS'S OWN WORD, so a word from another harness's ladder — or one this ladder no `
      + `longer carries — refuses HERE rather than reaching the binary. Re-cast the seat `
      + `(\`rbtv-bindings set\`) and re-materialize.`,
      { profile: profileName, seat: seatName, effort: want, rungs: rungs.slice() },
    );
  }
  return { rung: at + 1, inert: false };
}

module.exports = {
  bindingOf,
  catalogOf,
  castProfileFor,
  declaresBinding,
  effortRungFor,
  profileForBinding,
  MODEL_FLAGS,
  E_UNMAPPED_BINDING,
  E_AMBIGUOUS_BINDING,
  E_UNCAST_SEAT,
};
