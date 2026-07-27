'use strict';

class SpawnError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'SpawnError';
    this.code = code;
    this.details = details;
  }
}

const E_CONFIG_LOAD = 'E_CONFIG_LOAD';
const E_DUPLICATE_PROFILE = 'E_DUPLICATE_PROFILE';
const E_UNKNOWN_SLOT = 'E_UNKNOWN_SLOT';
const E_MISSING_KEY = 'E_MISSING_KEY';
const E_UNKNOWN_PROFILE = 'E_UNKNOWN_PROFILE';
const E_UNKNOWN_MODE = 'E_UNKNOWN_MODE';
const E_HEADED_NOT_CAPABLE = 'E_HEADED_NOT_CAPABLE';
const E_FLAG_INJECTION = 'E_FLAG_INJECTION';
const E_WORKDIR_ESCAPE = 'E_WORKDIR_ESCAPE';
const E_WORKDIR_MISSING = 'E_WORKDIR_MISSING';
const E_UNKNOWN_REQUEST_KEY = 'E_UNKNOWN_REQUEST_KEY';
const E_SESSION_NOT_FOUND = 'E_SESSION_NOT_FOUND';
const E_CARRIER_FAILED = 'E_CARRIER_FAILED';

const E_SYSTEMD_NOT_AVAILABLE = 'E_SYSTEMD_NOT_AVAILABLE';
const E_FS_SANDBOX_UNAVAILABLE = 'E_FS_SANDBOX_UNAVAILABLE';
const E_ORPHAN_RESCAN_FAILED = 'E_ORPHAN_RESCAN_FAILED';
const E_BAD_REQUEST = 'E_BAD_REQUEST';
// 7.30: a tmux session/window name carrying a target separator (`:` `.`) or whitespace would
// silently re-target another pane. Names are server-composed, so this refuses before compose.
const E_TMUX_NAME_INVALID = 'E_TMUX_NAME_INVALID';

module.exports = {
  SpawnError,
  E_CONFIG_LOAD,
  E_DUPLICATE_PROFILE,
  E_UNKNOWN_SLOT,
  E_MISSING_KEY,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_MODE,
  E_HEADED_NOT_CAPABLE,
  E_FLAG_INJECTION,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
  E_UNKNOWN_REQUEST_KEY,
  E_SESSION_NOT_FOUND,
  E_CARRIER_FAILED,
  E_SYSTEMD_NOT_AVAILABLE,
  E_FS_SANDBOX_UNAVAILABLE,
  E_ORPHAN_RESCAN_FAILED,
  E_BAD_REQUEST,
  E_TMUX_NAME_INVALID,
};
