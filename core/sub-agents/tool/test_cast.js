#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const TOOL = path.join(__dirname, 'cast.js');
const SCRATCH_ROOT = '/tmp/claude-1000/-home-henri-ht-wkdir-second-brain/204266c9-ba58-4854-b838-016c8b55cc42/scratchpad';
const BASE = fs.existsSync(SCRATCH_ROOT) ? SCRATCH_ROOT : os.tmpdir();

function mkFolder(name) {
  const dir = path.join(BASE, `cast-test-${name}-${process.pid}`);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function dryRun(args) {
  const res = spawnSync('node', [TOOL, ...args, '--dry-run'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 0, `expected exit 0, got ${res.status}, stderr: ${res.stderr}`);
  return JSON.parse(res.stdout);
}

// --- module graph: every lib/ module loads, and the require graph stays acyclic ---------------
// The 2026-08-20 split turned one 2052-line file into cast.js + lib/*.js. A require cycle or a
// typo'd path is invisible to every other arm here (they only ever reach cast.js through the
// verbs they exercise), so load each module directly and in isolation.
{
  const libDir = path.join(__dirname, 'lib');
  const mods = fs.readdirSync(libDir).filter((f) => f.endsWith('.js')).sort();
  assert.ok(mods.length >= 8, `expected the split modules under lib/, found: ${mods.join(', ')}`);
  for (const m of mods) {
    const full = path.join(libDir, m);
    delete require.cache[require.resolve(full)];
    const mod = require(full);
    assert.ok(mod && Object.keys(mod).length > 0, `${m} exports nothing`);
  }
  // A require cycle does NOT throw in CommonJS and does NOT show up in the exports surface — the
  // cycle-closing module simply receives a half-built `{}` and its imported bindings come back
  // undefined, which only explodes later at a call site. So assert the invariant directly: read
  // the sibling `require('./x')` edges out of each module and prove the graph is acyclic.
  const edges = new Map(mods.map((m) => [m.replace(/\.js$/, ''), []]));
  for (const m of mods) {
    const src = fs.readFileSync(path.join(libDir, m), 'utf8');
    for (const hit of src.matchAll(/require\('\.\/([A-Za-z0-9_-]+)'\)/g)) {
      edges.get(m.replace(/\.js$/, '')).push(hit[1]);
    }
  }
  const state = new Map();
  const walk = (node, trail) => {
    if (state.get(node) === 'done') return;
    assert.ok(state.get(node) !== 'open',
      `require cycle in lib/: ${[...trail, node].join(' -> ')}`);
    state.set(node, 'open');
    for (const next of edges.get(node) || []) walk(next, [...trail, node]);
    state.set(node, 'done');
  };
  for (const node of edges.keys()) walk(node, []);
}

// claude + sonnet effort 5 -> top rung "max"
{
  const folder = mkFolder('claude-sonnet');
  const out = dryRun(['claude', 'sonnet-5', '5', folder, '-p', 'hello']);
  assert.deepStrictEqual(out.argv.slice(-2), ['--effort', 'max']);
  assert.strictEqual(out.effort_word, 'max');
}

// codex effort 5 -> clamped to gpt-5.5's top rung (4 rungs: low,medium,high,xhigh)
{
  const folder = mkFolder('codex');
  const out = dryRun(['codex', 'gpt-5.5', '5', folder, '-p', 'hello']);
  assert.ok(out.argv.includes('model_reasoning_effort=xhigh'));
  assert.strictEqual(out.effort_word, 'xhigh');
}

// kimi now rides opencode: k3 effort 1 -> its lowest rung, K2.7 carries no dial at all
{
  const folder = mkFolder('kimi');
  const out = dryRun(['opencode', 'k3', '1', folder, '-p', 'hello']);
  assert.deepStrictEqual(out.argv.slice(0, 4), ['opencode', 'run', '-m', 'kimi-for-coding/k3']);
  assert.ok(out.argv.includes('--auto'), 'headless opencode must auto-approve permission asks');
  // the title is cast's only handle on WHICH session is its own (the store is shared across seats)
  const title = out.argv[out.argv.indexOf('--title') + 1];
  assert.ok(/ \[cast:[0-9a-f]{8}\]$/.test(title ?? ''), `headless opencode must carry a unique title tag: ${title}`);
  const other = dryRun(['opencode', 'k3', '1', folder, '-p', 'hello']);
  assert.notStrictEqual(other.argv[other.argv.indexOf('--title') + 1], title,
    'two launches must not share a title tag');
  assert.strictEqual(out.effort_word, 'low');
  const k27 = dryRun(['opencode', 'k2.7', '5', folder, '-p', 'hello']);
  assert.ok(!k27.argv.includes('--variant'), 'inert K2.7 must emit no --variant');
  assert.ok(k27.argv.includes('kimi-for-coding/kimi-for-coding'), 'short name must map to the id');
}

// opencode glm-5.2 effort 1 -> its lowest rung ("high", ladder has no low/medium)
{
  const folder = mkFolder('opencode');
  const out = dryRun(['opencode', 'glm-5.2', '1', folder, '-p', 'hello']);
  assert.deepStrictEqual(out.argv.slice(-2), ['--variant', 'high']);
  assert.strictEqual(out.effort_word, 'high');
}

// launch-folder omitted -> cwd of the caller
{
  const out = dryRun(['claude', 'sonnet-5', '1', '-p', 'hi']);
  assert.strictEqual(out.cwd, process.cwd());
}

// --headed: interactive forms — no print-mode flag, prompt rides argv, stdin freed for the TTY
{
  const folder = mkFolder('headed');
  const claude = dryRun(['claude', 'sonnet-5', '3', folder, '-p', 'hi', '--headed']);
  assert.ok(!claude.argv.includes('-p'), 'headed claude must drop -p');
  assert.strictEqual(claude.argv[claude.argv.length - 1], 'hi');
  assert.strictEqual(claude.stdin_preview, null);
  assert.strictEqual(claude.headed, true);

  const codex = dryRun(['codex', 'gpt-5.5', '3', folder, '-p', 'hi', '--headed']);
  assert.ok(!codex.argv.includes('exec'), 'headed codex must drop exec');
  assert.strictEqual(codex.argv[codex.argv.length - 1], 'hi');

  const oc = dryRun(['opencode', 'glm-5.2', '3', folder, '-p', 'hi', '--headed']);
  assert.ok(!oc.argv.includes('run'), 'headed opencode must drop run');
  assert.ok(!oc.argv.includes('--auto'), 'headed opencode leaves permission asks to the human');
  assert.ok(!oc.argv.includes('--variant'), 'headed opencode TUI has no --variant');
  assert.ok(!oc.argv.includes('--title'), 'headed opencode is a human session, not a bound one');
  assert.strictEqual(oc.effort_word, null);
  assert.deepStrictEqual(oc.argv.slice(-2), ['--prompt', 'hi']);
}

// plain mode ignores a seat.md sitting in the launch-folder — that carriage moved to `cast seat`
{
  const folder = mkFolder('plain-ignores-seat');
  fs.writeFileSync(path.join(folder, 'seat.md'), '# seat descriptor\nact as X.');
  const out = dryRun(['claude', 'haiku-4-5', '1', folder, '-p', 'wake up']);
  assert.ok(!out.argv.includes('--append-system-prompt-file'));
  assert.strictEqual(out.stdin_preview, 'wake up');
}

// plain mode -s/-S: claude gets a real system-prompt flag; codex gets it prepended to the message
{
  const folder = mkFolder('plain-system');
  const out = dryRun(['claude', 'sonnet-5', '1', folder, '-p', 'hi', '-s', 'be terse']);
  assert.deepStrictEqual(out.argv.slice(out.argv.indexOf('--append-system-prompt'), out.argv.indexOf('--append-system-prompt') + 2), ['--append-system-prompt', 'be terse']);
  assert.strictEqual(out.stdin_preview, 'hi');

  const sysFile = path.join(folder, 'sys.md');
  fs.writeFileSync(sysFile, 'be VERY terse');
  const outFile = dryRun(['claude', 'sonnet-5', '1', folder, '-p', 'hi', '-S', sysFile]);
  assert.ok(outFile.argv.includes('--append-system-prompt-file'));

  const codex = dryRun(['codex', 'gpt-5.5', '1', folder, '-p', 'hi', '-S', sysFile]);
  assert.ok(codex.stdin_preview.startsWith('be VERY terse'), `expected prepended system text: ${codex.stdin_preview}`);
}

// cast seat, claude: frontmatter picks harness/model/effort; seat.md -> --append-system-prompt-file
{
  const folder = mkFolder('seat-claude');
  fs.writeFileSync(path.join(folder, 'seat.md'),
    '---\nseat: x\nharness: claude\nmodel: claude-opus-5\neffort: xhigh\n---\n# seat descriptor\nact as X.');
  const out = dryRun(['seat', folder, '-p', 'wake up']);
  assert.ok(out.argv[0] === 'claude' && out.argv.includes('claude-opus-5'));
  assert.deepStrictEqual(out.argv.slice(out.argv.indexOf('--effort'), out.argv.indexOf('--effort') + 2), ['--effort', 'xhigh']);
  const idx = out.argv.indexOf('--append-system-prompt-file');
  assert.strictEqual(out.argv[idx + 1], path.join(folder, 'seat.md'));
  assert.strictEqual(out.stdin_preview, 'wake up');
}

// cast seat, codex: no system-prompt flag — seat text rides the first message
{
  const folder = mkFolder('seat-codex');
  const seatText = '---\nharness: codex\nmodel: gpt-5.5\neffort: high\n---\n# seat descriptor\nact as Y.';
  fs.writeFileSync(path.join(folder, 'seat.md'), seatText);
  const out = dryRun(['seat', folder, '-p', 'wake up']);
  assert.ok(out.argv[0] === 'codex' && out.argv.includes('model_reasoning_effort=high'));
  assert.ok(!out.argv.includes('--append-system-prompt-file'));
  assert.ok(out.stdin_preview.startsWith(seatText), `stdin_preview did not start with seat text: ${out.stdin_preview}`);
}

// cast seat refuses a short alias in seat.md's model: — the daemon's launch-spec table takes only
// the pin VERBATIM and never resolves an alias, so a seat cast clean with the alias still died at
// first daemon seed (goal-memory-management, 2026-08-23, seat distill-ignite-memory / grok-4.6).
// task 164.
{
  const folder = mkFolder('seat-alias-refused');
  fs.writeFileSync(path.join(folder, 'seat.md'),
    '---\nharness: opencode\nmodel: grok-4.6\neffort: high\n---\n# seat descriptor\nact as Z.');
  const res = spawnSync('node', [TOOL, 'seat', folder, '--dry-run'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 2, 'seat mode must refuse a short-alias model');
  assert.ok(/pin VERBATIM/.test(res.stderr), `expected pin-verbatim refusal, got: ${res.stderr}`);

  // the pin itself still launches
  const pinned = mkFolder('seat-pin-ok');
  fs.writeFileSync(path.join(pinned, 'seat.md'),
    '---\nharness: opencode\nmodel: xai/grok-4.6\neffort: high\n---\n# seat descriptor\nact as Z.');
  const out = dryRun(['seat', pinned, '-p', 'wake up']);
  assert.ok(out.argv.includes('xai/grok-4.6'), `expected the pin on argv, got: ${out.argv}`);
}

// cast seat without -p/-f: allowed, a default wake message stands in; -s/-S refused
{
  const folder = mkFolder('seat-no-prompt');
  fs.writeFileSync(path.join(folder, 'seat.md'), '---\nharness: claude\nmodel: claude-opus-5\neffort: high\n---\nbody');
  const out = dryRun(['seat', folder]);
  assert.ok(out.stdin_preview.includes('act per your seat descriptor'), `unexpected default wake: ${out.stdin_preview}`);

  const res = spawnSync('node', [TOOL, 'seat', folder, '-s', 'nope', '--dry-run']);
  assert.strictEqual(res.status, 2, 'seat mode must refuse -s');
}

// cast seat, effort inert -> no effort argv; missing seat.md or bad rung -> exit 2
{
  const folder = mkFolder('seat-inert');
  fs.writeFileSync(path.join(folder, 'seat.md'), '---\nharness: claude\nmodel: claude-haiku-4-5\neffort: inert\n---\nbody');
  const out = dryRun(['seat', folder, '-p', 'hi']);
  assert.strictEqual(out.effort_word, null);

  const empty = mkFolder('seat-empty');
  let res = spawnSync('node', [TOOL, 'seat', empty, '-p', 'hi', '--dry-run']);
  assert.strictEqual(res.status, 2, 'missing seat.md must exit 2');

  const bad = mkFolder('seat-bad-rung');
  fs.writeFileSync(path.join(bad, 'seat.md'), '---\nharness: claude\nmodel: claude-opus-5\neffort: turbo\n---\nbody');
  res = spawnSync('node', [TOOL, 'seat', bad, '-p', 'hi', '--dry-run']);
  assert.strictEqual(res.status, 2, 'unknown effort rung must exit 2');
}

// -f FILE reads the prompt from a file
{
  const folder = mkFolder('file-prompt');
  const promptFile = path.join(folder, 'prompt.txt');
  fs.writeFileSync(promptFile, 'from a file');
  const out = dryRun(['claude', 'sonnet-5', '1', folder, '-f', promptFile]);
  assert.strictEqual(out.stdin_preview, 'from a file');
}

// -f - reads the prompt from stdin
{
  const folder = mkFolder('stdin-prompt');
  const res = spawnSync('node', [TOOL, 'claude', 'sonnet-5', '1', folder, '-f', '-', '--dry-run'], {
    encoding: 'utf8',
    input: 'piped in',
  });
  assert.strictEqual(res.status, 0, `expected exit 0, got ${res.status}, stderr: ${res.stderr}`);
  const out = JSON.parse(res.stdout);
  assert.strictEqual(out.stdin_preview, 'piped in');
}

// error paths: exit 2
{
  const res = spawnSync('node', [TOOL, 'nope', 'x', '1', BASE, '-p', 'hi', '--dry-run']);
  assert.strictEqual(res.status, 2, 'unknown harness must exit 2');
}
{
  const res = spawnSync('node', [TOOL, 'claude', 'sonnet-5', '9', BASE, '-p', 'hi', '--dry-run']);
  assert.strictEqual(res.status, 2, 'out-of-range effort must exit 2');
}
{
  const missing = path.join(BASE, 'cast-test-does-not-exist');
  const res = spawnSync('node', [TOOL, 'claude', 'sonnet-5', '1', missing, '-p', 'hi', '--dry-run']);
  assert.strictEqual(res.status, 2, 'missing launch-folder must exit 2');
}

// -p and -f together: refused
{
  const res = spawnSync('node', [TOOL, 'claude', 'sonnet-5', '1', BASE, '-p', 'hi', '-f', '/dev/null', '--dry-run']);
  assert.strictEqual(res.status, 2, '-p and -f together must exit 2');
}

// neither -p nor -f: refused
{
  const res = spawnSync('node', [TOOL, 'claude', 'sonnet-5', '1', BASE, '--dry-run']);
  assert.strictEqual(res.status, 2, 'no prompt source must exit 2');
}

// unknown flag: refused, names the flag
{
  const res = spawnSync('node', [TOOL, 'claude', 'sonnet-5', '1', BASE, '-p', 'hi', '--bogus'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 2, 'unknown flag must exit 2');
  assert.ok(res.stderr.includes('--bogus'), `error should name the unknown flag: ${res.stderr}`);
}

// unknown model: refused, suggests the closest known model
{
  const res = spawnSync('node', [TOOL, 'claude', 'claude-sonet-5', '1', BASE, '-p', 'hi', '--dry-run'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 2, 'unknown model must exit 2');
  assert.ok(res.stderr.includes('did you mean'), `error should suggest a model: ${res.stderr}`);
  assert.ok(res.stderr.includes('sonnet-5'), `suggestion should name the close model: ${res.stderr}`);
}

// per-verb --help: exit 0, prints that verb's usage; a prompt that is literally "-h" is not help
{
  for (const verb of ['route', 'monitor', 'sessions', 'doctor', 'list', 'seat', 'resume', 'api']) {
    for (const flag of ['-h', '--help']) {
      const res = spawnSync('node', [TOOL, verb, flag], { encoding: 'utf8' });
      assert.strictEqual(res.status, 0, `cast ${verb} ${flag} must exit 0: ${res.stderr}`);
      assert.ok(new RegExp(`usage: cast ${verb}\\b`, 'i').test(res.stdout),
        `cast ${verb} ${flag} must print its own usage, got: ${res.stdout}`);
    }
  }
  // not help: -h carried as a value alongside other args must still reach the verb
  const res = spawnSync('node', [TOOL, 'seat', '.', '-p', '-h', '--dry-run'], { encoding: 'utf8' });
  assert.ok(!/^usage: cast seat/.test(res.stdout), `"-h" as prompt text must not print usage: ${res.stdout}`);
}

// -h: exit 0, <=50 lines (one screen; raised from 40 for resume/sessions, from 44 for monitor, from 47 for route), mentions every SPECS model id
{
  const res = spawnSync('node', [TOOL, '-h'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 0, 'cast -h must exit 0');
  const lines = res.stdout.split('\n').filter((l) => l.length > 0);
  assert.ok(lines.length <= 50, `help must be <=50 lines, got ${lines.length}`);
  // enumerate models from the tool's own inventory, never by re-parsing its source
  const inv = JSON.parse(spawnSync('node', [TOOL, 'list', '--json'], { encoding: 'utf8' }).stdout);
  const shorts = Object.values(inv).flatMap((models) => Object.keys(models));
  assert.ok(shorts.length > 10, `sanity: expected the full inventory, got ${shorts.length}`);
  for (const short of shorts) {
    assert.ok(res.stdout.includes(` ${short} `), `help text missing model: ${short}`);
  }
  for (const id of ['claude-opus-5', 'zai-coding-plan/glm-5.2', 'kimi-for-coding/k3']) {
    assert.ok(!res.stdout.includes(id), `help text must print short names only, found long id: ${id}`);
  }
  // every model row names what each effort number resolves to, clamping included
  assert.ok(res.stdout.includes('1=low 2=medium 3=high 4=xhigh 5=max'), 'claude effort map missing');
  assert.ok(res.stdout.includes('1=high 2-5=max'), 'glm-5.2 clamped effort map missing');
  assert.ok(/haiku-4-5 +\(no dial/.test(res.stdout), 'inert ladder must say so');
}

// doctor: exits 0, --json parses
{
  const res = spawnSync('node', [TOOL, 'doctor'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 0, 'doctor must exit 0');
}
{
  const res = spawnSync('node', [TOOL, 'doctor', '--json'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 0, 'doctor --json must exit 0');
  // doctor delegates to `acct doctor`: harnesses installed + providers enabled, one view
  const parsed = JSON.parse(res.stdout);
  const h = parsed.harnesses;
  assert.ok(h && 'claude' in h && 'codex' in h && 'opencode' in h);
  assert.ok(parsed.providers && 'claude' in parsed.providers);
}

// list --json: parses and matches SPECS keys
{
  const res = spawnSync('node', [TOOL, 'list', '--json'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 0, 'list --json must exit 0');
  const parsed = JSON.parse(res.stdout);
  assert.deepStrictEqual(Object.keys(parsed).sort(), ['claude', 'codex', 'opencode'].sort());
  assert.ok(Array.isArray(parsed.claude['sonnet-5']));
  assert.deepStrictEqual(parsed.claude['haiku-4-5'], []);
}

// a model opencode gives no variants for (k2.7) is inert: any effort, no --variant argv
{
  const folder = mkFolder('opencode-inert');
  const out = dryRun(['opencode', 'k2.7', '5', folder, '-p', 'hello']);
  assert.ok(!out.argv.includes('--variant'), `inert model must emit no --variant: ${out.argv}`);
  assert.strictEqual(out.effort_word, null);
}

// cast resume: per-harness argv, explicit id vs `last`, prompt on stdin
{
  const folder = mkFolder('resume');
  const byId = dryRun(['resume', 'claude', 'abc-123', folder, '-p', 'follow up']);
  assert.deepStrictEqual(byId.argv, ['claude', '-p', '--resume', 'abc-123', '--permission-mode', 'bypassPermissions']);
  assert.strictEqual(byId.cwd, folder);
  assert.strictEqual(byId.stdin_preview, 'follow up');

  const last = dryRun(['resume', 'claude', 'last', folder, '-p', 'hi']);
  assert.ok(last.argv.includes('--continue') && !last.argv.includes('--resume'));

  const codex = dryRun(['resume', 'codex', 'last', folder, '-p', 'hi']);
  assert.deepStrictEqual(codex.argv.slice(0, 4), ['codex', 'exec', 'resume', '--last']);
  assert.ok(codex.argv.includes('sandbox_mode=danger-full-access'));
  assert.ok(codex.argv.includes('approval_policy=never'));

  const oc = dryRun(['resume', 'opencode', 'ses_x1', folder, '-p', 'hi']);
  assert.deepStrictEqual(oc.argv, ['opencode', 'run', '-s', 'ses_x1', '--auto']);
  const ocLast = dryRun(['resume', 'opencode', 'last', folder, '-p', 'hi']);
  assert.deepStrictEqual(ocLast.argv, ['opencode', 'run', '-c', '--auto']);
}

// cast resume: launch-folder omitted -> caller's cwd
{
  const out = dryRun(['resume', 'claude', 'last', '-p', 'hi']);
  assert.strictEqual(out.cwd, process.cwd());
}

// cast resume refusals: --headed, -s, missing prompt, unknown harness
{
  const folder = mkFolder('resume-refusals');
  for (const args of [
    ['resume', 'claude', 'last', folder, '-p', 'hi', '--headed'],
    ['resume', 'claude', 'last', folder, '-p', 'hi', '-s', 'nope'],
    ['resume', 'claude', 'last', folder],
    ['resume', 'nope', 'last', folder, '-p', 'hi'],
  ]) {
    const res = spawnSync('node', [TOOL, ...args, '--dry-run']);
    assert.strictEqual(res.status, 2, `must exit 2: cast ${args.join(' ')}`);
  }
}

// cast sessions: reads claude + codex stores under $HOME, folder-filtered, --json shape
{
  const folder = mkFolder('sessions');
  const home = mkFolder('sessions-home');
  const enc = folder.replace(/[^a-zA-Z0-9]/g, '-');
  fs.mkdirSync(path.join(home, '.claude', 'projects', enc), { recursive: true });
  fs.writeFileSync(path.join(home, '.claude', 'projects', enc, 'aaaa-bbbb.jsonl'), [
    JSON.stringify({ type: 'mode', mode: 'normal' }),
    JSON.stringify({ type: 'user', message: { role: 'user', content: '<system-reminder>injected</system-reminder>' } }),
    JSON.stringify({ type: 'user', message: { role: 'user', content: 'fix the   parser bug' } }),
    '',
  ].join('\n'));

  const day = path.join(home, '.codex', 'sessions', '2026', '08', '14');
  fs.mkdirSync(day, { recursive: true });
  const meta = { timestamp: '2026-08-14T12:00:00.000Z', type: 'session_meta', payload: { id: 'cx-1', cwd: folder } };
  const userMsg = { type: 'response_item', payload: { type: 'message', role: 'user', content: [{ type: 'input_text', text: 'x'.repeat(80) }] } };
  fs.writeFileSync(path.join(day, 'rollout-1.jsonl'), `${JSON.stringify(meta)}\n${JSON.stringify(userMsg)}\nrest\n`);
  const other = { timestamp: '2026-08-14T13:00:00.000Z', type: 'session_meta', payload: { id: 'cx-2', cwd: '/elsewhere' } };
  fs.writeFileSync(path.join(day, 'rollout-2.jsonl'), `${JSON.stringify(other)}\n`);

  // PATH holds node only, so the opencode shell-out fails fast to an empty list
  const res = spawnSync('node', [TOOL, 'sessions', folder, '--json'], {
    encoding: 'utf8', env: { ...process.env, HOME: home, PATH: path.dirname(process.execPath) },
  });
  assert.strictEqual(res.status, 0, `sessions must exit 0, stderr: ${res.stderr}`);
  const rows = JSON.parse(res.stdout);
  const ids = rows.map((r) => `${r.harness}:${r.id}`).sort();
  assert.deepStrictEqual(ids, ['claude:aaaa-bbbb', 'codex:cx-1'], `wrong rows: ${res.stdout}`);
  const byHarness = Object.fromEntries(rows.map((r) => [r.harness, r]));
  assert.strictEqual(byHarness.claude.label, 'fix the parser bug', 'claude label: injected <...> block skipped, whitespace collapsed');
  assert.strictEqual(byHarness.codex.label, `${'x'.repeat(59)}…`, 'codex label: truncated at 60 with ellipsis');

  // single-harness form filters to that store
  const onlyCodex = spawnSync('node', [TOOL, 'sessions', 'codex', folder, '--json'], {
    encoding: 'utf8', env: { ...process.env, HOME: home },
  });
  assert.deepStrictEqual(JSON.parse(onlyCodex.stdout).map((r) => r.id), ['cx-1']);

  // an unknown harness is refused, not silently empty
  const nope = spawnSync('node', [TOOL, 'sessions', 'nope', folder]);
  assert.strictEqual(nope.status, 2, 'sessions on an unknown harness must exit 2');
}

// launch handle: one stderr line + one registry row, minted claude session in argv, none on dry-run
{
  const folder = mkFolder('handle');
  const home = mkFolder('handle-home');
  // a launch that fails to spawn still emits the handle first (emitted before the spawn)
  const res = spawnSync('node', [TOOL, 'claude', 'haiku-4-5', '1', folder, '-p', 'hi'], {
    encoding: 'utf8', env: { ...process.env, HOME: home, PATH: path.dirname(process.execPath) },
  });
  const line = res.stderr.split('\n').find((l) => l.startsWith('cast: handle '));
  assert.ok(line, `no handle line on stderr: ${res.stderr}`);
  const h = JSON.parse(line.slice('cast: handle '.length));
  assert.strictEqual(h.harness, 'claude');
  assert.strictEqual(h.model, 'haiku-4-5');
  assert.strictEqual(h.folder, folder);
  assert.ok(Number.isInteger(h.pid) && Number.isInteger(h.start) && h.start > 0, `pid/start not pinned: ${line}`);
  assert.ok(/^[0-9a-f-]{36}$/.test(h.session), `claude session must be a minted uuid: ${h.session}`);
  assert.strictEqual(h.transcript,
    path.join(home, '.claude', 'projects', folder.replace(/[^a-zA-Z0-9]/g, '-'), `${h.session}.jsonl`));
  assert.ok(h.t0 > 0 && h.t0 <= Date.now());

  const rows = fs.readFileSync(path.join(home, '.cast', 'handles.jsonl'), 'utf8')
    .split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].session, h.session);

  // the minted id rides argv; dry-run emits neither handle line nor registry row
  const dry = spawnSync('node', [TOOL, 'claude', 'haiku-4-5', '1', folder, '-p', 'hi', '--dry-run'], {
    encoding: 'utf8', env: { ...process.env, HOME: mkFolder('handle-dry-home') },
  });
  assert.ok(!dry.stderr.includes('cast: handle'), `dry-run must emit no handle: ${dry.stderr}`);
  assert.ok(JSON.parse(dry.stdout).argv.includes('--session-id'), 'claude launch must mint --session-id');
  // headed claude and the other harnesses carry no minted session
  assert.ok(!dryRun(['claude', 'sonnet-5', '1', folder, '-p', 'hi', '--headed']).argv.includes('--session-id'));
  assert.ok(!dryRun(['codex', 'gpt-5.5', '1', folder, '-p', 'hi']).argv.includes('--session-id'));
}

// codex reader drops subagent rollouts; opencode reader returns [] on an absent store
{
  const folder = mkFolder('readers');
  const home = mkFolder('readers-home');
  const day = path.join(home, '.codex', 'sessions', '2026', '08', '14');
  fs.mkdirSync(day, { recursive: true });
  const meta = (id, extra) => JSON.stringify({
    timestamp: '2026-08-14T12:00:00.000Z', type: 'session_meta', payload: { id, cwd: folder, ...extra },
  });
  fs.writeFileSync(path.join(day, 'rollout-user.jsonl'), `${meta('cx-user', { thread_source: 'user' })}\n`);
  fs.writeFileSync(path.join(day, 'rollout-sub.jsonl'), `${meta('cx-sub', { thread_source: 'subagent' })}\n`);
  fs.writeFileSync(path.join(day, 'rollout-old.jsonl'), `${meta('cx-old', {})}\n`); // pre-field rollout

  const res = spawnSync('node', [TOOL, 'sessions', folder, '--json'], {
    encoding: 'utf8',
    env: { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') },
  });
  assert.strictEqual(res.status, 0, `sessions must exit 0, stderr: ${res.stderr}`);
  const ids = JSON.parse(res.stdout).map((r) => r.id).sort();
  assert.deepStrictEqual(ids, ['cx-old', 'cx-user'], `subagent rollout must be filtered out: ${res.stdout}`);
  assert.ok(!res.stderr.includes('unreadable'), 'an absent opencode store is silent, not an error');
}

// cast monitor: roster drops dead pids, --watch fires STALL on a live-but-frozen job
{
  const folder = mkFolder('monitor');
  const home = mkFolder('monitor-home');
  const enc = folder.replace(/[^a-zA-Z0-9]/g, '-');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });

  // an absent registry is not an error: empty roster, and --watch exits 0 at once
  assert.strictEqual(monitor(['--json']).stdout.trim(), '[]', 'absent registry -> empty roster');
  const noReg = monitor(['--watch', '--poll', '1']);
  assert.strictEqual(noReg.status, 0, 'no live rows must exit 0');
  assert.strictEqual(noReg.stdout, '', 'watch must be silent with nothing to report');

  // a live process we own, with a stale transcript -> STALLED
  const sleeper = require('child_process').spawn('sleep', ['300'], { detached: true, stdio: 'ignore' });
  sleeper.unref();
  try {
    const start = Number(fs.readFileSync(`/proc/${sleeper.pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    const session = '11111111-2222-3333-4444-555555555555';
    const transcript = path.join(home, '.claude', 'projects', enc, `${session}.jsonl`);
    fs.mkdirSync(path.dirname(transcript), { recursive: true });
    fs.writeFileSync(transcript, '{}\n');
    const stale = Date.now() - 3600_000;
    fs.utimesSync(transcript, stale / 1000, stale / 1000);

    const row = (over) => JSON.stringify({
      pid: sleeper.pid, start, harness: 'claude', model: 'haiku-4-5', session,
      folder, transcript, t0: Date.now() - 3600_000, ...over,
    });
    const dead = JSON.stringify({
      pid: 999999, start: 12345, harness: 'claude', model: 'haiku-4-5', session: 'dead',
      folder, transcript: null, t0: Date.now(), });
    fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'), `${dead}\n${row()}\n`);

    // roster: the dead pid is gone, the live one is STALLED (transcript an hour old)
    const rows = JSON.parse(monitor(['--json']).stdout);
    assert.strictEqual(rows.length, 1, `dead pid must drop from the roster: ${JSON.stringify(rows)}`);
    assert.strictEqual(rows[0].pid, sleeper.pid);
    assert.strictEqual(rows[0].state, 'STALLED');
    assert.ok(rows[0].progress_age_s >= 3500, `progress age should be ~1h: ${rows[0].progress_age_s}`);
    assert.strictEqual(monitor([]).status, 0, 'roster always exits 0');

    // --folder filters by prefix
    assert.strictEqual(JSON.parse(monitor(['--json', '--folder', BASE]).stdout).length, 1);
    assert.strictEqual(JSON.parse(monitor(['--json', '--folder', '/nowhere']).stdout).length, 0);

    // --watch fires the STALL line and exits 3
    const watch = monitor(['--watch', '--stall', '60', '--poll', '1']);
    assert.strictEqual(watch.status, 3, `stall must exit 3, got ${watch.status}: ${watch.stdout}`);
    assert.ok(watch.stdout.startsWith(`STALL ${sleeper.pid} claude ${session} ${folder} alive=`),
      `unexpected stall line: ${watch.stdout}`);
    assert.ok(/progress-age=\d+s desc=\d+ cpu\+\d+ io\+\d+ out=(-|\d+)$/m.test(watch.stdout),
      `stall line shape: ${watch.stdout}`);
    // owner 2026-08-22: the no-kill rule ships in the OUTPUT, not only in orchestrator prose
    assert.ok(watch.stdout.includes('ADVISORY, not authority'),
      `stall burst must carry the advisory: ${watch.stdout}`);
    assert.ok(watch.stdout.indexOf('STALL ') < watch.stdout.indexOf('ADVISORY'),
      `advisory must TRAIL the events, never lead: ${watch.stdout}`);

    // a fresh transcript is healthy: watch stays silent, so it must be killed rather than exit
    fs.utimesSync(transcript, Date.now() / 1000, Date.now() / 1000);
    assert.strictEqual(monitor(['--json'])
      .stdout.includes('"state":"ok"'), true, 'fresh progress -> ok');

    // NO-SIGNAL: transcript absent and past --grace
    fs.unlinkSync(transcript);
    const noSig = monitor(['--watch', '--grace', '1', '--poll', '1']);
    assert.strictEqual(noSig.status, 3, 'dead-at-launch must exit 3');
    assert.ok(noSig.stdout.startsWith(`NO-SIGNAL ${sleeper.pid} claude ${folder} alive=`),
      `unexpected no-signal line: ${noSig.stdout}`);
    // ...but not before --grace elapses
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'), `${row({ t0: Date.now() })}\n`);
    const young = monitor(['--watch', '--grace', '600', '--poll', '1'], { timeout: 2500 });
    assert.strictEqual(young.stdout, '', `within grace must stay silent: ${young.stdout}`);
    // it must have been STILL POLLING when the timeout killed it — not exited quietly
    assert.strictEqual(young.signal, 'SIGTERM', `watch must keep polling within grace, got exit ${young.status}`);
  } finally {
    process.kill(sleeper.pid, 'SIGKILL'); // our own child, spawned above
  }

  // usage errors
  for (const args of [['--bogus'], ['--stall'], ['--stall', 'soon'], ['--poll', '0'], ['--watch', '--json']]) {
    assert.strictEqual(monitor(args).status, 2, `must exit 2: cast monitor ${args.join(' ')}`);
  }
  for (const args of [['--deadline'], ['--deadline', 'soon']]) {
    assert.strictEqual(monitor(args).status, 2, `must exit 2: cast monitor ${args.join(' ')}`);
  }
}

// cast monitor: a stale harness signal with a live working subtree is SUSPECT, never STALL —
// the 2026-08-19 false positive (seat blocked on a probe suite writing to a file, stdout silent)
{
  const folder = mkFolder('monitor-busy');
  const home = mkFolder('monitor-busy-home');
  const enc = folder.replace(/[^a-zA-Z0-9]/g, '-');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });

  const scratch = path.join(folder, 'suite-output.txt');
  const outFd = fs.openSync(scratch, 'w');
  const busy = require('child_process').spawn('bash',
    ['-c', 'while :; do echo working; done'],
    { detached: true, stdio: ['ignore', outFd, 'ignore'] });
  busy.unref();
  fs.closeSync(outFd);
  try {
    const start = Number(fs.readFileSync(`/proc/${busy.pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    const session = '99999999-8888-7777-6666-555555555555';
    const transcript = path.join(home, '.claude', 'projects', enc, `${session}.jsonl`);
    fs.mkdirSync(path.dirname(transcript), { recursive: true });
    fs.writeFileSync(transcript, '{}\n');
    const stale = Date.now() - 3600_000;
    fs.utimesSync(transcript, stale / 1000, stale / 1000);
    fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'), `${JSON.stringify({
      pid: busy.pid, start, harness: 'claude', model: 'haiku-4-5', session,
      folder, transcript, t0: Date.now() - 3600_000,
    })}\n`);

    // roster: harness signal an hour stale, but the subtree is alive -> SUSPECT, not STALLED
    const rows = JSON.parse(monitor(['--json']).stdout);
    assert.strictEqual(rows.length, 1, `busy job must be on the roster: ${JSON.stringify(rows)}`);
    assert.strictEqual(rows[0].state, 'SUSPECT', `live subtree must hold SUSPECT: ${JSON.stringify(rows)}`);

    // --watch must keep polling (killed by our timeout), never exit 3 on the working subtree
    const watch = monitor(['--watch', '--stall', '2', '--poll', '1'], { timeout: 6000 });
    assert.strictEqual(watch.stdout, '', `busy subtree must not fire an event: ${watch.stdout}`);
    assert.strictEqual(watch.signal, 'SIGTERM', `watch must still be polling, got exit ${watch.status}`);
  } finally {
    try { process.kill(-busy.pid, 'SIGKILL'); } catch { process.kill(busy.pid, 'SIGKILL'); }
  }
}

// cast monitor: opencode ancestor-directory + per-job t0 bind (not newest-across-the-plan)
{
  const plan = mkFolder('oc-plan');
  const seatA = path.join(plan, 'seats', 'a');
  const seatB = path.join(plan, 'seats', 'b');
  const orphan = mkFolder('oc-orphan');
  fs.mkdirSync(seatA, { recursive: true });
  fs.mkdirSync(seatB, { recursive: true });
  const home = mkFolder('oc-monitor-home');
  const xdg = path.join(home, 'xdg');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: xdg };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });

  const writeOcDb = (rows) => {
    const dbPath = path.join(xdg, 'opencode', 'opencode.db');
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    try { fs.unlinkSync(dbPath); } catch { /* first write */ }
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(dbPath);
    db.exec('create table session (id text primary key, directory text not null, parent_id text,'
      + ' title text, time_created integer not null, time_updated integer not null)');
    const ins = db.prepare(
      'insert into session (id, directory, parent_id, title, time_created, time_updated) values (?,?,?,?,?,?)',
    );
    for (const r of rows) {
      ins.run(r.id, r.directory, r.parent_id ?? null, r.title ?? '', r.time_created, r.time_updated);
    }
    db.close();
  };
  const ageOc = (id, timeUpdated) => {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(path.join(xdg, 'opencode', 'opencode.db'));
    db.prepare('update session set time_updated = ? where id = ?').run(timeUpdated, id);
    db.close();
  };

  const spawnSleeper = () => {
    const s = require('child_process').spawn('sleep', ['300'], { detached: true, stdio: 'ignore' });
    s.unref();
    const start = Number(fs.readFileSync(`/proc/${s.pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    return { pid: s.pid, start, kill: () => process.kill(s.pid, 'SIGKILL') };
  };
  const a = spawnSleeper();
  const b = spawnSleeper();
  const c = spawnSleeper();
  try {
    const now = Date.now();
    const t0a = now - 2500;
    const t0b = now - 800;
    // tags bind each handle to its OWN session row (never by nearest time_created) — same identity
    // mechanic launch.js's `--title` gives every headless opencode run.
    const tagA = 'a [cast:aaaaaaaa]';
    const tagB = 'b [cast:bbbbbbbb]';
    const tagC = 'c [cast:cccccccc]';
    const handle = (job, folder, t0, tag) => JSON.stringify({
      pid: job.pid, start: job.start, harness: 'opencode', model: 'glm-5.2', session: null,
      tag, folder, transcript: null, t0,
    });
    fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'),
      `${handle(a, seatA, t0a, tagA)}\n${handle(b, seatB, t0b, tagB)}\n`);

    writeOcDb([
      { id: 'ses_a', directory: plan, title: tagA, time_created: t0a + 20, time_updated: now },
      { id: 'ses_b', directory: plan, title: tagB, time_created: t0b + 20, time_updated: now },
      { id: 'ses_child', directory: plan, parent_id: 'ses_a', time_created: t0a + 40, time_updated: now },
      { id: 'ses_nested', directory: path.join(plan, 'seats', 'a', 'nested'), time_created: now, time_updated: now },
    ]);

    // both live seats bind their own ancestor row → ok, not NO-SIGNAL
    const roster = JSON.parse(monitor(['--json']).stdout);
    assert.strictEqual(roster.length, 2, `expected 2 live opencode jobs: ${JSON.stringify(roster)}`);
    assert.ok(roster.every((r) => r.state === 'ok'), `both must be ok: ${JSON.stringify(roster)}`);
    assert.ok(roster.every((r) => r.progress_age_s !== null), `signal must resolve: ${JSON.stringify(roster)}`);

    // age only ses_b: that handle leaves ok (SUSPECT — launched <2*poll ago, so the one-shot
    // confirm window still holds terminal STALLED back), the other stays ok; distinct ages
    // prove no shared bind
    ageOc('ses_b', now - 3600_000);
    const aged = JSON.parse(monitor(['--json']).stdout);
    const byPid = Object.fromEntries(aged.map((r) => [r.pid, r]));
    assert.strictEqual(byPid[a.pid].state, 'ok', `fresh row must stay ok: ${JSON.stringify(aged)}`);
    assert.strictEqual(byPid[b.pid].state, 'SUSPECT', `aged row must leave ok: ${JSON.stringify(aged)}`);
    assert.ok(byPid[a.pid].progress_age_s !== byPid[b.pid].progress_age_s,
      `two handles must not share one row: ${JSON.stringify(aged)}`);
    assert.ok(byPid[b.pid].progress_age_s >= 3500, `stale age ~1h: ${byPid[b.pid].progress_age_s}`);

    const watchStall = monitor(['--watch', '--stall', '60', '--poll', '1']);
    assert.strictEqual(watchStall.status, 3, `stall must exit 3: ${watchStall.stdout}`);
    assert.ok(watchStall.stdout.startsWith(`STALL ${b.pid} opencode - ${seatB} alive=`),
      `stall must name only the stale pid: ${watchStall.stdout}`);
    assert.ok(!watchStall.stdout.includes(String(a.pid)),
      `fresh pid must not appear on STALL: ${watchStall.stdout}`);

    // restore ses_b; a third handle with no matching tagged row past --grace is NO-SIGNAL alone
    ageOc('ses_b', Date.now());
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'),
      `${handle(a, seatA, t0a, tagA)}\n${handle(b, seatB, t0b, tagB)}\n`
      + `${handle(c, orphan, now - 10_000, tagC)}\n`);
    const watchNo = monitor(['--watch', '--grace', '1', '--poll', '1']);
    assert.strictEqual(watchNo.status, 3, `no-signal must exit 3: ${watchNo.stdout}`);
    assert.ok(watchNo.stdout.startsWith(`NO-SIGNAL ${c.pid} opencode ${orphan} alive=`),
      `no-signal must name only the orphan pid: ${watchNo.stdout}`);
    assert.ok(!watchNo.stdout.includes(String(a.pid)) && !watchNo.stdout.includes(String(b.pid)),
      `healthy pids must stay silent: ${watchNo.stdout}`);

    // sessions: seat folder sees the plan-root row; plan exact-match works; a parent does not dump descendants
    const sessions = (folder) => JSON.parse(spawnSync('node', [TOOL, 'sessions', 'opencode', folder, '--json'], {
      encoding: 'utf8', env,
    }).stdout).map((r) => r.id).sort();
    assert.deepStrictEqual(sessions(seatA), ['ses_a', 'ses_b']);
    assert.deepStrictEqual(sessions(plan), ['ses_a', 'ses_b']);
    assert.deepStrictEqual(sessions(path.dirname(plan)), []);
    const scratch = mkFolder('oc-scratch-inside');
    writeOcDb([{ id: 'ses_scratch', directory: scratch, time_created: now, time_updated: now }]);
    assert.deepStrictEqual(sessions(scratch), ['ses_scratch']);
  } finally {
    for (const s of [a, b, c]) {
      try { s.kill(); } catch { /* already gone */ }
    }
  }
}

// cast monitor --watch: ENDED + exit 4 when a job this watch has seen disappears
{
  const folder = mkFolder('monitor-ended');
  const home = mkFolder('monitor-ended-home');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });
  // Orphan the sleeper (setsid + background) so a kill REALLY clears /proc. A killed CHILD of this
  // suite lingers as a zombie — we are blocked in spawnSync and cannot reap it — and the liveness
  // guard would rightly still see it. Departure MUST be a real death: dropping the registry row
  // instead is the false positive the guard exists to suppress (a pruned row is not a dead job).
  const spawnSleeper = () => {
    const out = require('child_process').execFileSync('setsid',
      ['bash', '-c', 'sleep 300 </dev/null >/dev/null 2>&1 & echo $!'], { encoding: 'utf8' });
    const pid = Number(out.trim());
    const start = Number(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    return { pid, start, kill: () => { try { process.kill(pid, 'SIGKILL'); } catch { /* gone */ } } };
  };
  const sleeper = spawnSleeper();
  try {
    const start = sleeper.start;
    const handles = path.join(home, '.cast', 'handles.jsonl');
    fs.mkdirSync(path.dirname(handles), { recursive: true });
    fs.writeFileSync(handles, `${JSON.stringify({
      pid: sleeper.pid, start, harness: 'claude', model: 'haiku-4-5', session: null,
      folder, transcript: null, t0: Date.now(),
    })}\n`);
    // A REAL death: the registry row stays put and liveJobs drops it because /proc no longer
    // carries that pid+starttime. This is what ENDED must key on.
    const drop = require('child_process').spawn('bash',
      ['-c', `sleep 2; kill -9 ${sleeper.pid}`], { detached: true, stdio: 'ignore' });
    drop.unref();
    const watch = monitor(['--watch', '--poll', '1', '--grace', '600', '--stall', '600'],
      { timeout: 8000 });
    assert.strictEqual(watch.status, 4, `ENDED must exit 4, got ${watch.status}: ${watch.stdout}`);
    assert.ok(watch.stdout.startsWith(`ENDED ${sleeper.pid} claude ${folder} alive=`),
      `unexpected ENDED line: ${watch.stdout}`);
    assert.ok(/last-state=\S+$/m.test(watch.stdout), `ENDED line shape: ${watch.stdout}`);
    assert.ok(watch.stdout.includes('ADVISORY, not authority'),
      `ENDED burst must carry the advisory: ${watch.stdout}`);
  } finally {
    try { process.kill(sleeper.pid, 'SIGKILL'); } catch { /* already gone */ }
  }
}

// cast monitor --watch: ENDED fires once and does not re-fire (W3)
{
  const folder = mkFolder('monitor-ended-once');
  const home = mkFolder('monitor-ended-once-home');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });
  // Orphan the sleeper (setsid + background) so a kill REALLY clears /proc. A killed CHILD of this
  // suite lingers as a zombie — we are blocked in spawnSync and cannot reap it — and the liveness
  // guard would rightly still see it. Departure MUST be a real death: dropping the registry row
  // instead is the false positive the guard exists to suppress (a pruned row is not a dead job).
  const spawnSleeper = () => {
    const out = require('child_process').execFileSync('setsid',
      ['bash', '-c', 'sleep 300 </dev/null >/dev/null 2>&1 & echo $!'], { encoding: 'utf8' });
    const pid = Number(out.trim());
    const start = Number(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    return { pid, start, kill: () => { try { process.kill(pid, 'SIGKILL'); } catch { /* gone */ } } };
  };
  const a = spawnSleeper();
  const b = spawnSleeper();
  try {
    const handle = (job) => JSON.stringify({
      pid: job.pid, start: job.start, harness: 'claude', model: 'haiku-4-5', session: null,
      folder, transcript: null, t0: Date.now(),
    });
    const handles = path.join(home, '.cast', 'handles.jsonl');
    fs.mkdirSync(path.dirname(handles), { recursive: true });
    fs.writeFileSync(handles, `${handle(a)}\n${handle(b)}\n`);
    const drop = require('child_process').spawn('bash',
      ['-c', `sleep 2; kill -9 ${a.pid}`], { detached: true, stdio: 'ignore' });
    drop.unref();
    const watch = monitor(['--watch', '--poll', '1', '--grace', '600', '--stall', '600'],
      { timeout: 5500 });
    assert.strictEqual(watch.signal, 'SIGTERM',
      `watch must keep polling after one ENDED, got exit ${watch.status}: ${watch.stdout}`);
    const ended = watch.stdout.split('\n').filter((l) => l.startsWith('ENDED '));
    assert.strictEqual(ended.length, 1, `ENDED must fire once, got: ${watch.stdout}`);
    assert.ok(ended[0].startsWith(`ENDED ${a.pid} claude ${folder} alive=`),
      `ENDED must name the dead pid: ${ended[0]}`);
    assert.ok(!watch.stdout.includes(String(b.pid)),
      `live pid must stay silent: ${watch.stdout}`);
  } finally {
    a.kill();
    b.kill();
  }
}

// cast monitor --watch: a PRUNED registry row is NOT a death — no ENDED while the process lives.
// Regression pin for the D1 blocker: emitHandle prunes every row older than HANDLE_TTL_MS on each
// launch, and liveJobs returns [] on ANY read failure. Keying ENDED on row-absence told an
// orchestrator "already gone" about a job still burning tokens — the 2026-08-22 failure inverted.
{
  const folder = mkFolder('monitor-row-pruned');
  const home = mkFolder('monitor-row-pruned-home');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });
  const out = require('child_process').execFileSync('setsid',
    ['bash', '-c', 'sleep 300 </dev/null >/dev/null 2>&1 & echo $!'], { encoding: 'utf8' });
  const pid = Number(out.trim());
  const start = Number(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')
    .split(') ').pop().split(' ')[19]);
  try {
    const handles = path.join(home, '.cast', 'handles.jsonl');
    fs.mkdirSync(path.dirname(handles), { recursive: true });
    fs.writeFileSync(handles, `${JSON.stringify({
      pid, start, harness: 'claude', model: 'haiku-4-5', session: null,
      folder, transcript: null, t0: Date.now(),
    })}\n`);
    // blank the registry while the process stays ALIVE — a prune, not a death
    const prune = require('child_process').spawn('bash',
      ['-c', `sleep 2; : > '${handles}'`], { detached: true, stdio: 'ignore' });
    prune.unref();
    const watch = monitor(['--watch', '--poll', '1', '--grace', '600', '--stall', '600'],
      { timeout: 8000 });
    assert.ok(fs.existsSync(`/proc/${pid}`),
      'fixture broken: the planted process must still be alive for this arm to mean anything');
    assert.ok(!watch.stdout.includes('ENDED '),
      `a pruned row must NEVER be reported as ENDED while the process lives: ${watch.stdout}`);
  } finally {
    try { process.kill(pid, 'SIGKILL'); } catch { /* gone */ }
  }
}

// cast monitor --watch: stall + ENDED in one poll exits 3, not 4 (W5)
{
  const folder = mkFolder('monitor-ended-w5');
  const home = mkFolder('monitor-ended-w5-home');
  const enc = folder.replace(/[^a-zA-Z0-9]/g, '-');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });
  // Orphan the sleeper (setsid + background) so a kill REALLY clears /proc. A killed CHILD of this
  // suite lingers as a zombie — we are blocked in spawnSync and cannot reap it — and the liveness
  // guard would rightly still see it. Departure MUST be a real death: dropping the registry row
  // instead is the false positive the guard exists to suppress (a pruned row is not a dead job).
  const spawnSleeper = () => {
    const out = require('child_process').execFileSync('setsid',
      ['bash', '-c', 'sleep 300 </dev/null >/dev/null 2>&1 & echo $!'], { encoding: 'utf8' });
    const pid = Number(out.trim());
    const start = Number(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    return { pid, start, kill: () => { try { process.kill(pid, 'SIGKILL'); } catch { /* gone */ } } };
  };
  const frozen = spawnSleeper();
  const dying = spawnSleeper();
  try {
    const session = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
    const transcript = path.join(home, '.claude', 'projects', enc, `${session}.jsonl`);
    fs.mkdirSync(path.dirname(transcript), { recursive: true });
    fs.writeFileSync(transcript, '{}\n');
    const handle = (job, over) => JSON.stringify({
      pid: job.pid, start: job.start, harness: 'claude', model: 'haiku-4-5', session: null,
      folder, transcript: null, t0: Date.now(), ...over,
    });
    const handles = path.join(home, '.cast', 'handles.jsonl');
    fs.mkdirSync(path.dirname(handles), { recursive: true });
    fs.writeFileSync(handles,
      `${handle(frozen, { session, transcript })}\n${handle(dying, {})}\n`);
    const mutate = require('child_process').spawn('bash',
      ['-c', `sleep 2.5; touch -d '1 hour ago' '${transcript}'; kill -9 ${dying.pid}`],
      { detached: true, stdio: 'ignore' });
    mutate.unref();
    const watch = monitor(['--watch', '--poll', '1', '--stall', '60', '--grace', '600'],
      { timeout: 8000 });
    assert.strictEqual(watch.status, 3,
      `freeze+ENDED must exit 3, got ${watch.status}: ${watch.stdout}`);
    assert.ok(watch.stdout.includes(`STALL ${frozen.pid} `),
      `must print STALL: ${watch.stdout}`);
    assert.ok(watch.stdout.includes(`ENDED ${dying.pid} claude ${folder} alive=`),
      `must print ENDED: ${watch.stdout}`);
  } finally {
    frozen.kill();
    dying.kill();
  }
}

{
  const folder = mkFolder('monitor-limit');
  const home = mkFolder('monitor-limit-home');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });
  const outFile = path.join(folder, 'stdout.txt');
  fs.writeFileSync(outFile,
    'AI_APICallError: Usage limit reached for 5 hour. Your limit will reset at 2026-08-22 11:10:16\n');
  const fd = fs.openSync(outFile, 'a');
  const sleeper = require('child_process').spawn('sleep', ['60'],
    { detached: true, stdio: ['ignore', fd, 'ignore'] });
  sleeper.unref();
  fs.closeSync(fd);
  try {
    const start = Number(fs.readFileSync(`/proc/${sleeper.pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'), `${JSON.stringify({
      pid: sleeper.pid, start, harness: 'opencode', model: 'glm-5.2', session: null,
      folder, transcript: null, t0: Date.now() - 120_000,
    })}\n`);
    const rows = JSON.parse(monitor(['--json']).stdout);
    assert.strictEqual(rows.length, 1, `limit fixture must be on the roster: ${JSON.stringify(rows)}`);
    assert.strictEqual(rows[0].state, 'provider-limit', `expected provider-limit: ${JSON.stringify(rows)}`);
    assert.strictEqual(rows[0].resets, '2026-08-22 11:10:16');
    const watch = monitor(['--watch', '--poll', '1', '--grace', '600', '--stall', '600']);
    assert.strictEqual(watch.status, 3, `provider-limit must exit 3, got ${watch.status}: ${watch.stdout}`);
    assert.ok(watch.stdout.includes('PROVIDER-LIMIT'), `event line: ${watch.stdout}`);
    assert.ok(watch.stdout.includes('provider-limit: glm-5.2 resets 2026-08-22 11:10:16'),
      `named reason: ${watch.stdout}`);
    assert.ok(watch.stdout.includes('ADVISORY, not authority'), `advisory: ${watch.stdout}`);
  } finally {
    try { process.kill(sleeper.pid, 'SIGKILL'); } catch { /* gone */ }
  }
}

{
  const folder = mkFolder('monitor-deadline');
  const home = mkFolder('monitor-deadline-home');
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: path.join(home, 'no-such-data') };
  const monitor = (args, extra) => spawnSync('node', [TOOL, 'monitor', ...args],
    { encoding: 'utf8', env, ...extra });
  const sleeper = require('child_process').spawn('sleep', ['60'], { detached: true, stdio: 'ignore' });
  sleeper.unref();
  try {
    const start = Number(fs.readFileSync(`/proc/${sleeper.pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'), `${JSON.stringify({
      pid: sleeper.pid, start, harness: 'claude', model: 'haiku-4-5', session: null,
      folder, transcript: null, t0: Date.now() - 5000,
    })}\n`);
    const rows = JSON.parse(monitor(['--json', '--deadline', '1']).stdout);
    assert.strictEqual(rows[0].state, 'DEADLINE', `activity must not block deadline: ${JSON.stringify(rows)}`);
    const watch = monitor(['--watch', '--deadline', '1', '--poll', '1', '--grace', '600', '--stall', '600']);
    assert.strictEqual(watch.status, 3, `deadline must exit 3, got ${watch.status}: ${watch.stdout}`);
    assert.ok(watch.stdout.startsWith(`DEADLINE ${sleeper.pid} claude ${folder} alive=`),
      `deadline line: ${watch.stdout}`);
    assert.ok(watch.stdout.includes('ADVISORY, not authority'), `advisory: ${watch.stdout}`);
  } finally {
    try { process.kill(sleeper.pid, 'SIGKILL'); } catch { /* gone */ }
  }
}

// opencode reconciliation (issue G-owner-console-0819-0010): a final message the CLI swallowed
// from stdout is recovered from the session store; a run whose store holds NO final assistant
// message must not read as success — no-report marker + non-zero exit.
// The store is SHARED and opencode records the resolved project root, not the launch cwd, so a
// concurrent sibling seat's session sits in the same candidate set (measured 2026-08-31: a whole
// sibling report was appended as this run's). Every arm below therefore seeds a sibling holding a
// distinct report, and asserts that text never reaches this run's stdout: cast binds by the title
// tag it passed at launch, or it binds nothing at all.
{
  const folder = mkFolder('oc-reconcile');
  const home = mkFolder('oc-reconcile-home');
  const xdg = path.join(home, 'xdg');
  const bin = mkFolder('oc-reconcile-bin');
  const dbPath = path.join(xdg, 'opencode', 'opencode.db');
  const SIBLING = 'SIBLING-REPORT: a concurrent seat spoke';

  // the fake opencode stands in for the real one on the behaviour this binding rests on: the
  // session row it creates carries the --title it was launched with.
  const helper = path.join(bin, 'seed-session.js');
  fs.writeFileSync(helper, `const { DatabaseSync } = require('node:sqlite');
const argv = process.argv.slice(2);
const title = argv[argv.indexOf('--title') + 1];
const db = new DatabaseSync(${JSON.stringify(dbPath)});
const now = Date.now();
db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_r', process.cwd(), null, title, now, now);
db.close();
`);
  const fakeOpencode = (script, { createSession = true } = {}) => {
    fs.writeFileSync(path.join(bin, 'opencode'),
      `#!/bin/sh\ncat >/dev/null\n${createSession ? `node ${helper} "$@"\n` : ''}${script}\n`);
    fs.chmodSync(path.join(bin, 'opencode'), 0o755);
  };
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: xdg,
    PATH: `${bin}:${path.dirname(process.execPath)}` };

  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const { DatabaseSync } = require('node:sqlite');
  // fixture rows are born just before the cast launch, inside its t0-2000 bind window
  const seedDb = (withFinalText) => {
    try { fs.unlinkSync(dbPath); } catch { /* first write */ }
    const db = new DatabaseSync(dbPath);
    db.exec('create table session (id text primary key, directory text not null, parent_id text,'
      + ' title text, time_created integer not null, time_updated integer not null)');
    db.exec('create table message (id text primary key, session_id text not null,'
      + ' time_created integer not null, time_updated integer not null, data text not null)');
    db.exec('create table part (id text primary key, message_id text not null, session_id text not null,'
      + ' time_created integer not null, time_updated integer not null, data text not null)');
    const now = Date.now();
    const say = (id, sessionId, text) => {
      db.prepare('insert into message values (?,?,?,?,?)').run(id, sessionId, now, now,
        JSON.stringify({ role: 'assistant' }));
      db.prepare('insert into part values (?,?,?,?,?,?)').run(`prt_${id}`, id, sessionId, now, now,
        JSON.stringify({ type: 'text', text }));
    };
    // the concurrent sibling: same project root, born inside the same window, already finished
    db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_sib', folder, null,
      'a sibling seat [cast:deadbeef]', now, now);
    say('msg_sib', 'ses_sib', SIBLING);
    // this run's own messages; its SESSION row is written by the fake opencode, with cast's title
    if (withFinalText) say('msg_1', 'ses_r', withFinalText);
    db.close();
  };
  const cast = () => spawnSync('node', [TOOL, 'opencode', 'glm-5.2', '1', folder, '-p', 'hi'],
    { encoding: 'utf8', env });
  const noSibling = (res, arm) => assert.ok(!res.stdout.includes(SIBLING),
    `${arm}: a sibling session's report must never be recovered as this run's: ${res.stdout}`);

  // swallowed: stdout ends mid-tool-trace, exit 0 — the store's final message must be appended
  fakeOpencode('echo "| tool call trace"\nexit 0');
  seedDb('FINAL-REPORT: work landed');
  let res = cast();
  assert.strictEqual(res.status, 0, `recovered run must keep exit 0, got ${res.status}: ${res.stderr}`);
  assert.ok(res.stdout.includes('recovered final message'), `must mark the recovery: ${res.stdout}`);
  assert.ok(res.stdout.includes('FINAL-REPORT: work landed'), `must append the store's final message: ${res.stdout}`);
  noSibling(res, 'swallowed');

  // no report anywhere: bound session, store holds no assistant text — marker + non-zero
  seedDb(null);
  res = cast();
  assert.notStrictEqual(res.status, 0, `report-less exit 0 must turn non-zero: ${res.stdout}`);
  assert.ok(res.stdout.includes('cast: no-report'), `must print the no-report marker: ${res.stdout}`);
  noSibling(res, 'report-less');

  // cast's own session never reached the store: no id of its own -> no-report, never a neighbour's
  fakeOpencode('echo "| tool call trace"\nexit 0', { createSession: false });
  seedDb('FINAL-REPORT: work landed');
  res = cast();
  assert.notStrictEqual(res.status, 0, `unbindable run must not read as success: ${res.stdout}`);
  assert.ok(res.stdout.includes('cast: no-report'), `must print the no-report marker: ${res.stdout}`);
  noSibling(res, 'unbindable');

  // control: final message reached stdout — passed through untouched, no marker of either kind
  fakeOpencode('echo "ALL DONE here"\nexit 0');
  seedDb('ALL DONE here');
  res = cast();
  assert.strictEqual(res.status, 0, `healthy run must exit 0: ${res.stderr}`);
  assert.ok(res.stdout.includes('ALL DONE here'), `stdout must pass through: ${res.stdout}`);
  assert.ok(!res.stdout.includes('recovered final message'), `no recovery marker on a healthy run: ${res.stdout}`);
  assert.ok(!res.stdout.includes('cast: no-report'), `no no-report marker on a healthy run: ${res.stdout}`);
  noSibling(res, 'healthy');

  fakeOpencode('echo "AI_APICallError: Usage limit reached for 5 hour. Your limit will reset at 2026-08-22 11:10:16"\nexit 1');
  seedDb(null);
  res = cast();
  assert.notStrictEqual(res.status, 0, `limit run must be non-zero: ${res.stdout}`);
  assert.ok(res.stdout.includes('provider-limit: glm-5.2 resets 2026-08-22 11:10:16'),
    `must name the limit instead of no-report: ${res.stdout}`);
  assert.ok(!res.stdout.includes('cast: no-report'), `limit must not print no-report: ${res.stdout}`);
  noSibling(res, 'provider-limit');
}

