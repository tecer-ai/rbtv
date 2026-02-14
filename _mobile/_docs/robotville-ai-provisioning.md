# Robotville.ai Site Provisioning (Netlify)

> **Purpose:** Step-by-step instructions to create the Netlify site and attach the robotville.ai custom domain. Execute once; p6-2 configures deploy credentials on the VPS.

---

## Prerequisites

- Netlify account (user has one).
- Domain robotville.ai owned and manageable (registrar or DNS access).

---

## Step 1 — Create the Netlify Site

1. Log in at [app.netlify.com](https://app.netlify.com).
2. **Add new site** → **Deploy manually** (no git required for initial setup).
3. Optionally drag-and-drop a single file (e.g. `index.html` with "Coming soon") to get a live URL, or leave empty — site can be updated later via CLI.
4. Note the **Site name** and **Site ID** (e.g. in Site settings → General → Site information). The **Site ID** is required for CLI deploys with `--site <site-id>` if you have multiple sites.

---

## Step 2 — Add Custom Domain robotville.ai

1. In the site: **Domain settings** → **Add custom domain** (or **Add domain alias**).
2. Enter `robotville.ai` and optionally `www.robotville.ai`.
3. Choose one:
   - **Netlify DNS (recommended):** Netlify provides nameservers. In your registrar, set the domain's nameservers to those Netlify shows. Netlify then creates the required A/CNAME records.
   - **External DNS:** Netlify shows the target (e.g. `xxx.netlify.app` or load balancer). In your current DNS provider, add:
     - **A** record for `@` (apex) → Netlify's load balancer IP (from Netlify docs).
     - **CNAME** for `www` → `xxx.netlify.app` (your site's Netlify subdomain).
4. Wait for DNS propagation (minutes to hours). In Netlify, **Verify DNS configuration** until it reports success.
5. **HTTPS:** Netlify provisions a certificate automatically once DNS is verified. Ensure **HTTPS** is enabled for the custom domain.

---

## Step 3 — Verify Domain and HTTPS

1. Open `https://robotville.ai` in a browser (and `https://www.robotville.ai` if configured).
2. Confirm the page loads and the connection is HTTPS (padlock).
3. If the site is still empty, a placeholder is fine — p6-3 adds the real home page; p6-4 adds the deploy command.

---

## Step 4 — Obtain Netlify Auth Token (for p6-2)

For VPS/Nanobot to deploy via CLI without interactive login:

1. Netlify dashboard → **User settings** → **Applications** → **Personal access tokens** (or **Team** → **Access tokens**).
2. **New access token** — name it (e.g. `robotville-vps-deploy`), create.
3. Copy the token once; store it securely. p6-2 will document where to put it on the VPS (e.g. in `/etc/robotville/nanobot-gateway.env` or a deploy-only env file) as `NETLIFY_AUTH_TOKEN`.
4. Do not commit the token to git.

---

## Checklist

| Step | Action | Done |
|------|--------|------|
| 1 | Create Netlify site (Deploy manually) | |
| 2 | Add custom domain robotville.ai; configure DNS (Netlify or external) | |
| 3 | Verify DNS and HTTPS for https://robotville.ai | |
| 4 | Create personal access token for CLI; store securely for p6-2 | |

---

## References

- [Netlify custom domains](https://docs.netlify.com/domains/custom-domains/)
- [Netlify CLI deploy](https://cli.netlify.com/commands/deploy/) — use `--dir` and `--prod` for content deploys.
