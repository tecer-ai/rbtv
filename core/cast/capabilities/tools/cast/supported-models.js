'use strict';

// The supported models and their launch mechanics: every (harness, model, mode) row this copy of
// cast can run, carrying the harness-native model id, the effort ladder and the provider whose
// login it needs. The providers themselves (login method, key variable, credential store) are
// data in `providers.json` beside this file; a row names one by its key there.
//
// The routing columns (levels, scores, cost, image capability) live in the model catalog: the
// shipped `models.csv` beside this file, which holds at least one row for every row here, or the
// installation's own `.rbtv/config/cast/models.csv`. A row of the model catalog in force SELECTS
// its harness+model: a launch names a model that is supported (a row here) and selected, and
// `cast route` JOINS the two on harness+model, excluding a model catalog row with no row here.
// lib/model-catalog.js reads the table and holds that launch check.
//
// Readers:
//   * the launch path (lib/core.js, lib/launch.js) consumes SPECS below: `mode: cli` rows only,
//     in this file's order.
//   * lib/route.js and lib/model-catalog.js consume ROWS for the launch and provider half of each
//     joined row.
//   * lib/api.js consumes the `mode: api` rows.
//
// mode:
//   cli  launchable by `cast <harness> <model> <effort>` (a real OS process)
//   api  an API worker reached by `cast api` — routable, NOT launchable
//
// Launch-ladder provenance:
//   claude   — measured on live launches.
//   codex    — each model's `supported_reasoning_levels` in the model manifest embedded in the
//              codex binary, spot-checked against live `codex exec` runs.
//              Excluded and why: gpt-5.2 — live 400, "not supported when using
//              Codex with a ChatGPT account"; gpt-5.4, gpt-5.4-mini, codex-auto-review — manifest
//              visibility "hide". sol/terra also list an `ultra` rung above max; a 1-5 dial can
//              never reach a 6th rung, so it is left out rather than sitting here unreachable.
//   opencode — the `variants` keys in `opencode models <provider> --verbose` (what `--variant`
//              validates against). NOT ~/.cache/opencode/models.json, whose
//              `reasoning_options` disagrees. A model with no variants is inert. The k3 rows
//              are the one place `--verbose` UNDER-reports: it lists high,max, but a live
//              `opencode run --variant low` on both returns normally.
//
// One row per model line, the latest: a superseded version is deleted, not kept.

const EFFORT_FLAG = {
  claude: (e) => ['--effort', e],
  codex: (e) => ['-c', `model_reasoning_effort=${e}`],
  opencode: (e) => ['--variant', e],
};

const CLAUDE_LADDER = ['low', 'medium', 'high', 'xhigh', 'max'];

