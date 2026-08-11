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
const { SpawnError } = require('./errors');

// A seat declares a cast this workspace cannot spawn — an alias where the pinned literal belongs,
// a model that left `profiles:`, a harness that was never configured. FAIL LOUD: the alternative
// is launching the caller's profile instead, which is the defect (a seat cast `claude-fable-5`
// ran `claude-sonnet-5` and the record said otherwise).
const E_UNMAPPED_BINDING = 'E_UNMAPPED_BINDING';
// Two profiles claim one (harness, model). See the ambiguity note above.
const E_AMBIGUOUS_BINDING = 'E_AMBIGUOUS_BINDING';

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

module.exports = {
  bindingOf,
  catalogOf,
  declaresBinding,
  profileForBinding,
  MODEL_FLAGS,
  E_UNMAPPED_BINDING,
  E_AMBIGUOUS_BINDING,
};
