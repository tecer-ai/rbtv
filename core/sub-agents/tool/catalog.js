'use strict';

// The LAUNCH half of cast's model knowledge: every (harness, model, mode) row cast can actually
// run, carrying the harness-native model id, the effort ladder and the credential it needs.
//
// The ROUTING half moved OUT 2026-08-20 (route redesign §6): levels, scores, cost, web/image
// capability now live in `models.csv` beside this file, which the owner edits without touching
// code. `cast route` JOINS the two on harness+model — a CSV row with no row here is excluded
// (route must never pick what cast cannot launch), and a row here with no CSV twin is simply
// unroutable while staying launchable by hand.
//
// Two readers:
//   * cast.js's launch path consumes SPECS below — `mode: cli` rows only, in this file's order.
//   * lib/route.js consumes ROWS for the launch/auth half of each joined pick.
//
// mode:
//   cli  launchable by `cast <harness> <model> <effort>` (a real OS process)
//   api  an API worker reached by `cast api` — routable, NOT launchable
// (The `agent-tool` mode was DELETED 2026-08-20: a caller with a native sub-agent tool substitutes
// it ITSELF when the routed model is runnable there — the sub-agents doc's rule.)
//
// Launch-ladder provenance (unchanged since 2026-08-12):
//   claude   — measured 2026-08-12.
//   codex    — each model's `supported_reasoning_levels` in the model manifest embedded in the
//              codex binary (0.147.0), spot-checked against live `codex exec` runs 2026-08-12.
//              gpt-5.5 has xhigh. Excluded and why: gpt-5.2 — live 400, "not supported when using
//              Codex with a ChatGPT account"; gpt-5.4, gpt-5.4-mini, codex-auto-review — manifest
//              visibility "hide". sol/terra also list an `ultra` rung above max; a 1-5 dial can
//              never reach a 6th rung, so it is left out rather than sitting here unreachable.
//   opencode — the `variants` keys in `opencode models <provider> --verbose` (what `--variant`
//              validates against), re-measured 2026-08-12/13/14. NOT ~/.cache/opencode/models.json,
//              whose `reasoning_options` disagrees. A model with no variants (glm-4.7, K2.7) is
//              inert. kimi rides opencode since 2026-08-14 (the `kimi` CLI is gone) — its ids are
//              opaque ("kimi-for-coding" IS K2.7 Coding), so `model` carries the generation. The k3
//              rows are the one place `--verbose` UNDER-reports: it lists high,max, but a live
//              `opencode run --variant low` on both returns normally (2026-08-14).
//
// PRUNING vs ROUTING: rows kept here that models.csv omits (gpt-5.5, glm-4.7, k2.7, k3-256k, the
// gemini/grok legacy rows) stay LAUNCHABLE — `cast codex gpt-5.5 3` still works. They just stop
// being answers `cast route` can give.

const EFFORT_FLAG = {
  claude: (e) => ['--effort', e],
  codex: (e) => ['-c', `model_reasoning_effort=${e}`],
  opencode: (e) => ['--variant', e],
};

const CLAUDE_LADDER = ['low', 'medium', 'high', 'xhigh', 'max'];
const CLI_LOGIN = { method: 'cli-login', required: true };
const ZAI_AUTH = {
  method: 'api-key', required: true, env_var: 'ZHIPU_API_KEY',
  credential_store: 'opencode', credential_store_key: 'zai-coding-plan',
};
const DEEPSEEK_OC_AUTH = {
  method: 'api-key', required: true, env_var: 'DEEPSEEK_API_KEY',
  credential_store: 'opencode', credential_store_key: 'deepseek',
};
const SAKANA_AUTH = { method: 'api-key', required: true, env_var: 'SAKANA_API_KEY' };
const GOOGLE_OC_AUTH = {
  method: 'api-key', required: true, env_var: 'GEMINI_API_KEY',
  credential_store: 'opencode', credential_store_key: 'google',
};
const XAI_OC_AUTH = {
  method: 'api-key', required: true, env_var: 'XAI_API_KEY',
  credential_store: 'opencode', credential_store_key: 'xai',
};
const KIMI_OC_AUTH = {
  method: 'api-key', required: true, env_var: 'KIMI_API_KEY',
  credential_store: 'opencode', credential_store_key: 'kimi-for-coding',
};
// The `cast api` path calls Google directly, so its key must resolve to a VALUE the runner can put
// in a header — OS env or the rbtv env_file. An opencode credential store cannot serve it, hence
// no credential_store here (unlike the opencode-carried google rows above).
const GOOGLE_API_AUTH = { method: 'api-key', required: true, env_var: 'GEMINI_API_KEY' };

