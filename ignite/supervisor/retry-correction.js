'use strict';

// -- THE OWNER-CORRECTION PAYLOAD [d-recovery-correction-lands-in-instructions] -----------------
//
// The owner replies `retry-with-change <free text>` on a stuck lane's recovery ask
// (`ignite/chat/recovery-thread.js#dispatch`, the `retry-with-change` arm). That free text MUST
// land in the RESTARTED seat's own starting instructions, in a section marked as an owner
// correction, so the seat cannot begin work without having read it. The rejected alternative -
// posting it as a coordination-log message - was reversed on the race argument: a restarted seat
// can act before the message lands, reproducing the failure this feature exists to end.
//
// THE GAP THIS CLOSES. `retryWithChange` (the lane-scoped re-arm act `rr-lane-rearm` built)
// UNBLOCKS the lane - it clears the counter row and arms the ending - it does NOT relaunch. The
// actual relaunch happens later, on the supervisor's own next reconcile pass
// (`reconcile.js#counterDisarmed` -> `launchSitting` -> `seatBootPrompt` -> `coord.py boot-prompt`
// -> `launch.py#boot_prompt`). This module is what bridges that gap: it writes the correction to
// the ONE shared writable surface a relaunched seat's boot prompt reads from
// (`{goalFolder}/coordination/`), so the text is already on disk, in the right place, well before
// that later reconcile pass ever fires.
//
// EXTENDS THE EXISTING ROUTE-PAYLOAD CHANNEL, PER A DIFFERENT DIRECTORY. `attest.py`'s
// `write_route_payload`/`read_route_payload` already do exactly this job for a routed FAIL
// (`cmd_route_fail`); `boot_prompt` (`launch.py`) already folds that payload into the relaunched
// sitting's opening as an ADDITION, never a substitution. This module writes the SAME shape of
// file to a SEPARATE directory (`correction-payloads/`, `attest.CORRECTION_PAYLOAD_DIR`) so an
// owner correction and an unrelated routed FAIL landing for the same seat before its next boot
// cannot silently clobber one another - `write_route_payload` overwrites, it does not merge.
// `boot_prompt` reads this second channel and folds it in under its own explicit
// "OWNER CORRECTION" heading (never merged into the routed-FAIL wrapper text, which would say the
// wrong thing about why the seat was relaunched).
//
// THE PATH IS THE ONLY CONTRACT. Nothing here calls into Python; the JS writer and the Python
// reader (`attest.route_payload_path(base, seat, kind="correction")`) agree ONLY by writing and
// reading the same path. `CORRECTION_PAYLOAD_DIR` below must stay byte-identical to
// `attest.CORRECTION_PAYLOAD_DIR` in `ignite/supervisor/attest.py` - nothing enforces that
// automatically across the language boundary, so a change to one side is a change to both.

const fs = require('node:fs');
const path = require('node:path');

const CORRECTION_PAYLOAD_DIR = 'correction-payloads';

// The same seat-name syntax `runtime/gateway/parse.js#BUS_NAME_RE` (line 118) already validates
// at the intent-parsing boundary, re-checked here in defense of depth: `seat` becomes a FILENAME
// below, and this module must never trust an upstream caller's validation to still be in force by
// the time it runs. `comments` is never checked against this - it is untrusted owner free text
// that only ever becomes file CONTENT, never a path segment.
const SAFE_SEAT_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

// Writes the owner's `retry-with-change` free text into `seat`'s next-boot correction payload.
// `{ goalFolder, seat, comments }` -> `{ ok, written, path?, error? }`, never throws.
//
// EMPTY/ABSENT `comments` IS A CLEAN NO-OP - most `retry-with-change` replies carry no free text,
// and `boot_prompt` must render EXACTLY as it does today when nothing was written: no empty
// section, no header with nothing under it. So an empty correction writes NOTHING, rather than an
// empty file a reader would have to special-case.
function writeRetryCorrection({ goalFolder, seat, comments } = {}) {
  const text = String(comments || '').trim();
  if (!text) return { ok: true, written: false };
  if (typeof goalFolder !== 'string' || !goalFolder) {
    return {
      ok: false, written: false, error: 'goalFolder is required',
    };
  }
  if (typeof seat !== 'string' || !SAFE_SEAT_RE.test(seat)) {
    return {
      ok: false, written: false, error: `not a valid seat name: ${JSON.stringify(seat)}`,
    };
  }
  const dir = path.join(goalFolder, 'coordination', CORRECTION_PAYLOAD_DIR);
  const target = path.join(dir, `${seat}.md`);
  try {
    fs.mkdirSync(dir, { recursive: true });
    // `write_route_payload`'s own body is the precedent for the file's shape - a dated heading
    // plus the raw words, appended (never substituted) into the next boot prompt.
    const body = `## OWNER CORRECTION — retry-with-change (${new Date().toISOString()})\n\n${text}\n`;
    fs.writeFileSync(target, body, 'utf8');
  } catch (err) {
    return { ok: false, written: false, error: err.message };
  }
  return { ok: true, written: true, path: target };
}

module.exports = { writeRetryCorrection, CORRECTION_PAYLOAD_DIR };
