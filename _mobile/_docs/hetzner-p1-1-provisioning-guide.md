# p1-1: Hetzner provisioning guide (on the provider)

Step-by-step for **Provision Hetzner project, network, and Ubuntu VPS with SSH-key access and API manageability**. Do this in the Hetzner Cloud Console (and optionally with the API).

---

## Prerequisites (on your machine)

1. **Hetzner account**  
   Sign up at [https://www.hetzner.com/](https://www.hetzner.com/) if needed.

2. **SSH key** (create before adding a server; keys cannot be added to an existing server via the Console):
   ```bash
   ssh-keygen -t ed25519 -C "robotville-vps"
   ```
   - Save to default path (e.g. `~/.ssh/id_ed25519`) or choose a path.
   - Use a passphrase for security.
   - You will need the **public** key (e.g. `~/.ssh/id_ed25519.pub`) in the next step.

---

## 1. Create a project (Console)

1. Go to [https://console.hetzner.com/](https://console.hetzner.com/).
2. Log in.
3. **Create a new project** (or use an existing one):
   - Click **New project** (or open **Projects** and create one).
   - Name it e.g. `robotville` or `robotville-vps`.
   - Confirm. You are now inside that project.

---

## 2. Add your SSH key (Console)

1. In the left menu: **Security** → **SSH keys**.
2. Click **Add SSH key**.
3. **Name**: e.g. `robotville-workstation`.
4. **Public key**: Paste the full contents of your `.pub` file (one line).
5. Save.  
   You must do this **before** creating the server; the Console does not allow adding SSH keys to an existing server later (you can add keys via CLI/API if needed).

---

## 3. Create the Ubuntu VPS (Console)

1. In the left menu: **Servers** → **Add server**.
2. **Location**: Pick a region (e.g. Falkenstein, Nuremberg, Helsinki).
3. **Image**: **Ubuntu** — choose a current LTS (e.g. 24.04).
4. **Type**: Choose a plan (e.g. **Shared vCPU** → CX22 or CAX11 for a small instance).
5. **Networking**:
   - Leave **Public IPv4** and **Public IPv6** enabled so you can reach the server via SSH (or at least IPv4).
   - Optional: under **Networks**, add the server to a **Private network** if you plan to use one (e.g. for later internal services).
6. **Volumes**: Leave empty. The server’s local disk is enough for Nanobot and RBTV; add a Volume later only if you need extra persistent storage.
7. **SSH key**: Select the SSH key you added in step 2.  
   **Important:** If you don’t select one here, you won’t have key-based login and may be locked out once password login is disabled in p1-3.
8. **Name**: e.g. `robotville-vps` or `nanobot-gateway` (must be unique in the project, RFC 1123 style).
9. **Firewalls**: Skip for now (p1-3 will set a baseline).
10. **Backups**: Optional (can enable later).
11. **Cloud config** (cloud-init): If the form requires a value, paste this minimal config (no extra setup; Ubuntu uses defaults):

    ```yaml
    #cloud-config
    # Robotville VPS - minimal; SSH key and defaults only
    ```

    If the field is optional, you can leave it empty. Do not add `runcmd` or package installs here unless you know what you need; p1-3 and later steps configure the server after first boot.
12. Click **Create & buy now**.  
    Wait until the server status is **Running** and note the **IPv4** (and IPv6 if you use it).

---

## 4. Enable API manageability (Console)

1. In the left menu: **Security** → **API tokens**.
2. Click **Generate API token**.
3. **Description**: e.g. `robotville-api` or `robotville-automation`.
4. **Permissions**: **Read & Write** (needed to manage servers, power, etc.).
5. Generate and **copy the token immediately** — the full token is shown only once.  
   Store it somewhere safe (e.g. password manager or env var `HCLOUD_TOKEN`); you will use it for scripts/API and for p1-2 documentation (store only references/secrets policy, not the raw token in the repo).

**Note:** Each API token is tied to **one project**. For another project you need a separate token.

---

## 5. Verify SSH access (your machine)

From your workstation:

```bash
ssh root@<SERVER_IPv4>
```

- Replace `<SERVER_IPv4>` with the server’s public IPv4 from the Console.
- If your key has a non-default path: `ssh -i ~/.ssh/your_key root@<SERVER_IPv4>`.
- First connection: accept the host key fingerprint when prompted.

If you get a shell as `root`, SSH-key access is working. You can then proceed to p1-2 (document server inventory and access) and p1-3 (security baseline).

---

## 6. Optional: verify API (your machine)

With the API token set (e.g. `export HCLOUD_TOKEN=your_token`) and [hcloud CLI](https://github.com/hetznercloud/hcloud-go) installed:

```bash
hcloud server list
```

You should see your new server and its ID, name, and IP. This confirms API manageability.

---

## Checklist (p1-1 done)

- [ ] Project created (or existing one selected).
- [ ] SSH key added in **Security** → **SSH keys**.
- [ ] Ubuntu VPS created with that SSH key and public IPv4 (and optional IPv6 / private network).
- [ ] API token generated and stored safely; API access tested (e.g. `hcloud server list`).
- [ ] SSH login as `root@<IPv4>` works.

After this, you can run **p1-2** (create `robotville-vps-access.md` with server inventory, SSH endpoint, access policy, recovery notes) and **p1-3** (security baseline).
