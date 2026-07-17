'use strict';

// The server-side headless vt/terminal-state model (session-surface-spec.md Design 1, screen
// capture). A pty yields a raw byte STREAM, not a screen; this model consumes the pty-master
// byte stream (fed from the dtach attach bridge) into a fixed cell grid, so screen capture
// returns the CURRENT RENDERED screen (spec Behavior #3), not a replay of raw ANSI.
//
// ★ Amendment #4 DECISION — this is a MINIMAL IN-HOUSE vt-state model, chosen over an external
// npm vt library (e.g. @xterm/headless) to keep the daemon's ZERO-npm-dependency posture
// (no package.json; stdlib + a symlinked js-yaml). It is deliberately text-capture-scoped:
// it tracks the cursor and the character cell grid, and it INTERPRETS the cursor/erase/scroll
// control sequences a TUI uses to place text; it does NOT render colour/attributes (SGR is
// parsed-and-dropped) because criterion 3 is "rendered CONTENT", not styling. It is a streaming
// parser: an escape sequence split across two write() calls is held in `pending` and resumed.
//
// Fidelity note (surfaced in the dispatch return's concerns): a hand-rolled model cannot match a
// full terminal emulator on every sequence a complex TUI emits (scroll regions, wrapped soft
// lines, complex private modes). It handles the common cursor/erase/alt-screen set faithfully;
// exotic sequences are skipped, never mis-placed. This is the Amendment-#4 in-house/zero-dep
// tradeoff, stated, not hidden.

const { StringDecoder } = require('node:string_decoder');

const DEFAULT_ROWS = 24;
const DEFAULT_COLS = 80;
const TAB = 8;

function blankRow(cols) {
  return new Array(cols).fill(' ');
}

class VtModel {
  constructor({ rows = DEFAULT_ROWS, cols = DEFAULT_COLS } = {}) {
    this.rows = rows;
    this.cols = cols;
    this.reset();
  }

  reset() {
    this.grid = [];
    for (let r = 0; r < this.rows; r += 1) this.grid.push(blankRow(this.cols));
    this.cr = 0; // cursor row (0-indexed)
    this.cc = 0; // cursor col (0-indexed)
    this.pending = ''; // partial escape sequence across chunk boundaries
    // UTF-8 decode with cross-chunk carry (p6-2 review fix): the former latin1 ('binary') decode
    // split every multibyte character into mojibake cells — a real TUI's box-drawing borders and
    // any non-ASCII text rendered as garbage AND drifted the column accounting. StringDecoder
    // holds a partial multibyte sequence across write() boundaries. Stated limitation: a
    // double-WIDTH char (CJK/emoji) still occupies ONE cell in this model.
    this.decoder = new StringDecoder('utf8');
    this.bytesConsumed = 0;
  }

  resize(rows, cols) {
    this.rows = rows;
    this.cols = cols;
    this.reset();
  }

  _scrollUp() {
    this.grid.shift();
    this.grid.push(blankRow(this.cols));
  }

  _lf() {
    this.cr += 1;
    if (this.cr >= this.rows) {
      this.cr = this.rows - 1;
      this._scrollUp();
    }
  }

  _putChar(ch) {
    if (this.cc >= this.cols) {
      // soft-wrap
      this.cc = 0;
      this._lf();
    }
    this.grid[this.cr][this.cc] = ch;
    this.cc += 1;
  }

  _eraseInDisplay(n) {
    if (n === 2 || n === 3) {
      for (let r = 0; r < this.rows; r += 1) this.grid[r] = blankRow(this.cols);
      return;
    }
    if (n === 0) {
      for (let c = this.cc; c < this.cols; c += 1) this.grid[this.cr][c] = ' ';
      for (let r = this.cr + 1; r < this.rows; r += 1) this.grid[r] = blankRow(this.cols);
      return;
    }
    if (n === 1) {
      for (let r = 0; r < this.cr; r += 1) this.grid[r] = blankRow(this.cols);
      for (let c = 0; c <= this.cc && c < this.cols; c += 1) this.grid[this.cr][c] = ' ';
    }
  }

  _eraseInLine(n) {
    if (n === 0) { for (let c = this.cc; c < this.cols; c += 1) this.grid[this.cr][c] = ' '; return; }
    if (n === 1) { for (let c = 0; c <= this.cc && c < this.cols; c += 1) this.grid[this.cr][c] = ' '; return; }
    if (n === 2) { this.grid[this.cr] = blankRow(this.cols); }
  }

  _clamp() {
    if (this.cr < 0) this.cr = 0;
    if (this.cr >= this.rows) this.cr = this.rows - 1;
    if (this.cc < 0) this.cc = 0;
    if (this.cc >= this.cols) this.cc = this.cols - 1;
  }

