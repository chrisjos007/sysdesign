# Phase 1 — Accounts & local prep

[← Phase 0](00-concepts.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 2 →](02-aws-ec2.md)

**Goal:** everything you need *before* touching AWS: a registry token, a hostname, an API key, an SSH key and working local tools.
**Time:** ~30 minutes.

---

## Step 1.1 — Check your local tools

**Where:** 🪟 Windows

```powershell
ssh -V
git --version
docker version
```

**Expected:**
- `ssh -V` prints something like `OpenSSH_for_Windows_9.x`.
- `git --version` prints a version.
- `docker version` prints both a **Client** and a **Server** section.

**If it fails:**
- `ssh` not found → Settings → System → Optional features → Add a feature → **OpenSSH Client**.
- `docker version` shows only Client and then an error → start **Docker Desktop** from the Start menu, wait for the whale icon to settle, and retry.

- [ ] All three commands work

---

## Step 1.2 — Create a GitHub token for the container registry (GHCR)

**Where:** 🌐 Browser (github.com)

**Why:** Jenkins, and you in Phase 8, push images to `ghcr.io`. GHCR only accepts a **classic** personal access token (PAT), not a fine-grained one.

1. github.com → your avatar (top right) → **Settings**.
2. Left sidebar, at the bottom → **Developer settings**.
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token** → **Generate new token (classic)**.
4. Note: `ghcr-sysdesign-jenkins`.
5. Expiration: **90 days** is a sensible balance. Put a calendar reminder a week before it expires; you'll rotate it in [Phase 15](15-operations.md).
6. Scopes: tick **`write:packages`**. This auto-ticks `read:packages`. Leave everything else unticked.
7. **Generate token** → copy it (`ghp_…`) → save it in your password manager as "GHCR token (Jenkins)".

> The token is shown **once**. If you lose it, delete it and generate a new one.

- [ ] Classic PAT with `write:packages` saved in your password manager

---

## Step 1.3 — Get a hostname from DuckDNS

**Where:** 🌐 Browser (duckdns.org)

**Why:** Let's Encrypt only issues certificates for real DNS names, not bare IPs. DuckDNS gives you a free subdomain.

1. Go to duckdns.org and sign in (GitHub login is fine).
2. In **sub domain**, type `sysdesignquest`, then **add domain**.
3. Leave the IP as-is for now. You'll set it to the VM's IP in Phase 2.
4. Write `sysdesignquest.duckdns.org` into your values sheet as `APP_HOST`.
5. At the top of the DuckDNS page, copy your **token** (a UUID) into your password manager as "DuckDNS token". The instance uses it in Phase 3 to update its own IP on every boot.

The rest of this guide already uses **`sysdesignquest.duckdns.org`** in every command and manifest.

> Using your own domain instead? Create an **A record** for e.g. `quest.yourdomain.com` pointing at the instance's IP in Phase 2 (you'll then need an Elastic IP or your DNS provider's update API instead of the DuckDNS updater), then find-and-replace `sysdesignquest.duckdns.org` with it across this guide and your `k8s/` files.

- [ ] Hostname chosen and noted; DuckDNS token saved

---

## Step 1.4 — Have your Gemini API key ready

**Where:** 🌐 Browser (aistudio.google.com/apikey)

Use the key Render already uses, or create a new one. It's needed in Phase 9. Keep it in your password manager.

- [ ] Gemini key available

---

## Step 1.5 — Create an SSH key for the VM

**Where:** 🪟 Windows

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\quest_vm -C "quest-vm"
```

When asked for a passphrase, **set one**. It protects the key if your PC is compromised. Windows' ssh-agent can remember it, see below.

**Expected:** two new files:
- `$HOME\.ssh\quest_vm`: the **private** key. Never share it or upload it anywhere.
- `$HOME\.ssh\quest_vm.pub`: the **public** key. This is what you give AWS.

Check:
```powershell
Get-Content $HOME\.ssh\quest_vm.pub
```
This prints one line starting with `ssh-ed25519`.

*(Optional)* Avoid retyping the passphrase with the ssh-agent. Run PowerShell **as Administrator** once:
```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
```
Then, in a normal PowerShell:
```powershell
ssh-add $HOME\.ssh\quest_vm
```

- [ ] Key pair created, public key prints

---

## Step 1.6 — Make sure your repo is up to date

**Where:** 🪟 Windows

```powershell
git status
git pull
```

You'll add files to this repo throughout the guide and push them to GitHub. The VM pulls them from there. If `git pull` complains about local changes, commit or stash them first.

- [ ] Local repo in sync with GitHub

---

## ✅ Checkpoint

- [ ] `ssh`, `git`, `docker` all work
- [ ] GHCR classic token saved in your password manager
- [ ] DuckDNS hostname reserved and token saved
- [ ] Gemini key available
- [ ] SSH key pair exists