{
  const folder = mkFolder('oc-deadline');
  const home = mkFolder('oc-deadline-home');
  const xdg = path.join(home, 'xdg');
  const bin = mkFolder('oc-deadline-bin');
  fs.writeFileSync(path.join(bin, 'opencode'), '#!/bin/sh\ncat >/dev/null\nsleep 5\nexit 0\n');
  fs.chmodSync(path.join(bin, 'opencode'), 0o755);
  const env = { ...process.env, HOME: home, XDG_DATA_HOME: xdg,
    PATH: `${bin}:${path.dirname(process.execPath)}`, CAST_DEADLINE_MS: '400' };
  const res = spawnSync('node', [TOOL, 'opencode', 'glm-5.2', '1', folder, '-p', 'hi'],
    { encoding: 'utf8', env, timeout: 8000 });
  assert.notStrictEqual(res.status, 0, `deadline must be non-zero: ${res.stderr}`);
  assert.ok(res.stderr.includes('cast: deadline'), `must print deadline: ${res.stderr}`);
}

// --- liveness binding by tag, not time-proximity (LE-2: cast-attribution) ---------------------
// opencode records the resolved PROJECT ROOT, not the launch cwd, so two concurrent seats under
// one project root land in the same session-store window; binding by nearest time_created let a
// job's liveness/progress signal come from a SIBLING's session (measured 2026-08-31, ~20 concurrent
// seats). Binding is now the exact `--title` tag launch.js gave the run — the same identity
// `opencodeTagged` uses to recover the final message.
{
  const home = mkFolder('bind-tag-home');
  const xdg = path.join(home, 'xdg');
  const dbPath = path.join(xdg, 'opencode', 'opencode.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(dbPath);
  db.exec('create table session (id text primary key, directory text not null, parent_id text,'
    + ' title text, time_created integer not null, time_updated integer not null)');
  const folder = mkFolder('bind-tag-folder');
  const t0 = Date.now();
  const tagA = 'bind-tag-folder [cast:aaaaaaaa]';
  const tagB = 'bind-tag-folder [cast:bbbbbbbb]';
  // session B is born CLOSER to handle A's t0 than A's own session — exactly the shape that
  // misattributes under time-proximity binding.
  db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_a', folder, null, tagA, t0 - 500, t0 - 500);
  db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_b', folder, null, tagB, t0 - 1, t0 - 1);
  db.close();

  const savedXdg = process.env.XDG_DATA_HOME;
  const savedHome = process.env.HOME;
  process.env.XDG_DATA_HOME = xdg;
  process.env.HOME = home;
  const libDir = path.join(__dirname, 'lib');
  const sessionsPath = path.join(libDir, 'sessions.js');
  const monitorPath = path.join(libDir, 'monitor.js');
  try {
    delete require.cache[require.resolve(sessionsPath)];
    delete require.cache[require.resolve(monitorPath)];
    const monitor = require(monitorPath);
    const bound = monitor.opencodeBind({ folder, tag: tagA, t0 }, new Set());
    assert.strictEqual(bound, 'ses_a',
      `must bind the handle's OWN tagged session, never the temporally-closer sibling: got ${bound}`);
  } finally {
    process.env.XDG_DATA_HOME = savedXdg;
    process.env.HOME = savedHome;
    delete require.cache[require.resolve(sessionsPath)];
    delete require.cache[require.resolve(monitorPath)];
  }
}

// --- provider-limit attributed per job, not off the shared opencode.log (LE-2 cont'd) ----------
// The detector's diagnostic fallback tails a log SHARED by every opencode run on the box; without
// a per-job filter, one job's usage-limit line could be flagged onto a DIFFERENT handle running
// the same model. Two handles, same model — only job B actually hit the limit.
{
  const folder = mkFolder('limit-perjob-folder');
  const home = mkFolder('limit-perjob-home');
  const xdg = path.join(home, 'xdg');
  const dbPath = path.join(xdg, 'opencode', 'opencode.db');
  const logPath = path.join(xdg, 'opencode', 'log', 'opencode.log');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  fs.mkdirSync(path.dirname(logPath), { recursive: true });

  const spawnSleeper = () => {
    const out = require('child_process').execFileSync('setsid',
      ['bash', '-c', 'sleep 300 </dev/null >/dev/null 2>&1 & echo $!'], { encoding: 'utf8' });
    const pid = Number(out.trim());
    const start = Number(fs.readFileSync(`/proc/${pid}/stat`, 'utf8')
      .split(') ').pop().split(' ')[19]);
    return { pid, start, kill: () => { try { process.kill(pid, 'SIGKILL'); } catch { /* gone */ } } };
  };
  const jobA = spawnSleeper();
  const jobB = spawnSleeper();
  try {
    const t0 = Date.now() - 5000;
    const tagA = 'limit-perjob-folder [cast:aaaaaaaa]';
    const tagB = 'limit-perjob-folder [cast:bbbbbbbb]';
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(dbPath);
    db.exec('create table session (id text primary key, directory text not null, parent_id text,'
      + ' title text, time_created integer not null, time_updated integer not null)');
    db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_a', folder, null, tagA, t0, t0);
    db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_b', folder, null, tagB, t0 + 1, t0 + 1);
    db.close();

    // shared log: ONLY job B's session hit the limit
    fs.writeFileSync(logPath, `timestamp=${new Date(t0 + 2000).toISOString()} level=ERROR run=xxxx`
      + ' message="stream error" providerID=zai-coding-plan modelID=glm-5.2 session.id=ses_b'
      + ' small=false agent=build mode=primary error.error="AI_APICallError: Usage limit reached'
      + ' for 5 hour. Your limit will reset at 2026-08-31 20:00:00"\n');

    fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
    const handle = (job, tag) => JSON.stringify({
      pid: job.pid, start: job.start, harness: 'opencode', model: 'glm-5.2', session: null,
      tag, folder, transcript: null, t0,
    });
    fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'),
      `${handle(jobA, tagA)}\n${handle(jobB, tagB)}\n`);

    const env = { ...process.env, HOME: home, XDG_DATA_HOME: xdg };
    const rows = JSON.parse(spawnSync('node', [TOOL, 'monitor', '--json'], { encoding: 'utf8', env }).stdout);
    const rowA = rows.find((r) => r.pid === jobA.pid);
    const rowB = rows.find((r) => r.pid === jobB.pid);
    assert.strictEqual(rowB.state, 'provider-limit', `B genuinely hit the limit: ${JSON.stringify(rowB)}`);
    assert.notStrictEqual(rowA.state, 'provider-limit',
      `A must NOT inherit B's limit off the shared log: ${JSON.stringify(rowA)}`);
  } finally {
    jobA.kill();
    jobB.kill();
  }
}

// --- detached-launch refusal (ruling D): the standing gate on the binary itself -------------
// setsid makes cast a session leader -> refused before anything spawns. The rest of this suite
// doubles as the false-positive control: every other arm runs cast as a live child of this
// node process and none of them trips the gate.
{
  const setsidLaunch = (extra = []) => require('child_process').spawnSync('setsid',
    ['node', path.join(__dirname, 'cast.js'), 'claude', 'sonnet-5', '1', os.tmpdir(), ...extra, '-p', 'never runs'],
    { encoding: 'utf8' });
  const refused = setsidLaunch();
  assert.strictEqual(refused.status, 2, `detached launch must exit 2, got ${refused.status}`);
  assert.ok(refused.stderr.includes('refused: detached launch'), `unexpected stderr: ${refused.stderr}`);
  assert.ok(refused.stderr.includes('session leader'), `must name the mark: ${refused.stderr}`);
  const overridden = setsidLaunch(['--detached', '--dry-run']);
  assert.strictEqual(overridden.status, 0, `--detached --dry-run must pass, got ${overridden.status}: ${overridden.stderr}`);
}

console.log('all cast tests passed');
