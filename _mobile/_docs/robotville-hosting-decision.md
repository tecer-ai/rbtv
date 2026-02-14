# Robotville.ai Hosting Decision

> **Purpose:** Records the Netlify vs GitHub Pages evaluation and the decision to use Netlify for robotville.ai. Used by p6-2 (deploy credentials) and p6-4 (deploy command).

---

## Evaluation Criteria

Requirements from Phase 6:

- **CLI deploy via shell** — Nanobot uses `exec` to run deploy; must be a single command or short script.
- **Per-path routing** — `/docs/{project}` and `/app/{project}` must be independently deployable (docs in this phase; app deferred).
- **Custom domain** — robotville.ai (already owned).
- **Existing account** — User has Netlify account.

---

## Evaluation: Netlify vs GitHub Pages

| Criterion | Netlify | GitHub Pages |
|-----------|---------|--------------|
| CLI deploy via shell | `netlify deploy --dir=<path> --prod` (optional `--auth $NETLIFY_AUTH_TOKEN`) | Requires git push to repo; no single-command deploy of arbitrary directory |
| Per-path routing | Redirects/rewrites in `_redirects` or `netlify.toml`; deploy specific dirs per project | Limited — repo structure dictates paths; no per-project dir deploy |
| Independent path deploys | Yes — deploy any directory; `/docs/{project}` = deploy that project's build | No — full repo or branch deploy only |
| Nanobot `exec` compatibility | Direct — one shell command per deploy | Indirect — git add/commit/push + wait for Actions |
| Custom domain | Native — add domain in UI, DNS or Netlify DNS | Supported via CNAME; repo/branch coupling |
| Existing account | User has Netlify account | Would require new setup |

---

## Decision

**Platform: Netlify.**

**Rationale:**

1. CLI deploy is a single command — Nanobot can run `netlify deploy --dir=<path> --prod` (with auth token in env) without git workflow.
2. Per-path routing matches `/docs/{project-name}` and future `/app/{project-name}` — each can be a separate deploy from a different directory.
3. User already has a Netlify account — no new provider setup.
4. GitHub Pages would require git-based deploys and branch/repo structure, which does not align with "deploy this project's output folder on user command."

---

## CLI Deploy Contract (for p6-2 and p6-4)

- **Command (production):** `netlify deploy --dir=<absolute-path-to-publish-dir> --prod`
- **Auth:** Use `NETLIFY_AUTH_TOKEN` in environment so CLI runs non-interactively (required for VPS/Nanobot `exec`).
- **Site binding:** One Netlify site for robotville.ai; deploys can target different publish directories for `/` (home), `/docs/<project>`, and later `/app/<project>` via path configuration (e.g. `netlify.toml` or subdirectory deploys).

Exact publish paths and path routing (e.g. how `/docs/foo` maps to a deploy) are defined in p6-3 (home page) and p6-4 (deploy command).

---

## References

- Netlify CLI: `netlify deploy --dir=<path> --prod` — [Netlify CLI deploy](https://cli.netlify.com/commands/deploy/)
- Custom domain: Netlify DNS or external DNS with CNAME/A records — [Netlify custom domains](https://docs.netlify.com/domains/custom-domains/)