  // Handle a complete CSI sequence: params + final byte. Returns nothing (mutates state).
  _csi(paramStr, finalByte) {
    // Private-mode sequences (ESC[?...h / ESC[?...l) — alt-screen enter/exit clears the grid so a
    // capture reflects the visible screen, not the primary buffer bleed-through.
    if (paramStr.startsWith('?')) {
      const codes = paramStr.slice(1).split(';').map((x) => parseInt(x, 10));
      if (finalByte === 'h' || finalByte === 'l') {
        if (codes.some((c) => c === 1049 || c === 47 || c === 1047)) {
          for (let r = 0; r < this.rows; r += 1) this.grid[r] = blankRow(this.cols);
          this.cr = 0; this.cc = 0;
        }
      }
      return;
    }
    const params = paramStr.split(';').map((x) => (x === '' ? null : parseInt(x, 10)));
    const p0 = params[0];
    const n = Number.isInteger(p0) ? p0 : null;
    switch (finalByte) {
      case 'H': case 'f': {
        const row = (Number.isInteger(params[0]) ? params[0] : 1) - 1;
        const col = (Number.isInteger(params[1]) ? params[1] : 1) - 1;
        this.cr = row; this.cc = col; this._clamp(); break;
      }
      case 'A': this.cr -= (n || 1); this._clamp(); break;
      case 'B': this.cr += (n || 1); this._clamp(); break;
      case 'C': this.cc += (n || 1); this._clamp(); break;
      case 'D': this.cc -= (n || 1); this._clamp(); break;
      case 'E': this.cr += (n || 1); this.cc = 0; this._clamp(); break;
      case 'F': this.cr -= (n || 1); this.cc = 0; this._clamp(); break;
      case 'G': this.cc = (n || 1) - 1; this._clamp(); break;
      case 'd': this.cr = (n || 1) - 1; this._clamp(); break;
      case 'J': this._eraseInDisplay(n || 0); break;
      case 'K': this._eraseInLine(n || 0); break;
      case 'm': break; // SGR colour/attrs — parsed and dropped (text-capture scope)
      default: break; // unhandled CSI — skipped, never mis-placed
    }
  }

  write(chunk) {
    const s = this.pending + (Buffer.isBuffer(chunk) ? this.decoder.write(chunk) : String(chunk));
    this.pending = '';
    this.bytesConsumed += Buffer.byteLength(chunk);
    let i = 0;
    const len = s.length;
    while (i < len) {
      const ch = s[i];
      const code = s.charCodeAt(i);
      if (ch === '\x1b') {
        // Need at least the introducer; hold if incomplete.
        if (i + 1 >= len) { this.pending = s.slice(i); return; }
        const next = s[i + 1];
        if (next === '[') {
          // CSI: ESC [ params... finalByte(0x40-0x7E)
          let j = i + 2;
          while (j < len) {
            const c = s.charCodeAt(j);
            if (c >= 0x40 && c <= 0x7e) break; // final byte
            j += 1;
          }
          if (j >= len) { this.pending = s.slice(i); return; } // incomplete CSI
          const paramStr = s.slice(i + 2, j);
          const finalByte = s[j];
          this._csi(paramStr, finalByte);
          i = j + 1;
          continue;
        }
        if (next === ']') {
          // OSC: ESC ] ... (BEL | ESC \)
          let j = i + 2;
          let terminated = false;
          while (j < len) {
            if (s.charCodeAt(j) === 0x07) { j += 1; terminated = true; break; }
            if (s[j] === '\x1b' && j + 1 < len && s[j + 1] === '\\') { j += 2; terminated = true; break; }
            j += 1;
          }
          if (!terminated) { this.pending = s.slice(i); return; }
          i = j;
          continue;
        }
        // Other 2-byte escapes (ESC ( 0, ESC =, ESC >, ESC M, ...): skip the escape + one byte.
        i += 2;
        continue;
      }
      if (code === 0x0a) { this._lf(); i += 1; continue; }        // LF
      if (code === 0x0d) { this.cc = 0; i += 1; continue; }       // CR
      if (code === 0x08) { this.cc = Math.max(0, this.cc - 1); i += 1; continue; } // BS
      if (code === 0x09) { this.cc = Math.min(this.cols - 1, (Math.floor(this.cc / TAB) + 1) * TAB); i += 1; continue; } // TAB
      if (code === 0x07) { i += 1; continue; }                    // BEL — ignore
      if (code < 0x20) { i += 1; continue; }                      // other C0 — ignore
      this._putChar(ch);
      i += 1;
    }
  }

  // The current rendered screen: rows joined, each right-trimmed; trailing blank lines dropped.
  render() {
    const lines = this.grid.map((row) => row.join('').replace(/\s+$/u, ''));
    let last = lines.length - 1;
    while (last >= 0 && lines[last] === '') last -= 1;
    return lines.slice(0, last + 1).join('\n');
  }
}

module.exports = { VtModel, DEFAULT_ROWS, DEFAULT_COLS };
