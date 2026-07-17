'use strict';

// server/pty/ — the headed/pty session-surface extension (task 6.2, session-surface-spec.md
// Design 1–3). Module entry: the daemon (server/index.js) creates ONE pty host and routes
// session_mode:headed spawns to it (pty wiring only); everything headless stays on the existing
// sole-spawn-path unchanged. See pty-host.js for the architecture and the D79-proven properties.

const { createPtyHost } = require('./pty-host');

module.exports = { createPtyHost };
