'use strict';

// The repo root, resolved from this file's own position: lib -> rbtv -> tools ->
// capabilities -> rbtv-cli -> core -> <rbtv root>. `RBTV_ROOT` overrides it, the
// same env-override shape the rest of this family uses — which is also what makes
// the tree probeable from a throwaway copy without editing the real one.
//
// The positional walk is an inference about where this file sits, and it is wrong
// the moment the tool is copied or the layout moves. Callers that need the tree
// name the root they resolved when it is missing, rather than throwing a stack.

const path = require('path');

const RBTV_ROOT = process.env.RBTV_ROOT
  ? path.resolve(process.env.RBTV_ROOT)
  : path.resolve(__dirname, '..', '..', '..', '..', '..', '..');

function rel(abs) {
  return path.relative(RBTV_ROOT, abs).split(path.sep).join('/');
}

module.exports = { RBTV_ROOT, rel };