// Row fields: harness · model (the short name cast addresses) · mode · id (what the harness itself
// wants on argv) · rungs (cast's 1-5 effort ladder; [] = inert) · auth · available (absent = true)
// · depths (an api model's own reasoning-mode ladder; [] = single-mode; cli rows do not use it).
const ROWS = [
  // --- claude, cli -----------------------------------------------------------------------------
  { harness: 'claude', model: 'fable-5', mode: 'cli', id: 'claude-fable-5', rungs: CLAUDE_LADDER, auth: CLI_LOGIN },
  { harness: 'claude', model: 'opus-5', mode: 'cli', id: 'claude-opus-5', rungs: CLAUDE_LADDER, auth: CLI_LOGIN },
  { harness: 'claude', model: 'sonnet-5', mode: 'cli', id: 'claude-sonnet-5', rungs: CLAUDE_LADDER, auth: CLI_LOGIN },
  { harness: 'claude', model: 'haiku-4-5', mode: 'cli', id: 'claude-haiku-4-5', rungs: [], auth: CLI_LOGIN },

  // --- codex, cli ------------------------------------------------------------------------------
  { harness: 'codex', model: 'gpt-5.6-sol', mode: 'cli', id: 'gpt-5.6-sol', rungs: CLAUDE_LADDER, auth: CLI_LOGIN },
  { harness: 'codex', model: 'gpt-5.6-terra', mode: 'cli', id: 'gpt-5.6-terra', rungs: CLAUDE_LADDER, auth: CLI_LOGIN },
  { harness: 'codex', model: 'gpt-5.6-luna', mode: 'cli', id: 'gpt-5.6-luna', rungs: CLAUDE_LADDER, auth: CLI_LOGIN },
  { harness: 'codex', model: 'gpt-5.5', mode: 'cli', id: 'gpt-5.5',
    rungs: ['low', 'medium', 'high', 'xhigh'], auth: CLI_LOGIN },

  // --- opencode, cli ---------------------------------------------------------------------------
  { harness: 'opencode', model: 'glm-5.3', mode: 'cli', id: 'zai-coding-plan/glm-5.3',
    rungs: ['high', 'max'], auth: ZAI_AUTH},
  { harness: 'opencode', model: 'glm-5.2', mode: 'cli', id: 'zai-coding-plan/glm-5.2',
    rungs: ['high', 'max'], auth: ZAI_AUTH },
  { harness: 'opencode', model: 'glm-5.2-highspeed', mode: 'cli', id: 'zai-coding-plan/glm-5.2-highspeed',
    rungs: ['high', 'max'], auth: ZAI_AUTH },
  { harness: 'opencode', model: 'deepseek-v4-flash', mode: 'cli', id: 'deepseek/deepseek-v4-flash',
    rungs: ['low', 'medium', 'high', 'max'], auth: DEEPSEEK_OC_AUTH },
  { harness: 'opencode', model: 'deepseek-v4-pro', mode: 'cli', id: 'deepseek/deepseek-v4-pro',
    rungs: ['low', 'medium', 'high', 'max'], auth: DEEPSEEK_OC_AUTH},
  { harness: 'opencode', model: 'sakana-namazu', mode: 'cli', id: 'sakana/sakana-namazu',
    rungs: ['low', 'medium', 'high'], auth: SAKANA_AUTH },
  { harness: 'opencode', model: 'fugu-ultra', mode: 'cli', id: 'sakana/fugu-ultra',
    rungs: ['low', 'medium', 'high'], auth: SAKANA_AUTH },
  { harness: 'opencode', model: 'gemini-3.1-pro-preview', mode: 'cli', id: 'google/gemini-3.1-pro-preview',
    rungs: ['low', 'medium', 'high'], auth: GOOGLE_OC_AUTH },
  // 3.7-flash REPLACED 3.6-flash here 2026-08-22, when models.csv started routing 3.7: same
  // provider, same ladder (variants read from `opencode models google --verbose` that day —
  // minimal, low, medium, high), one row for one row. The swap is why 3.6 is gone rather than
  // kept as an unrouted-but-launchable row: `cast -h`'s model table has a 50-line budget
  // (test_cast.js pins it) and adding a row without removing one breaks it.
  { harness: 'opencode', model: 'gemini-3.7-flash', mode: 'cli', id: 'google/gemini-3.7-flash',
    rungs: ['minimal', 'low', 'medium', 'high'], auth: GOOGLE_OC_AUTH },
  { harness: 'opencode', model: 'gemini-flash-latest', mode: 'cli', id: 'google/gemini-flash-latest',
    rungs: ['low', 'high'], auth: GOOGLE_OC_AUTH },
  { harness: 'opencode', model: 'grok-4.6', mode: 'cli', id: 'xai/grok-4.6',
    rungs: ['low', 'medium', 'high'], auth: XAI_OC_AUTH },
  { harness: 'opencode', model: 'grok-4.6-fast', mode: 'cli', id: 'xai/grok-4.6-fast',
    rungs: ['low', 'medium', 'high'], auth: XAI_OC_AUTH },
  { harness: 'opencode', model: 'k2.7', mode: 'cli', id: 'kimi-for-coding/kimi-for-coding', rungs: [], auth: KIMI_OC_AUTH },
  { harness: 'opencode', model: 'k2.7-highspeed', mode: 'cli', id: 'kimi-for-coding/kimi-for-coding-highspeed', rungs: [], auth: KIMI_OC_AUTH },
  { harness: 'opencode', model: 'k3', mode: 'cli', id: 'kimi-for-coding/k3',
    rungs: ['low', 'high', 'max'], auth: KIMI_OC_AUTH },
  { harness: 'opencode', model: 'k3-256k', mode: 'cli', id: 'kimi-for-coding/k3-256k',
    rungs: ['low', 'high', 'max'], auth: KIMI_OC_AUTH },

  // --- api workers, Google only (routable, never launched) -------------------------------------
  // DeepSeek and Manus api rows were DELETED 2026-08-20 (route redesign §7): DeepSeek survives via
  // its opencode cli rows above, Manus is gone entirely.
  { harness: 'api', model: 'gemini-3.5-flash', mode: 'api', id: 'gemini-3.5-flash', rungs: [],
    auth: GOOGLE_API_AUTH, depths: ['off', 'on'] },
  // The Google image-generation worker. ⚠ `model`/`id` are BLANK ON PURPOSE — the owner has not
  // picked the model id yet, and the blank matches models.csv so the route join still finds it.
  // Consequence while blank: `cast route --caps image` returns this row with an empty model, and
  // `cast api` cannot address it. Filling the id in BOTH files makes it usable; nothing else here
  // has to change. It is not marked available:false — availability stays the honest GEMINI_API_KEY
  // presence test, so the failure a caller sees is the real one.
  { harness: 'api', model: '', mode: 'api', id: '', rungs: [],
    auth: GOOGLE_API_AUTH, depths: [] },
];

// The launch table cast.js spawns from: `mode: cli` rows, in catalog order, keyed the way the
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
