'use strict';

// Task C5 fixture child — the ONLY honest way to read a composed argv is to ask the process that
// received it. A tick-log field would be the ticker's own account of what it composed; this is the
// exec'd command line itself, written by the child from its OWN `process.argv`.
//
// It writes into its CWD, which the carrier sets to the queue row's `workdir` — so the probe reads
// the capture from the fixture goal folder it created, with no path passed in to be got wrong.

const fs = require('node:fs');
const path = require('node:path');

fs.writeFileSync(path.join(process.cwd(), 'argv-echo.json'),
  JSON.stringify(process.argv.slice(1), null, 2) + '\n');
