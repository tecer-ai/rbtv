'use strict';

// ═══ THE (harness, model) → LAUNCH-SPEC TABLE — core-build tasks 7.54 / 7.787 ═════════════════
//
// ⚠ THE NAME LAYER IS GONE (owner ruling `#d-abolish-profile-names`, 2026-08-12). This module used
// to map a seat's cast (harness, model) onto a launch profile NAME, because `profiles:` was keyed
// by arbitrary names and a name was the only thing a caller could select. Both halves of that are
// abolished: `launch-specs:` in `config/spawn-profiles.yaml` is keyed BY THE PAIR ITSELF, and no
// caller anywhere in ignite may select a launch spec. Bindings
// (`.rbtv/config/modules/{module}/{component}/bindings/{code}.json`) are the ABSOLUTE source of
// truth for what a seat runs; the daemon reads the seat's own descriptor at spawn time and looks
// the mechanics up by the pair. There is nothing left in between for a name to name.
//
// ⚑ THE KEY IS THE AUTHORITY, AND THAT DELETED A DERIVATION LAW RATHER THAN MOVING IT. Until the
// abolition the pair a spec RAN was derived from its own `exec:` argv — `harness = basename(argv[0])`,
// `model = the token after the first --model/-m` — identically here and in
// `capabilities/bindings/tool/bindings.py`, because the two answer the same question from opposite
// ends (that tool answers "what can this workspace cast?", this module answered "which profile IS
// that cast?"). Now the YAML states the pair directly, so both sides READ it and neither derives
// it. `bindingOf` survives for ONE job: proving at config LOAD that a spec's argv agrees with the
// key it is filed under (`profiles.js#validateSpecKey`), so `claude/claude-opus-5` can never carry
// an argv that runs haiku. That check is the old law kept as a GUARD, which is the only place it
// still earns its keep.
//
// ⚑ THE MODEL VOCABULARY IS THE SPEC'S PIN, VERBATIM (`bindings.md`, owner ruling 2026-08-10):
// `claude-fable-5`, not `fable`. Only the pinned literal joins a binding back to a launch spec.
// NOTHING here rewrites one spelling into another — an alias is UNMAPPED and refused loudly, and
// the refusal prints the castable set so the author can see what it should have said.

const path = require('node:path');
const { SpawnError, E_UNKNOWN_EFFORT } = require('./errors');

// A seat declares a cast this workspace cannot spawn — an alias where the pinned literal belongs,
// a model that left `launch-specs:`, a harness that was never configured. FAIL LOUD: the
// alternative is launching something else, which is the defect (a seat cast `claude-fable-5` ran
// `claude-sonnet-5` and the record said otherwise).
const E_UNMAPPED_BINDING = 'E_UNMAPPED_BINDING';
// The seat declares no cast at all (owner ruling D2, 2026-08-11; made absolute by
// `#d-abolish-profile-names` sub-ruling 3, 2026-08-12 — there is no fallback left anywhere).
// Distinct from UNMAPPED on purpose: unmapped means "you named a pair this workspace cannot
// spawn", uncast means "you named nothing", and the two need different fixes — fix the spelling
// vs. cast the seat.
const E_UNCAST_SEAT = 'E_UNCAST_SEAT';

// The flags a spec may pin its model with, in search order. Read ONLY by the load-time key/argv
// agreement guard (see the ⚑ note above) — never to derive a catalog.
const MODEL_FLAGS = ['--model', '-m'];

// THE INTERNAL KEY. `launch-specs:` is nested (`harness: { model: { … } }`) in YAML because that is
// what a human edits without repeating himself; it is FLATTENED to this one string at load so every
// lookup in the daemon is a single own-property test. The separator is `/` because a model literal
// already carries `/` (`zai-coding-plan/glm-5.2`) and a harness name never does, so
// `harness + '/' + model` is unambiguous read left-to-right at the first separator.
function specKey(harness, model) {
  return `${String(harness || '').trim()}/${String(model || '').trim()}`;
}

