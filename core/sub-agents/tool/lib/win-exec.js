'use strict';

// cast — how a program name becomes a process on THIS platform.
//
// POSIX starts every harness from a bare name. Windows does not. Measured on the Windows
// desktop 2026-09-01:
//   claude   -> C:\Users\henri\.local\bin\claude.exe                    a real .exe   launches
//   codex    -> C:\Users\henri\AppData\Roaming\npm\codex + codex.cmd    npm shim      ENOENT
//   opencode -> ...\npm\opencode + opencode.cmd                         npm shim      ENOENT
// An npm global install writes a batch wrapper (.cmd), a PowerShell wrapper (.ps1) and an
// extensionless POSIX sh script. Node's spawn with shell:false hands the name straight to
// Windows' CreateProcess, which starts an .exe but never a batch file — and since
// CVE-2024-27980 (Node 18.20.2 / 20.12.2 / 21.7.3) Node refuses a .cmd target outright
// rather than silently routing it through cmd.exe with unescaped arguments.
//
// `shell: true` is NOT the fix. It concatenates argv into one string the shell re-parses
// (Node's own DEP0190 deprecation). Measured 2026-09-01 against cast's real --dry-run argv:
// opencode's `--title "<folder> [cast:xxxxxxxx]"` splits into two arguments — and that title
// is the ONLY session identity cast has for opencode, whose loss is the 2026-08-31 bug where
// one seat's report landed in another seat's output. A headed prompt shatters at every space,
// an apostrophe aborts the launch, and `$(id)` inside any argument really executed.
//
// So: resolve what Windows would actually start, and route ONLY a batch file through
// cmd.exe, with every token pre-quoted and argv still a real array. A .exe keeps the exact
// direct-spawn path it has today, so the one harness that already works is not disturbed.
// On POSIX this module returns its input unchanged.

const fs = require('fs');
const path = require('path');

// --- vendored: cross-spawn 7.0.6, lib/util/escape.js -----------------------------------------
// Copyright (c) 2018 Made With MOAR, Lda — MIT License.
// https://github.com/moxystudio/node-cross-spawn/blob/master/LICENSE
// Copied verbatim rather than depended on: cast has no package.json and no node_modules, and
// cross-spawn's own dependencies (which, path-key, shebang-command) serve PATH resolution and
// POSIX shebang sniffing, neither of which is wanted here. Quoting for cmd.exe is the class of
// bug CVE-2024-27980 is about — this is tested, widely-run code, not a hand-rolled regex.
// See http://www.robvanderwoude.com/escapechars.php
const metaCharsRegExp = /([()\][%!^"`<>&|;, *?])/g;

function escapeCommand(arg) {
  return arg.replace(metaCharsRegExp, '^$1');
}

function escapeArgument(arg, doubleEscapeMetaChars) {
  arg = `${arg}`;
  // Sequence of backslashes followed by a double quote: double the backslashes, escape the quote.
  arg = arg.replace(/(?=(\\+?)?)\1"/g, '$1$1\\"');
  // Sequence of backslashes at end of string (about to be followed by our closing quote).
  arg = arg.replace(/(?=(\\+?)?)\1$/, '$1$1');
  arg = `"${arg}"`;
  arg = arg.replace(metaCharsRegExp, '^$1');
  if (doubleEscapeMetaChars) arg = arg.replace(metaCharsRegExp, '^$1');
  return arg;
}
// --- end vendored ----------------------------------------------------------------------------

// What Windows itself would start for this name. Extensions come from PATHEXT, never from a
// guess — and a name with no extension is NEVER matched against the extensionless file, because
// on Windows that file is the POSIX sh script the same npm install wrote, which Windows cannot
// run at all. Absolute or path-bearing names are taken as given.
function resolveWindowsExecutable(name, env) {
  const exts = (env.PATHEXT || '.COM;.EXE;.BAT;.CMD').split(';').filter(Boolean);
  const isFile = (p) => { try { return fs.statSync(p).isFile(); } catch { return false; } };
  const hasKnownExt = exts.some((e) => name.toLowerCase().endsWith(e.toLowerCase()));

  if (path.isAbsolute(name) || name.includes('/') || name.includes('\\')) {
    if (hasKnownExt) return isFile(name) ? name : null;
    for (const ext of exts) if (isFile(name + ext)) return name + ext;
    return null;
  }
  for (const dir of (env.PATH || '').split(path.delimiter).filter(Boolean)) {
    if (hasKnownExt) {
      const direct = path.join(dir, name);
      if (isFile(direct)) return direct;
      continue;
    }
    for (const ext of exts) {
      const candidate = path.join(dir, name + ext);
      if (isFile(candidate)) return candidate;
    }
  }
  return null;
}

// The one call every spawn site goes through. Returns the command, args and extra spawn options
// to use on this platform. `platform` and `env` are injectable so the Windows branch is checkable
// from the POSIX self-check suite.
function spawnable(cmd, args, platform = process.platform, env = process.env) {
  if (platform !== 'win32') return { cmd, args, opts: {} };

  const resolved = resolveWindowsExecutable(cmd, env);
  // Not found, or directly executable: leave it exactly as it is. A missing program must still
  // surface as Node's own ENOENT for `cmd`, not as a confusing error from cmd.exe.
  if (resolved === null || /\.(exe|com)$/i.test(resolved)) return { cmd, args, opts: {} };

  // cross-spawn double-escapes only for a .cmd under node_modules/.bin, whose shim re-enters
  // cmd.exe a second time. A global npm shim (AppData\Roaming\npm) does not, so a single pass
  // is what cross-spawn itself would apply to these exact files.
  const doubleEscape = /node_modules[\\/]\.bin[\\/][^\\/]+\.cmd$/i.test(resolved);
  const line = [escapeCommand(path.normalize(resolved))]
    .concat(args.map((a) => escapeArgument(a, doubleEscape)))
    .join(' ');
  return {
    cmd: env.comspec || env.ComSpec || 'cmd.exe',
    args: ['/d', '/s', '/c', `"${line}"`],
    opts: { windowsVerbatimArguments: true },
  };
}

module.exports = { spawnable, resolveWindowsExecutable };
