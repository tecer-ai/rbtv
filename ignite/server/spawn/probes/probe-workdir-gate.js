'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture, fire } = require('./lib');

capture('probe-workdir-gate', async (lines) => {
  const ctx = setup();
  try {
    // A REAL symlink-escape: a link INSIDE workdir_root that resolves OUTSIDE it.
    // canonicalizeWorkdir uses realpathSync, so the escape must be caught post-resolution.
    const escapeLink = path.join(ctx.workRoot, 'escape-link');
    fs.symlinkSync(ctx.escapedir, escapeLink);
    lines.push(`symlink ${escapeLink} -> ${fs.realpathSync(escapeLink)} (outside workdir_root ${ctx.workRoot})`);

    // ⚠ THE ESCAPE LEGS NOW USE SEAT-SHAPED PATHS, and that is a STRENGTHENING forced by 7.787,
    // not a workaround. `E_WORKDIR_ESCAPE` is a statement about A SPEC's containment boundary —
    // and since `#d-abolish-profile-names` a dispatch gets a spec ONLY from the seat descriptor at
    // its workdir. A bare `/tmp` therefore has no spec to escape FROM, and its honest first refusal
    // is the seatless one (asserted below). The case the containment gate actually protects is a
    // real SEAT folder sitting outside the spec's root — which is what these legs now hand it, cast
    // to the fixture's own spec so a spec genuinely exists to escape from.
    const outsideSeat = path.join(ctx.escapedir, '.rbtv', 'goals', 'g', 'seats', 'escapee');
    fs.mkdirSync(outsideSeat, { recursive: true });
    fs.writeFileSync(path.join(outsideSeat, 'seat.md'), '---\nseat: escapee\nharness: bash\nmodel: test-sleep\n---\n');
    const seatLink = path.join(ctx.workRoot, 'seat-escape-link');
    fs.symlinkSync(outsideSeat, seatLink);
    const cases = [
      { name: 'seat folder outside workdir_root', code: 'E_WORKDIR_ESCAPE', fn: () => ctx.mgr.spawn(0, 'headless', null, outsideSeat, 'probe') },
      { name: 'symlink escape (link inside root resolves outside)', code: 'E_WORKDIR_ESCAPE', fn: () => ctx.mgr.spawn(0, 'headless', null, seatLink, 'probe') },
      // The PAIRED case, so the two refusals stay distinguishable: a path that is not seat-shaped
      // at all is refused for naming no seat, NOT for escaping — the operator's fix differs.
      { name: 'absolute non-seat path outside root', code: 'E_SEATLESS_GOAL_DISPATCH', fn: () => ctx.mgr.spawn(0, 'headless', null, '/tmp', 'probe') },
    ];
    // ASSERT the code, never merely record it — the two legs below already do. A loop that pushes
    // `err.code` and moves on cannot fail, so any refusal that degrades into a different throw
    // (e.g. the `path.basename(null)` ERR_INVALID_ARG_TYPE regression of 29220dc9) still reads PASS.
    for (const c of cases) {
      try {
        await c.fn();
        throw new Error(`${c.name}: UNEXPECTED PASS — expected ${c.code}`);
      } catch (err) {
        if (err.code !== c.code) throw err;
        lines.push(`${c.name}: ${err.code}`);
      }
    }

    // Omitted workdir: REFUSED (r-seats-only-architecture (3)). The default branch used to
    // fall back to default_workdir_root / materialize the flat .rbtv/sessions/ dir; a dispatch
    // with no home is now a refusal, not a flat dir.
    const fired = fire(ctx, { cast: 'test-sleep', sessionMode: 'headless', workdir: null });
    try {
      await ctx.mgr.spawn(fired.exec_id, 'headless', null, null, 'probe');
      throw new Error('workdir omitted: UNEXPECTED PASS — the retired flat/default branch admitted a homeless dispatch');
    } catch (err) {
      if (err.code !== 'E_SEATLESS_GOAL_DISPATCH' || !/REFUSING SEATLESS DISPATCH/.test(err.message)) throw err;
      lines.push(`workdir omitted: ${err.code} (REFUSING SEATLESS DISPATCH)`);
    }
    // A flat non-seat workdir inside the root: refused by the same door.
    try {
      await ctx.mgr.spawn(0, 'headless', null, ctx.workRoot, 'probe');
      throw new Error('flat workdir: UNEXPECTED PASS — a non-seat workdir was admitted');
    } catch (err) {
      if (err.code !== 'E_SEATLESS_GOAL_DISPATCH') throw err;
      lines.push(`flat non-seat workdir inside root: ${err.code}`);
    }
    lines.push('result: escapes rejected; omitted and non-seat workdirs are REFUSED (no flat fallback remains)');
  } finally {
    teardown(ctx);
  }
});
