# Phase 4 — VM baseline

[← Phase 3](03-firewalls.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 5 →](05-k3s.md)

**Goal:** a patched, auto-updating VM with the repo cloned and a way to survive dropped SSH sessions.
**Time:** ~15 minutes.

---

## Step 4.1 — Patch the OS

**Where:** 🐧 VM

```bash
sudo apt update
sudo apt full-upgrade -y
```

If a purple dialog asks about restarting services or keeping a config file, accept the default (press **Enter**).

- [ ] Upgrade finished without errors

---

## Step 4.2 — Install the basic tools

**Where:** 🐧 VM

```bash
sudo apt install -y git jq tmux unattended-upgrades
sudo timedatectl set-timezone UTC
```

- `git`: to pull your repo.
- `jq`: to read JSON output.
- `tmux`: keeps sessions alive (next step).
- `unattended-upgrades`: automatic security patches.
- UTC time matches Airflow's schedules and makes logs unambiguous.

- [ ] Installed

---

## Step 4.3 — Reboot to load the new kernel

**Where:** 🐧 VM

```bash
sudo reboot
```

Your SSH session closes. Wait ~60 seconds, then reconnect from 🪟 Windows with `ssh oci`.

- [ ] Reconnected after reboot

---

## Step 4.4 — Confirm automatic security updates are on

**Where:** 🐧 VM

```bash
systemctl is-enabled unattended-upgrades
systemctl is-active unattended-upgrades
```

**Expected:** `enabled` and `active`.

- [ ] Both OK

---

## Step 4.5 — Learn the tmux basics (30 seconds)

**Why:** some later steps (Helm installs, image pulls) take minutes. If Wi-Fi blips, a plain SSH session and its running command die with it. Inside tmux, they keep going.

| Action | Keys / command |
|---|---|
| Start a named session | `tmux new -s work` |
| Detach (leave it running) | **Ctrl+B**, then **D** |
| Re-attach after reconnecting | `tmux attach -t work` |
| List sessions | `tmux ls` |

Try it now: `tmux new -s work`, run `top`, detach with **Ctrl+B D**, then `tmux attach -t work`. `top` is still running. Quit `top` with **q**.

- [ ] tmux works

---

## Step 4.6 — Clone the repo onto the VM

**Where:** 🐧 VM

```bash
git clone https://github.com/chrisjos007/sysdesign.git ~/sysdesign
cd ~/sysdesign && git log --oneline -3
```

**Expected:** your latest commits.

**How you'll work from now on:**
1. Create or edit files on 🪟 **Windows** (in VS Code), then commit and push.
2. On 🐧 **VM**: `cd ~/sysdesign && git pull`, then `kubectl apply …`.

That way git always holds the true version of every manifest.

- [ ] Repo cloned

---

## Step 4.7 — Sanity-check disk and memory

**Where:** 🐧 VM

```bash
df -h /
free -h
```

**Expected:** ~95 GB size for `/` and ~11 Gi total memory.

**If `/` shows ~45 GB:** the boot volume wasn't resized at creation. That's fine to continue, but you can grow it later: Block Storage → Boot Volumes → Edit size, then follow the console's rescan instructions.

- [ ] Disk and memory as expected

---

## ✅ Checkpoint

- [ ] OS patched and rebooted
- [ ] Unattended upgrades active
- [ ] tmux works
- [ ] Repo cloned at `~/sysdesign`
