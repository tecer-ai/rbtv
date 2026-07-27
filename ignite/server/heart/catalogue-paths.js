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
    }
  }
  return findings;
}

module.exports = { validateCataloguePaths, CATALOGUE_SECTIONS };
