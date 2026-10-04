#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: deploy.sh <commit>" >&2
  echo "  RBTV_DEPLOY     deploy worktree (required)" >&2
  echo "  RBTV_INSTALLATION  installation root (required)" >&2
  exit 2
}

commit="${1:-}"
deploy="${RBTV_DEPLOY:-}"
installation="${RBTV_INSTALLATION:-}"
if [[ -z "$commit" || -z "$deploy" || -z "$installation" || $# -ne 1 ]]; then
  usage
fi

unit_src="$deploy/core/ignite/capabilities/tools/ignite/units/rbtv-ignite-agents.service"
unit_dir="${XDG_CONFIG_HOME:-$HOME}/.config/systemd/user"
unit_dst="$unit_dir/rbtv-ignite-agents.service"

env_file="${installation}/.rbtv/config/env/.env"

if [[ ! -f "$env_file" ]]; then
  echo "env file missing: $env_file" >&2
  exit 1
fi

git -C "$deploy" checkout --detach "$commit"
new="$(git -C "$deploy" rev-parse HEAD)"

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
const [src, dst, deploy, installation, envFile, pathValue, linkBin] = process.argv.slice(1);
if (!pathValue) throw new Error("PATH required");
if (!linkBin) throw new Error("link bin required");
const segments = pathValue.split(path.delimiter);
const unitPath = segments.includes(linkBin) ? pathValue : linkBin + path.delimiter + pathValue;
let text = fs.readFileSync(src, "utf8");
const fill = { "@DEPLOY@": deploy, "@INSTALLATION@": installation, "@ENV_FILE@": envFile, "@PATH@": unitPath };
text = text.replace(/@[A-Z_]+@/g, (token) => {
  if (!Object.prototype.hasOwnProperty.call(fill, token)) throw new Error("unit still has placeholders");
  return fill[token];
});
if (/@[A-Z_]+@/.test(text)) throw new Error("unit still has placeholders");
fs.writeFileSync(dst, text);
' "$unit_src" "$unit_dst" "$deploy" "$installation" "$env_file" "$PATH" "$link_bin"

systemctl --user daemon-reload
systemctl --user enable rbtv-ignite-agents.service
systemctl --user restart rbtv-ignite-agents.service
echo "$new"
