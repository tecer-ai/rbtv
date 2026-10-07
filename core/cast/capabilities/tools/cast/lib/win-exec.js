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
// So: resolve what Windows would actually start. An npm shim is replaced by the node script it
// runs; any other batch file goes through cmd.exe, with every token pre-quoted and argv still a
// real array. A .exe keeps the exact
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

// The extensions spawnable() below knows how to start: a program directly, a batch file through
// cmd.exe. PATHEXT may list more (.JS, .VBS, .WSF on a stock Windows) — those are files Windows
// hands to its own script host, which is never the harness.
const STARTABLE_EXTS = ['.com', '.exe', '.bat', '.cmd'];

// What cast can start for this name on Windows. Extensions come from PATHEXT, in its order,
// narrowed to STARTABLE_EXTS — any other match is "not found". A name with no extension is NEVER
// matched against the extensionless file, because on Windows that file is the POSIX sh script
// the same npm install wrote, which Windows cannot run at all. Absolute or path-bearing names
// are taken as given.
function resolveWindowsExecutable(name, env) {
  const exts = (env.PATHEXT || '.COM;.EXE;.BAT;.CMD').split(';')
    .filter((e) => STARTABLE_EXTS.includes(e.toLowerCase()));
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

// Where PATH would find the program, or null. Read from the folders of PATH; nothing is started.
function findOnPath(name, env = process.env) {
  if (process.platform === 'win32') return resolveWindowsExecutable(name, env);
  for (const dir of (env.PATH || '').split(path.delimiter).filter(Boolean)) {
    const file = path.join(dir, name);
    try {
      if (fs.statSync(file).isFile()) {
        fs.accessSync(file, fs.constants.X_OK);
        return file;
      }
    } catch { /* not here */ }
  }
  return null;
}

// An npm global shim is a batch file ending in `"%_prog%" "%dp0%\path\to\entry.js" %*`. The
// script it runs is what matters: started with node directly, argv stays a real array and cmd.exe
// never re-parses it (a `&`, `|`, `<`, `>`, `%` or quote in an argument — a whole agent prompt —
// breaks the batch route). Null when the shim is not that shape.
function npmShimScript(shim) {
  let text;
  try { text = fs.readFileSync(shim, 'utf8'); } catch { return null; }
  const m = text.match(/"%_prog%"\s+"%dp0%\\([^"]+)"\s+%\*/);
  if (!m) return null;
  const script = path.join(path.dirname(shim), ...m[1].split('\\'));
  return fs.existsSync(script) ? script : null;
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

  const script = /\.cmd$/i.test(resolved) ? npmShimScript(resolved) : null;
  if (script) return { cmd: process.execPath, args: [script, ...args], opts: {} };

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

module.exports = { spawnable, resolveWindowsExecutable, findOnPath };