// The (harness, model) a spec's argv ACTUALLY runs, read off its own `exec:` argv. Used ONLY by the
// config-load guard that proves the argv agrees with the key. `null` when the spec declares no
// `exec:` half at all (a `command:`-halves spec, or a job).
function bindingOf(spec) {
  const argv = spec && spec.exec && Array.isArray(spec.exec.argv) ? spec.exec.argv : null;
  if (!argv || argv.length === 0) return null;
  const harness = path.basename(String(argv[0]));
  let model = '';
  for (const flag of MODEL_FLAGS) {
    const at = argv.indexOf(flag);
    // `at < argv.length - 1`: a flag in the LAST position pins nothing, and reading past it would
    // make the model `undefined`.
    if (at >= 0 && at < argv.length - 1) {
      model = String(argv[at + 1]);
      break;
    }
  }
  return { harness, model };
}

// Every (harness, model) this config can cast, as rows — READ off the keys, derived from nothing.
// The twin of `capabilities/bindings/tool/bindings.py#catalog`, which reads the same keys.
function catalogOf(launchSpecs) {
  return Object.keys(launchSpecs || {}).map((key) => {
    const at = key.indexOf('/');
    return { harness: key.slice(0, at), model: key.slice(at + 1), key };
  });
}

// True when a seat declares a cast at all. Under the abolition every seat that launches MUST — an
// undeclared cast is a refusal, not a fallback (`#d-abolish-profile-names` sub-ruling 3).
function declaresBinding(binding) {
  return Boolean(binding && String(binding.harness || '').trim() && String(binding.model || '').trim());
}

// ── THE SEAT'S CAST → THE LAUNCH SPEC THAT RUNS IT (task 7.54 · D19 · D27 · 7.787) ──────────────
//
// The defect this closed: two launch paths reached a seat and NEITHER read what the seat was cast
// as. The daemon lane passed one profile for every seat of a goal (`engine/seeding.js`), and the
// chat bridge passed a deployment-wide chat profile by surface (`bridges/chat/forward-path.js`) —
// so the planning interviewer, cast `claude-fable-5` in `taskforce.csv` AND in its own `seat.md`,
// was revived on `claude-sonnet-5` whenever the owner answered it in Slack, with `sessions.csv`
// recording the launch as if nothing had diverged.
//
// ⚑ IT LIVES HERE, IN THE ONE SHARED RESOLVER, AND THAT PLACEMENT IS THE FIX (owner ruling D27,
// 2026-08-11). It shipped inside `server/spawn/spawn.js`, where `probe-caged-settings`'s standing
// "no per-spec special case anywhere in `server/spawn/`" invariant reads spec knowledge as a
// violation. `spawn.js` reads the seat's declaration (seat.md parsing is a spawn concern, and its
// reader lives there) and DELEGATES the resolution here.
//
// ⚑ THERE IS NO CALLER TO FALL BACK TO ANY MORE, AND THAT IS THE WHOLE OF 7.787. This function
// used to take a `profileName` — the caller's requested profile — and return it whenever the seat
// declared nothing. Every remaining `--profile` flag, the lane marker's second token and the chat
// bridge's `session_profile` existed to supply that one parameter. They are all gone: an uncast
// seat is a NAMED REFUSAL, at every door, on every lane. Loud at launch beats quiet and wrong.
//
// ⚠ THE MODEL-LESS CARVE-OUT IS GONE TOO (it was D3(a), 2026-08-11: a caller-named spec pinning no
// model could still launch an uncast seat, so the `sleep`-based probe stand-ins kept working).
// Under the abolition there is no caller-named spec at all, so the carve-out has no subject. Job
// mechanics that pin no model live in the `jobs:` block and are not reachable from a seat launch.
//
// Returns `{ key, spec }` — the flattened `launch-specs:` key and its mechanics block.
function specForSeatCast(launchSpecs, binding, log, seat) {
  const specs = launchSpecs || {};
  if (!declaresBinding(binding)) {
    throw new SpawnError(
      E_UNCAST_SEAT,
      `REFUSING TO LAUNCH: ${seat ? `seat '${seat}'` : 'this seat'} declares no cast — `
      + '`harness:` and `model:` must BOTH be present in its seat.md '
      + `(got harness ${JSON.stringify((binding && binding.harness) || null)}, `
      + `model ${JSON.stringify((binding && binding.model) || null)}). Cast it in the workflow's `
      + 'bindings sheet (`rbtv-bindings set`) and re-materialize. There is no fallback: since '
      + '`#d-abolish-profile-names` no caller anywhere names what a seat runs, so an uncast seat '
      + 'has nothing it could run AS.',
      { harness: (binding && binding.harness) || null, model: (binding && binding.model) || null, seat },
    );
  }
  const harness = String(binding.harness).trim();
  const model = String(binding.model).trim();
  const key = specKey(harness, model);
  if (!Object.hasOwn(specs, key)) {
    const castable = catalogOf(specs).map((r) => `${r.harness}+${r.model}`).sort().join(' · ');
    throw new SpawnError(
      E_UNMAPPED_BINDING,
      `REFUSING TO LAUNCH: ${seat ? `seat '${seat}'` : 'this seat'} declares harness '${harness}' `
      + `model '${model}', which NO launch spec carries. The model must be the spec's pin VERBATIM `
      + '(`claude-fable-5`, never `fable`) — this table never rewrites one spelling into another. '
      + `Castable: ${castable || '(none — the config declares no launch-specs: block)'}.`,
      { harness, model, seat, castable: catalogOf(specs) },
    );
  }
  if (log) log('debug', 'launching the seat\'s own cast (D19 · #d-abolish-profile-names)', { seat, harness, model });
  return { key, spec: specs[key] };
}

