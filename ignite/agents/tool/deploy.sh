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

if ! git -C "$deploy" diff --quiet "$old" "$new" -- ignite/package.json; then
  npm ci --omit=dev --prefix "$deploy/ignite"
fi

if [[ ! -f "$unit_src" ]]; then
  echo "unit template missing: $unit_src" >&2
  exit 1
fi

mkdir -p "$unit_dir"
node -e '
const fs = require("fs");
const [src, dst, deploy, workspace, envFile] = process.argv.slice(1);
let text = fs.readFileSync(src, "utf8");
const fill = { "@DEPLOY@": deploy, "@WORKSPACE@": workspace, "@ENV_FILE@": envFile };
for (const [key, value] of Object.entries(fill)) text = text.split(key).join(value);
if (/@[A-Z_]+@/.test(text)) throw new Error("unit still has placeholders");
fs.writeFileSync(dst, text);
' "$unit_src" "$unit_dst" "$deploy" "$workspace" "$env_file"

systemctl --user daemon-reload
systemctl --user restart rbtv-ignite-agents.service
echo "$new"
