# Robotville.ai + Netlify — Full Walkthrough

> **Purpose:** Single walkthrough for (1) provisioning robotville.ai on Netlify and (2) configuring VPS deploy credentials so Nanobot can publish via CLI. Combines p6-1 provisioning and p6-2 VPS credentials.

---

## Part A — Netlify + robotville.ai (do this first)

### A1. Create the Netlify site

1. Log in at **[app.netlify.com](https://app.netlify.com)**.
2. **Add new site** → **Deploy manually** (no git needed).
3. Optional: drag the **`_mobile/_docs/netlify-placeholder/`** folder (contains a "Coming soon" `index.html`) into Netlify so the site has a URL; you can replace it later via CLI.
4. Open **Site configuration** (or **Site settings**) → **General** → **Site information**.
5. Note:
   - **Site name** (e.g. `robotville`)
   - **Site ID** (e.g. `abc123-def456-...`) — needed for CLI if you have more than one site.

### A2. Add custom domain robotville.ai

1. In the site: **Domain management** (or **Domain settings**) → **Add custom domain** / **Add domain alias**.
2. Enter **robotville.ai** and, if you want, **www.robotville.ai**.
3. Choose how to manage DNS:

   **Option A — Netlify DNS (simplest)**  
   - Netlify will show 4 nameservers (e.g. `dns1.p01.nsone.net`).  
   - In your **domain registrar** (where you bought robotville.ai), find "DNS" / "Nameservers" and set them to these 4.  
   - Save. Netlify will create the right A/CNAME records.  
   - Wait for DNS to propagate (often 5–30 minutes).

   **Option B — Keep DNS at your current provider**  
   - Netlify will show what to add (e.g. "Add an A record for `@`" and "Add CNAME for `www`").  
   - In your DNS provider, add:
     - **A** for `@` (apex) → Netlify's load balancer IP (see [Netlify DNS docs](https://docs.netlify.com/dns/overview/)).
     - **CNAME** for `www` → `<your-site>.netlify.app`.  
   - Save and wait for propagation.

4. In Netlify, run **Verify DNS configuration** until it succeeds.
5. Turn on **HTTPS** for the custom domain (Netlify usually does this once DNS is verified).

### A3. Check that the site is live

1. Open **https://robotville.ai** (and **https://www.robotville.ai** if you added it).
2. Confirm the page loads and the padlock shows HTTPS.
3. Empty or "Coming soon" is fine — p6-3/p6-4 will add the real content and deploy flow.

### A4. Create a Netlify auth token (for the VPS)

1. In Netlify: **User settings** (avatar → **User settings**) → **Applications** → **Personal access tokens**  
   (or, for a team: **Team** → **Access** / **Access tokens**).
2. **New access token** (or **Create token**).
3. Name it (e.g. `robotville-vps-deploy`), create, and **copy the token once**.
4. Store it somewhere safe (password manager). You'll put it on the VPS in Part B.  
   Do not commit it to git.

---

## Part B — VPS deploy credentials (p6-2)

You need SSH access to the Robotville VPS and the **Site ID** from A1 and the **auth token** from A4.  
**Site name and Site ID** are recorded in `_mobile/_docs/netlify-site-info.md` so you can continue in another session.

### B1. Install Netlify CLI on the VPS

SSH in, then install the CLI so the `nanobot` user can run it:

```bash
# As root or with sudo
sudo npm install -g netlify-cli
# Or with a specific version:
# sudo npm install -g netlify-cli@17
```

Check:

```bash
netlify --version
```

If you prefer not to install globally, you can use `npx netlify deploy ...` from a directory that has `netlify-cli` in package.json; for a single global install, the above is usually enough.

### B2. Add Netlify env vars to the gateway env file

The Nanobot process (and any deploy script it runs) need `NETLIFY_AUTH_TOKEN`. Optionally set `NETLIFY_SITE_ID` if you have multiple sites.

1. On the VPS, edit the env file:
   ```bash
   sudoedit /etc/robotville/nanobot-gateway.env
   ```
2. Append (replace with your real token and, if needed, site ID):
   ```bash
   # Netlify deploy (p6-2) — for Nanobot deploy command
   NETLIFY_AUTH_TOKEN=nfp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   # Optional: required only if you have multiple Netlify sites
   # NETLIFY_SITE_ID=abc123-def456-...
   ```
3. Keep permissions and ownership as they are:
   ```bash
   sudo chown root:nanobot /etc/robotville/nanobot-gateway.env
   sudo chmod 640 /etc/robotville/nanobot-gateway.env
   ```

The `nanobot` user is in group `nanobot`, so it can read this file when you run deploy (e.g. via a script that sources it or when systemd passes it into the process).

### B3. Link the CLI to your site (one-time, as nanobot)

So `netlify deploy` knows which site to use:

```bash
sudo -u nanobot env HOME=/srv/nanobot bash -c '
  export NETLIFY_AUTH_TOKEN="nfp_YOUR_TOKEN_HERE"
  netlify link --id YOUR_SITE_ID
'
```

Use the **Site ID** from A1. When prompted for a "name" you can press Enter. This writes the link into `/srv/nanobot/.config/netlify/` (or similar under `HOME`).

If you prefer not to link, you can pass the site every time:  
`netlify deploy --dir=... --prod --site=YOUR_SITE_ID` and set `NETLIFY_SITE_ID` in the env file so a deploy script can use `--site "$NETLIFY_SITE_ID"`.

### B4. Test deploy as nanobot

Create a tiny test dir and deploy it to production:

```bash
sudo -u nanobot env HOME=/srv/nanobot bash -c '
  source /etc/robotville/nanobot-gateway.env 2>/dev/null || true
  export NETLIFY_AUTH_TOKEN
  mkdir -p /tmp/netlify-test
  echo "<h1>Test deploy</h1>" > /tmp/netlify-test/index.html
  netlify deploy --dir=/tmp/netlify-test --prod
'
```

If you didn't run `netlify link`, add `--site YOUR_SITE_ID` to the deploy command.

- If it succeeds, you'll see a production URL; open **https://robotville.ai** and you might see "Test deploy" (or the previous content) depending on how Netlify is routing.
- If you get "Not logged in" or "Invalid token", double-check `NETLIFY_AUTH_TOKEN` and that the token is in the env when the command runs.

### B5. Document for p6-4

For the Nanobot deploy command (p6-4), the flow will be:

1. Load `NETLIFY_AUTH_TOKEN` (and optionally `NETLIFY_SITE_ID`) from `/etc/robotville/nanobot-gateway.env`.
2. Run:  
   `netlify deploy --dir=<path-to-project-output> --prod`  
   (and `--site "$NETLIFY_SITE_ID"` if not linked).

Exact paths and routing for `/docs/{project-name}` will be defined in p6-3/p6-4.

---

## Checklist

| Step | Action | Done |
|------|--------|------|
| A1 | Create Netlify site (Deploy manually), note Site ID | |
| A2 | Add domain robotville.ai; set DNS (Netlify or external) | |
| A3 | Verify https://robotville.ai and HTTPS | |
| A4 | Create Netlify personal access token; store securely | |
| B1 | Install Netlify CLI on VPS | |
| B2 | Add NETLIFY_AUTH_TOKEN (and NETLIFY_SITE_ID if needed) to `/etc/robotville/nanobot-gateway.env` | |
| B3 | Run `netlify link --id SITE_ID` as nanobot (or plan to use `--site` every time) | |
| B4 | Test deploy as nanobot (placeholder file → prod) | |

---

## References

- [Netlify custom domains](https://docs.netlify.com/domains/custom-domains/)
- [Netlify CLI deploy](https://cli.netlify.com/commands/deploy/)
- VPS env template: `_mobile/_docs/server-env-template.md`.