// ── THE SEAT'S DECLARED `effort:` WORD → THAT SPEC'S RUNG NUMBER (owner-settled 2026-08-11) ─────
//
// ⚑ STORAGE IS THE WORD, RESOLUTION IS THE NUMBER, AND THIS IS THE ONE JOINT BETWEEN THEM. A seat
// stores the HARNESS'S OWN WORD (`xhigh`, `--thinking`, `max`) — written by `bindings.py#set_seat`
// from a 1-based number it validated against this same ladder, rendered into `seat.md` and
// `taskforce.csv` by `materialize-seats.py`. `resolveEffort` downstream takes a NUMBER. Storing
// the number instead was considered and REFUSED: a rung INSERTED into a ladder silently
// reinterprets every stored number, with no diff anywhere and no check firing, whereas a stale
// WORD refuses loudly at every door that reads it, this one included.
//
// ⚑ IT LIVES HERE FOR THE REASON `specForSeatCast` DOES. `spawn.js` reads the descriptor (seat.md
// parsing is a spawn concern) and delegates the MEANING of what it read, because
// `probe-caged-settings` holds `server/spawn/` to "no per-spec special case anywhere" and a ladder
// is per-spec knowledge by definition. Same split, same file, one law.
//
// ⚠ AND IT IS SEPARATE FROM `resolveEffort` ON PURPOSE — never widen that one to take a word.
// `probe-launch-profiles` leg 11 asserts it REFUSES the legacy word `'high'`, which is what keeps
// a caller left on the retired abstract vocabulary failing loudly instead of resolving to
// something plausible. Word→rung and rung→argv are two questions; one function each.
//
// Returns { rung, inert }. `inert` is REPORTED, never folded into the null rung: where no dial
// exists the seat's declaration is ACCEPTED and said so (G-270, owner ruling), and a caller that
// could only see `rung: null` could not tell accept-and-report from a silent drop.
function effortRungFor(spec, word, specLabel, seatName = null) {
  const want = String(word || '').trim();
  if (!want) return { rung: null, inert: false };          // undeclared — the harness's own default
  const effort = spec && spec.effort;
  // ponytail: no `effort:` block reads as "no dial" rather than refusing. Ceiling: unreachable
  // from a loaded config today — every castable spec declares a block, and `validateEffort`
  // forces even a dial-less harness to say `inert: true` explicitly. Upgrade path if a spec ever
  // ships without one: make this a throw, since by then the silence would be a real gap.
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
      + `'${want}', which is not a rung of launch spec ${specLabel}'s ladder `
      + `(${rungs.map((r, i) => `${i + 1}=${r}`).join(', ') || '(empty)'}). A seat stores the `
      + 'HARNESS\'S OWN WORD, so a word from another harness\'s ladder — or one this ladder no '
      + 'longer carries — refuses HERE rather than reaching the binary. Re-cast the seat '
      + '(`rbtv-bindings set`) and re-materialize.',
      { spec: specLabel, seat: seatName, effort: want, rungs: rungs.slice() },
    );
  }
  return { rung: at + 1, inert: false };
}

module.exports = {
  bindingOf,
  catalogOf,
  declaresBinding,
  effortRungFor,
  specForSeatCast,
  specKey,
  MODEL_FLAGS,
  E_UNMAPPED_BINDING,
  E_UNCAST_SEAT,
};