// Row fields: harness · model (the short name cast addresses) · mode · id (what the harness itself
// wants on argv) · rungs (cast's 1-5 effort ladder; [] = inert) · provider (a key of
// providers.json) · available (absent = true) · depths (an api model's own reasoning-mode ladder;
// [] = single-mode; cli rows do not use it).
const ROWS = [
  // --- claude, cli -----------------------------------------------------------------------------
  { harness: 'claude', model: 'fable-5-1', mode: 'cli', id: 'claude-fable-5-1', rungs: CLAUDE_LADDER, provider: 'claude' },
  { harness: 'claude', model: 'opus-5-5', mode: 'cli', id: 'claude-opus-5-5', rungs: CLAUDE_LADDER, provider: 'claude' },
  { harness: 'claude', model: 'sonnet-5-5', mode: 'cli', id: 'claude-sonnet-5-5', rungs: CLAUDE_LADDER, provider: 'claude' },
  { harness: 'claude', model: 'haiku-4-5', mode: 'cli', id: 'claude-haiku-4-5', rungs: [], provider: 'claude' },

  // --- codex, cli ------------------------------------------------------------------------------
  { harness: 'codex', model: 'gpt-6-astra', mode: 'cli', id: 'gpt-6-astra', rungs: CLAUDE_LADDER, provider: 'codex' },
  { harness: 'codex', model: 'gpt-6.1-sol', mode: 'cli', id: 'gpt-6.1-sol', rungs: CLAUDE_LADDER, provider: 'codex' },
  { harness: 'codex', model: 'gpt-5.6-terra', mode: 'cli', id: 'gpt-5.6-terra', rungs: CLAUDE_LADDER, provider: 'codex' },
  { harness: 'codex', model: 'gpt-6-luna', mode: 'cli', id: 'gpt-6-luna', rungs: CLAUDE_LADDER, provider: 'codex' },

  // --- opencode, cli ---------------------------------------------------------------------------
  { harness: 'opencode', model: 'glm-5.3', mode: 'cli', id: 'zai-coding-plan/glm-5.3',
    rungs: ['high', 'max'], provider: 'zai' },
  { harness: 'opencode', model: 'deepseek-v4-flash', mode: 'cli', id: 'deepseek/deepseek-v4-flash',
    rungs: ['low', 'medium', 'high', 'max'], provider: 'deepseek' },
  { harness: 'opencode', model: 'deepseek-v4-pro', mode: 'cli', id: 'deepseek/deepseek-v4-pro',
    rungs: ['low', 'medium', 'high', 'max'], provider: 'deepseek' },
  { harness: 'opencode', model: 'sakana-namazu', mode: 'cli', id: 'sakana/sakana-namazu',
    rungs: ['low', 'medium', 'high'], provider: 'sakana' },
  { harness: 'opencode', model: 'fugu-ultra', mode: 'cli', id: 'sakana/fugu-ultra',
    rungs: ['low', 'medium', 'high'], provider: 'sakana' },
  { harness: 'opencode', model: 'gemini-3.1-pro-preview', mode: 'cli', id: 'google/gemini-3.1-pro-preview',
    rungs: ['low', 'medium', 'high'], provider: 'google' },
  { harness: 'opencode', model: 'gemini-3.7-flash', mode: 'cli', id: 'google/gemini-3.7-flash',
    rungs: ['minimal', 'low', 'medium', 'high'], provider: 'google' },
  { harness: 'opencode', model: 'gemini-flash-latest', mode: 'cli', id: 'google/gemini-flash-latest',
    rungs: ['low', 'high'], provider: 'google' },
  { harness: 'opencode', model: 'grok-4.7', mode: 'cli', id: 'xai/grok-4.7',
    rungs: ['low', 'medium', 'high'], provider: 'xai' },
  { harness: 'opencode', model: 'k3', mode: 'cli', id: 'kimi-for-coding/k3',
    rungs: ['low', 'high', 'max'], provider: 'kimi' },
  { harness: 'opencode', model: 'k3-256k', mode: 'cli', id: 'kimi-for-coding/k3-256k',
    rungs: ['low', 'high', 'max'], provider: 'kimi' },

  // --- api workers, Google only (routable, never launched) -------------------------------------
  { harness: 'api', model: 'gemini-3.5-flash', mode: 'api', id: 'gemini-3.5-flash', rungs: [],
    provider: 'google', depths: ['off', 'on'] },
  // The Google image-generation worker, Nano Banana 2. `id` is the model name Google answers to on
  // generateContent; the `-preview` twin and the Pro/Lite siblings are deliberately NOT listed —
  // one image row keeps the `--caps image` short-circuit deterministic. Its models.csv twin
  // (image=Y, level L4, use=route) is what makes `cast route --caps image` return it; both files
  // carry the SAME model string or the join drops the row. No `depths`: an image model has no
  // thinking dial, so `cast api` skips the effort merge entirely.
  { harness: 'api', model: 'gemini-3.1-flash-image', mode: 'api', id: 'gemini-3.1-flash-image',
    rungs: [], provider: 'google', depths: [] },
];

// The launch table cast.js spawns from: `mode: cli` rows, in this file's order, keyed the way the
// harness itself wants the model named.
function buildSpecs() {
  const specs = {};
  for (const row of ROWS) {
    if (row.mode !== 'cli') continue;
    if (!specs[row.harness]) specs[row.harness] = {};
    specs[row.harness][row.id] = {
      short: row.model,
      effort: row.rungs.length
        ? { rungs: row.rungs.slice(), flag: EFFORT_FLAG[row.harness] }
        : { inert: true },
    };
  }
  return specs;
}

// Prefix allowlists the installer syncs into a workspace's
// `.claude/settings.local.json` `permissions.allow` so in-session CLI spawns of
// launchable harnesses are permitted. API rows declare none.
const PERMISSION_RULES = {
  claude: ['Bash(claude:*)', 'PowerShell(claude:*)'],
  codex: ['Bash(codex:*)', 'PowerShell(codex:*)'],
  opencode: ['Bash(opencode:*)', 'PowerShell(opencode:*)'],
};

module.exports = { ROWS, SPECS: buildSpecs(), EFFORT_FLAG, PERMISSION_RULES };
