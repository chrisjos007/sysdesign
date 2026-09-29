# Phase 3 — Network & DNS

[← Phase 2](02-aws-ec2.md) · [Guide home](../../AWS_K8S_DEPLOYMENT.md) · Next: [Phase 4 →](04-vm-baseline.md)

**Goal:** `sysdesignquest.duckdns.org` always points at the instance, even after stop/start, and port 80 is proven reachable from the internet.
**Time:** ~20 minutes.

---

## Background: one firewall, one moving IP

```
Internet ──► [ Security group ] ──► instance ──► k3s / Traefik
              AWS, outside the VM
```

- **Only one firewall matters:** the security group from Phase 2. Ubuntu's EC2 image ships with no restrictive host firewall, and k3s manages its own iptables rules, so there's nothing to open inside the VM.
- **The public IP changes** on every stop/start. Instead of paying for an Elastic IP (billed even while stopped), a small systemd timer on the instance tells DuckDNS its current IP at boot and every 5 minutes after.

---

## Step 3.1 — Confirm there's no host firewall in the way

**Where:** 🐧 VM (still logged in by IP from Phase 2)

```bash
sudo ufw status
sudo iptables -S | head
```

**Expected:** `Status: inactive`, and the iptables output shows only the default policies (`-P INPUT ACCEPT`, `-P FORWARD ACCEPT`, `-P OUTPUT ACCEPT`) and no REJECT/DROP rules.

**If `ufw` is active:** `sudo ufw disable`. The security group is the firewall in this setup, and ufw would break pod networking.

- [ ] No host firewall active

---

## Step 3.2 — Store your DuckDNS token on the instance

**Where:** 🐧 VM

```bash
read -rsp 'DuckDNS token: ' t; echo
printf 'DUCKDNS_TOKEN=%s\n' "$t" | sudo tee /etc/duckdns.env > /dev/null; unset t
sudo chmod 600 /etc/duckdns.env
sudo ls -l /etc/duckdns.env
```

Paste the token from your password manager (Phase 1.3) at the prompt. Nothing is shown while you paste.

**Expected:** `-rw------- 1 root root … /etc/duckdns.env`, readable by root only.

- [ ] Token file exists with mode `-rw-------`

---

## Step 3.3 — Create the DuckDNS updater service and timer

**Where:** 🐧 VM

```bash
sudo tee /etc/systemd/system/duckdns.service > /dev/null <<'EOF'
[Unit]
Description=Update DuckDNS with this instance's public IP
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/duckdns.env
# An empty ip= makes DuckDNS use the address the request came from,
# i.e. this instance's current public IP. "$$" passes a literal "$" through
# systemd, so the shell (not systemd) expands the token variable.
ExecStart=/bin/sh -c 'curl -fsS --retry 5 --retry-delay 5 "https://www.duckdns.org/update?domains=sysdesignquest&token=$${DUCKDNS_TOKEN}&ip=" | grep -qx OK'
EOF

sudo tee /etc/systemd/system/duckdns.timer > /dev/null <<'EOF'
[Unit]
Description=Refresh DuckDNS at boot and every 5 minutes

[Timer]
OnBootSec=30s
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now duckdns.timer
sudo systemctl start duckdns.service
systemctl status duckdns.service --no-pager | head -5
```

How it works:
- **`duckdns.service`** runs once: it calls the DuckDNS update URL with your token. DuckDNS answers `OK` or `KO`, and `grep -qx OK` makes the service **fail** on `KO`, so a bad token shows up as a failed unit rather than silently.
- **`duckdns.timer`** starts the service 30 s after every boot, then every 5 minutes.

**Expected:** the status shows `Active: inactive (dead)` and `status=0/SUCCESS`. "Inactive" is normal for a one-shot service that finished.

**If it shows `status=1/FAILURE`:** `journalctl -u duckdns.service --no-pager | tail` shows why. It's usually a wrong token (DuckDNS answered `KO`). Fix it with `sudoedit /etc/duckdns.env`.

```bash
systemctl list-timers duckdns.timer --no-pager
```
This shows when the next run is due.

- [ ] Service succeeded; timer listed

---

## Step 3.4 — Check DNS from Windows and switch to the alias

**Where:** 🪟 Windows

```powershell
Resolve-DnsName sysdesignquest.duckdns.org
```

**Expected:** an `A` record with the instance's current public IP (the one in the EC2 console). DuckDNS answers with a 60-second TTL, so allow up to a minute.

Now log out of the IP-based session (`exit`) and use the alias from Phase 2.8 from here on:
```powershell
ssh quest-vm
```

- [ ] DNS shows the instance IP; `ssh quest-vm` works

---

## Step 3.5 — Prove port 80 is reachable end to end

**Where:** 🐧 VM. Start a throwaway web server on port 80 (it runs in the foreground):
```bash
cd /tmp && sudo python3 -m http.server 80
```

**Where:** 🪟 Windows (a second PowerShell window)
```powershell
curl.exe -I http://sysdesignquest.duckdns.org
```

**Expected:** `HTTP/1.0 200 OK`, and a log line appears in the VM window.

**Where:** 🐧 VM → press **Ctrl+C** to stop the server.

**If it times out:** the security group's HTTP rule is missing (Phase 2.5). A timeout means it was dropped by a firewall; "connection refused" means it reached the VM but nothing was listening.

- [ ] `200 OK` from Windows

---

## Step 3.6 — Prove the IP follow-up works (stop/start test)

Do this once now, so you trust it later.

1. ☁️ **EC2** → Instances → select `sysdesign-k3s` → **Instance state** → **Stop instance**. Wait for **Stopped**.
2. ☁️ **Instance state** → **Start instance**. Wait for **Running** and note the **new** public IP. It differs from before.
3. 🪟 Wait ~1 minute, then:
   ```powershell
   Resolve-DnsName sysdesignquest.duckdns.org
   ssh quest-vm "uptime"
   ```

**Expected:** DNS returns the **new** IP, and `ssh quest-vm` connects without you changing anything.

- [ ] DNS follows the new IP automatically after a restart

---

## ✅ Checkpoint

- [ ] Security group: 22 (My IP), 80, 443 only
- [ ] No host firewall active
- [ ] DuckDNS updater runs at boot and every 5 min; survives a stop/start
- [ ] Port-80 test succeeded from Windows
- [ ] `ssh quest-vm` works by name
