'use strict';

// Boot-time validation of the paths the tool/workflow catalogues reference (campaign issue S-6(b)).
//
// THE DEFECT. Production config was read at boot with NO path validation, so a broken entry produced
// SILENCE rather than an error. Two live `tools:` entries pointed at fixtures inside an EPHEMERAL
// seat folder (`seats/jobs-builder/throwaway/…`) whose owning seat has since closed. Any tidy of
// that folder breaks them invisibly, and it surfaces months later as a confusing probe failure
// nobody connects to a directory that was deleted. The general rule this enforces:
// PRODUCTION CONFIG MUST NEVER REFERENCE A PATH WHOSE LIFETIME IS SHORTER THAN ITS OWN.
//
// It lives in its own module, and that is not tidiness: `server/index.js` calls `main()` at require
// time, so anything defined there cannot be exercised by a probe without booting a daemon. A check
// that cannot be tested is the shape of check that quietly stops working.
//
// WHAT IT CHECKS, and the bound is deliberate: argv[0] — the interpreter or binary — and every later
// element that LOOKS like an absolute filesystem path. It does NOT interpret flags or guess which
// strings are meant to be paths: a false ERROR about a string that was never a path would train
// readers to ignore the check, which costs more than the check earns.
//
// ⚠ AND EVERY `args_allowlist` VALUE (task 7.559). This walk is NOT an enhancement, it is the
// repair of a hole that task opened: 7.559 moves the edge-runner's goal path OUT of `argv` and into
// `args_allowlist`, and the argv walk above skips any token containing `{` — so without this the
// path would leave the boot check silently and a retired goal would go back to being invisible,
// which is the exact defect this module exists for. Same log-never-refuse posture.
//
// A DECLARED-BUT-ABSENT ALLOWLIST VALUE IS NOISE, NEVER AN OUTAGE — decided and stated rather than
// left to be discovered: it logs one `error` line per boot, FOREVER, and refuses nothing. That is
// the intended behaviour, and it is why the finding carries its OWN `why` rather than reusing the
// argv one. A stale member is a permission for a target that no longer exists, and the operator's
// action is to REMOVE it by the same act that added it — a reviewed diff plus a restart, ideally as
// part of the retiring goal's teardown. It is deliberately NOT cleaned up automatically: a daemon
// that edits its own security allowlist at boot is a strictly worse system than one that complains.
//
// WHAT IT DOES NOT DO: refuse the boot. A missing fixture in one throwaway entry must not take the
// whole daemon down — that trades a silent broken entry for a loud dead daemon, which is worse for a
// system whose purpose is running unattended. The caller logs `level: error`, one line per broken
// reference plus a count, so it is greppable in the journal and cannot read as routine noise.

const fs = require('node:fs');

const CATALOGUE_SECTIONS = ['tools', 'workflows'];

function validateCataloguePaths(mergedConfig) {
  const findings = [];
  for (const section of CATALOGUE_SECTIONS) {
    const entries = (mergedConfig && mergedConfig[section]) || {};
    for (const [name, entry] of Object.entries(entries)) {
      const argv = entry && Array.isArray(entry.argv) ? entry.argv : null;
      if (!argv || argv.length === 0) {
        findings.push({ section, name, index: null, path: null, why: 'entry declares no argv' });
        continue;
      }
      argv.forEach((element, index) => {
        if (typeof element !== 'string') return;
        if (element.includes('{')) return;            // a template slot, resolved at fire time
        if (!element.startsWith('/')) return;         // argv[0] from PATH, or a flag/value
        if (!fs.existsSync(element)) {
          findings.push({ section, name, index, path: element, why: 'path does not exist' });
        }
      });
      // The values a row may SELECT (7.559). No `{` skip here and none is wanted: an allowlist
      // member is a literal the config author wrote, never a template — that is the whole design.
      const allow = entry.args_allowlist;
      if (allow && typeof allow === 'object' && !Array.isArray(allow)) {
        for (const [key, permitted] of Object.entries(allow)) {
          if (!Array.isArray(permitted)) continue;
          permitted.forEach((value) => {
            if (typeof value !== 'string') return;
            if (!value.startsWith('/')) return;
            if (!fs.existsSync(value)) {
              findings.push({
                section, name, index: null, key, path: value,
                why: 'allowlisted path does not exist — a permitted value naming a target that is gone (stale permission; remove it by config edit + restart)',
              });
            }
          });
        }
      }
    }
  }
  return findings;
}

module.exports = { validateCataloguePaths, CATALOGUE_SECTIONS };
