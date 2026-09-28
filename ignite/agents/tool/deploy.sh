#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: deploy.sh <commit>" >&2
  echo "  RBTV_DEPLOY     deploy worktree (required)" >&2
  echo "  RBTV_WORKSPACE  workspace root (required)" >&2
  exit 2
}

commit="${1:-}"
deploy="${RBTV_DEPLOY:-}"
workspace="${RBTV_WORKSPACE:-}"
if [[ -z "$commit" || -z "$deploy" || -z "$workspace" || $# -ne 1 ]]; then
  usage
fi

unit_src="$deploy/ignite/agents/units/rbtv-ignite-agents.service"
unit_dir="${XDG_CONFIG_HOME:-$HOME}/.config/systemd/user"
unit_dst="$unit_dir/rbtv-ignite-agents.service"

env_file="$(node -e '
const fs = require("fs");
const path = require("path");
const ws = process.argv[1];
const book = JSON.parse(fs.readFileSync(path.join(ws, "rbtv.json"), "utf8"));
if (!book.env_file || typeof book.env_file !== "string") throw new Error("rbtv.json env_file required");
const rel = book.env_file.trim();
process.stdout.write(path.isAbsolute(rel) ? rel : path.join(ws, rel));
' "$workspace")"

if [[ ! -f "$env_file" ]]; then
  echo "env file missing: $env_file" >&2
  exit 1
fi

old="$(git -C "$deploy" rev-parse HEAD)"
git -C "$deploy" checkout --detach "$commit"
new="$(git -C "$deploy" rev-parse HEAD)"

if [[ -f "$deploy/ignite/package.json" ]] && ! git -C "$deploy" diff --quiet "$old" "$new" -- ignite/package.json; then
  npm ci --omit=dev --prefix "$deploy/ignite"
elif [[ ! -f "$deploy/ignite/package.json" && -d "$deploy/ignite/node_modules" ]]; then
  rm -rf "$deploy/ignite/node_modules"
fi

if [[ ! -f "$unit_src" ]]; then
  echo "unit template missing: $unit_src" >&2
  exit 1
fi

if [[ -z "${PATH:-}" ]]; then
  echo "PATH is empty" >&2
  exit 1
fi

link_bin="$(node -e 'process.stdout.write(require("node:path").join(require("node:os").homedir(), ".rbtv", "bin"))')"

mkdir -p "$unit_dir"
node -e '
const fs = require("fs");
const path = require("path");
const [src, dst, deploy, workspace, envFile, pathValue, linkBin] = process.argv.slice(1);
if (!pathValue) throw new Error("PATH required");
if (!linkBin) throw new Error("link bin required");
const segments = pathValue.split(path.delimiter);
const unitPath = segments.includes(linkBin) ? pathValue : linkBin + path.delimiter + pathValue;
let text = fs.readFileSync(src, "utf8");
const fill = { "@DEPLOY@": deploy, "@WORKSPACE@": workspace, "@ENV_FILE@": envFile, "@PATH@": unitPath };
text = text.replace(/@[A-Z_]+@/g, (token) => {
  if (!Object.prototype.hasOwnProperty.call(fill, token)) throw new Error("unit still has placeholders");
  return fill[token];
});
if (/@[A-Z_]+@/.test(text)) throw new Error("unit still has placeholders");
fs.writeFileSync(dst, text);
' "$unit_src" "$unit_dst" "$deploy" "$workspace" "$env_file" "$PATH" "$link_bin"

systemctl --user daemon-reload
systemctl --user enable rbtv-ignite-agents.service
systemctl --user restart rbtv-ignite-agents.service
echo "$new"
