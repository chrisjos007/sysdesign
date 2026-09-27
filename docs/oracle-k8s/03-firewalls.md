# Phase 3 — Firewalls

[← Phase 2](02-oracle-vm.md) · [Guide home](../../ORACLE_K8S_DEPLOYMENT.md) · Next: [Phase 4 →](04-vm-baseline.md)

**Goal:** web traffic can reach the VM, and the VM's own firewall won't break Kubernetes pod networking.
**Time:** ~20 minutes.

> ⚠️ **Do this whole phase before installing k3s** (Phase 5). Step 3.5 saves the firewall rules to disk. Once k3s is running, it adds hundreds of its own rules, and those must never be saved into that file.

---

## Background: two firewalls

```
Internet ──► [ Security List ]  ──►  [ iptables on the VM ]  ──►  process / pod
              OCI, outside VM          inside the VM
```

Traffic has to pass **both**. Oracle's Ubuntu image ships with strict iptables rules:
- **INPUT** allows SSH, then **REJECTs everything else** → ports 80/443 are blocked.
- **FORWARD** **REJECTs everything** → Kubernetes pod traffic, which the kernel *forwards* between the node and the pods, is silently blocked. Symptoms: CoreDNS crash-loops, pods can't resolve names.

You'll open what's needed on both.

---

## Step 3.1 — Open 80 and 443 in the Security List

**Where:** ☁️ ☰ → **Networking** → **Virtual cloud networks** → `sysdesign-vcn` → **Security** tab (or **Security Lists** in the left menu) → **Default Security List for sysdesign-vcn** → **Security rules** → **Add Ingress Rules**

Add **two** rules:

| Field | Rule 1 | Rule 2 |
|---|---|---|
| Stateless | unticked | unticked |
| Source Type | CIDR | CIDR |
| Source CIDR | `0.0.0.0/0` | `0.0.0.0/0` |
| IP Protocol | TCP | TCP |
| Source Port Range | *(blank)* | *(blank)* |
| Destination Port Range | `80` | `443` |
| Description | HTTP (Let's Encrypt + redirect) | HTTPS |

→ **Add Ingress Rules**.

**Expected:** the ingress rules list now shows 22, 80 and 443 (plus Oracle's default ICMP rules).

> **Do NOT open 6443** (the Kubernetes API) or 8080. You'll reach those through SSH only.

- [ ] Ingress rules for 80 and 443 exist

---

## Step 3.2 — (Optional) Restrict SSH to your IP

**Where:** 🌐 Browser → search "what is my ip" → note your IPv4.
**Then:** ☁️ same Security List → edit the rule with destination port **22** → Source CIDR `<your-ip>/32`.

**Trade-off:** SSH is then invisible to the rest of the internet, which means much less bot noise. But if your home IP changes (common with ISPs), you're locked out until you update the rule in the console. Leave it at `0.0.0.0/0` if unsure; SSH with key-only auth is already safe.

- [ ] Decided (restricted, or left open on purpose)

---

## Step 3.3 — Look at the VM's current rules

**Where:** 🐧 VM (`ssh oci`)

```bash
sudo iptables -L INPUT -n --line-numbers
sudo iptables -L FORWARD -n --line-numbers
```

**Expected** (roughly):
```
Chain INPUT (policy ACCEPT)
num  target  prot  source      destination
1    ACCEPT  all   0.0.0.0/0   0.0.0.0/0    state RELATED,ESTABLISHED
2    ACCEPT  icmp  0.0.0.0/0   0.0.0.0/0
3    ACCEPT  all   0.0.0.0/0   0.0.0.0/0
4    ACCEPT  udp   0.0.0.0/0   0.0.0.0/0    udp spt:123
5    ACCEPT  tcp   0.0.0.0/0   0.0.0.0/0    state NEW tcp dpt:22
6    REJECT  all   0.0.0.0/0   0.0.0.0/0    reject-with icmp-host-prohibited

Chain FORWARD (policy ACCEPT)
num  target  prot  source      destination
1    REJECT  all   0.0.0.0/0   0.0.0.0/0    reject-with icmp-host-prohibited
```

**Note the line number of the INPUT `REJECT` rule.** It's `6` above. If yours differs, use your number everywhere Step 3.4 says `6`.

- [ ] REJECT line number noted: ____

---

## Step 3.4 — Open the needed traffic

**Where:** 🐧 VM

Each `-I INPUT 6` **inserts** a rule at position 6, pushing the REJECT down, so the new rules are checked before it.

```bash
# Web traffic
sudo iptables -I INPUT 6 -p tcp -m state --state NEW --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp -m state --state NEW --dport 443 -j ACCEPT

# Pods (10.42.0.0/16) and Service IPs (10.43.0.0/16) must reach the node itself
# (Kubernetes API server, kubelet, DNS)
sudo iptables -I INPUT 6 -s 10.42.0.0/16 -j ACCEPT
sudo iptables -I INPUT 6 -s 10.43.0.0/16 -j ACCEPT

# Pods need the kernel to forward their traffic; remove the blanket reject.
# The Security List remains your outer firewall.
sudo iptables -D FORWARD -j REJECT --reject-with icmp-host-prohibited
```

**If the last command says `Bad rule (does a matching rule exist in that chain?)`:** delete it by line number instead, e.g. `sudo iptables -D FORWARD 1`, using the number from Step 3.3.

**Check:**
```bash
sudo iptables -L INPUT -n --line-numbers
sudo iptables -L FORWARD -n --line-numbers
```

**Expected:** four new ACCEPT rules (10.43…, 10.42…, 443, 80) **above** the REJECT in INPUT, and **no** REJECT in FORWARD.

- [ ] Rules look right

---

## Step 3.5 — Save the rules so they survive reboots

**Where:** 🐧 VM

```bash
sudo netfilter-persistent save
```

**Expected:** a line like `run-parts: executing /usr/share/netfilter-persistent/plugins.d/15-ip4tables save`. The rules are written to `/etc/iptables/rules.v4`.

Check the file:
```bash
sudo grep -E 'dport (80|443)|10\.4[23]\.0\.0|FORWARD' /etc/iptables/rules.v4
```

**Expected:** your 80/443/10.42/10.43 rules appear, and no `-A FORWARD -j REJECT` line.

- [ ] Rules saved

---

## Step 3.6 — Prove port 80 is reachable end to end

**Where:** 🐧 VM. Start a throwaway web server on port 80 (it runs in the foreground):

```bash
cd /tmp && sudo python3 -m http.server 80
```

**Where:** 🪟 Windows (new PowerShell window)
```powershell
curl.exe -I http://sysdesignquest.duckdns.org
```

**Expected:** `HTTP/1.0 200 OK`, and a log line appears in the VM window.

**Where:** 🐧 VM. Press **Ctrl+C** to stop the server.

**If it times out:** the Security List rule (Step 3.1) or the iptables rule (3.4) is missing. A timeout means a firewall dropped the packets. "Connection refused" means they reached the VM but nothing was listening.

- [ ] `200 OK` from Windows

---

## ✅ Checkpoint

- [ ] Security List: 22, 80, 443 open; 6443 **not** open
- [ ] iptables: 80, 443, 10.42/16, 10.43/16 accepted in INPUT; no REJECT in FORWARD
- [ ] Rules saved with `netfilter-persistent save`
- [ ] Port-80 test succeeded from Windows

**Undo, if ever needed:** `sudo iptables-restore < /etc/iptables/rules.v4` reloads the saved set. To start over, re-add the rules removed or added here and re-save.
