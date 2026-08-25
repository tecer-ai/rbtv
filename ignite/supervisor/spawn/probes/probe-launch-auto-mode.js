'use strict';

// G-49 / r-seats-launch-auto-mode — standing per-harness probe.
// Headless argv is taken from spawn-profiles.yaml (the daemon's exec argv), never hardcoded,
// so stripping a harness-gate-off flag from the config fails this live read.
// Observed failure mode: --auto removed from opencode's exec argv (opencode then silently
// auto-rejects the out-of-cwd read and this probe goes red).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync, execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { resolveTemplateSlots } = require('../config');

const SHIPPED = path.join(__dirname, '..', '..', '..', 'envelope', 'spawn-profiles.yaml');
const HARNESSES = ['claude', 'opencode', 'codex'];
const CHEAPEST = {
  claude: 'claude-haiku-4-5',
  opencode: 'zai-coding-plan/glm-5.2',
  codex: 'gpt-5.5',
};
const TIMEOUT_MS = 120000;

function gateOffFail(harness) {
  return `${harness} out-of-cwd read auto-rejected — check the harness-gate-off flag in its exec argv (G-49 / r-seats-launch-auto-mode)`;
}

function looksLikeAuthOrSetup(text) {
  return /not (logged in|authenticated)|unauthori[sz]ed|api[_ ]key|please (run\s+\S+\s+)?(login|auth)|authentication (failed|required)|no credentials|\b401\b|not inside a trusted directory|skip-git-repo-check/i.test(text);
}

function cheapestArgv(specs, harness) {
  const model = CHEAPEST[harness];
  const spec = specs[harness] && specs[harness][model];
  if (!spec || !spec.exec || !Array.isArray(spec.exec.argv)) {
    throw new Error(`${harness}: no exec argv for cheapest model ${model} in spawn-profiles.yaml`);
  }
  return { model, argv: spec.exec.argv };
}

capture('probe-launch-auto-mode', async (lines) => {
  const specs = yaml.load(fs.readFileSync(SHIPPED, 'utf8'))['launch-specs'];
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p2-2-probe-auto-'));
  const fails = [];
  try {
    for (const harness of HARNESSES) {
      const { model, argv: rawArgv } = cheapestArgv(specs, harness);
      const home = path.join(root, harness);
      const childDir = path.join(home, 'cwd');
      fs.mkdirSync(childDir, { recursive: true });
      execFileSync('git', ['init'], { cwd: home, stdio: 'ignore', timeout: 10000 });
      const marker = `G49-MARKER-${crypto.randomBytes(8).toString('hex')}`;
      const markerPath = path.join(home, 'marker.txt');
      fs.writeFileSync(markerPath, marker);
      const sessionRef = crypto.randomUUID();
      const argv = resolveTemplateSlots(rawArgv, { workdir: childDir, session_ref: sessionRef });
      const prompt = `read the file ${markerPath} and print its exact contents`;
      lines.push(`${harness} model: ${model}`);
      lines.push(`${harness} argv: ${argv.join(' ')}`);

      const res = spawnSync(argv[0], argv.slice(1), {
        cwd: childDir,
        input: prompt,
        encoding: 'utf8',
        timeout: TIMEOUT_MS,
        maxBuffer: 8 * 1024 * 1024,
        env: process.env,
      });
      const out = `${res.stdout || ''}\n${res.stderr || ''}`;
      if (res.error && res.error.code === 'ENOENT') {
        const err = new Error(`${harness}: ${res.error.message}`);
        lines.push(`${harness}: FAIL ${err.message}`);
        fails.push(err);
        continue;
      }
      if (looksLikeAuthOrSetup(out)) {
        const err = new Error(`${harness}: ${out.trim().slice(0, 800)}`);
        lines.push(`${harness}: FAIL ${err.message}`);
        fails.push(err);
        continue;
      }
      if (!out.includes(marker)) {
        const err = new Error(gateOffFail(harness));
        lines.push(`${harness}: FAIL ${err.message}`);
        lines.push(`${harness} output: ${out.trim().slice(0, 800)}`);
        fails.push(err);
        continue;
      }
      lines.push(`${harness}: PASS`);
    }
    if (fails.length) throw fails[0];
    lines.push('result: all three harnesses read the out-of-cwd marker');
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
  }
});
