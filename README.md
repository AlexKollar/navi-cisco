# Navi Cisco

A CCNA companion chip for Apex, built for the spine of Montco's
Computer Networking and Cyber Security A.A.S.: **CIS 170
Introduction to Networks, CIS 171 Switching/Routing/Wireless
Essentials, and CIS 172 Enterprise Networking, Security and
Automation.**

Navi Cisco is knowledge and config **text** only. It never
touches a network or a device — it builds study material and IOS
configurations you read, understand, and paste into Packet
Tracer or lab gear yourself. Standard library only, fully
offline. Its design law is the series': *explain, don't just
execute* — every generated config carries the reasoning you will
need to defend it in the lab and on the exam.

Subnet and CIDR math belong to the sibling chip **navi-netkit**;
Cisco only computes what ACLs and OSPF statements need (wildcard
masks), and points at netkit for the rest.

## Commands (5, plus `--test`)

```
cisco acl <scenario> [args]   access-list builder + explainer
cisco vlan <plan>             VLAN plan + config skeleton
cisco ospf <topic>            basics | config | troubleshoot
cisco ios [topic]             the IOS survival reference
cisco wireless <topic>        standards | security | design
cisco --test                  self-test (wildcards verified
                              against Python's ipaddress module)
```

`cisco <command> -h` shows one command's help; bare `cisco`
lists the commands.

### acl — scenarios

```
cisco acl block-host 192.168.1.50
cisco acl block-net 192.168.1.0/24
cisco acl web-only 192.168.10.0/24
cisco acl protect-server 192.168.1.10 www https
```

Standard vs extended is chosen on principle (standard filters
source only and sits near the destination; extended matches
ports and sits near the source), wildcard masks are computed —
wildcard = inverse of the subnet mask — and **every** output
ends with the implicit-deny warning: an ACL's invisible last
line drops everything no line permits. `protect-server` takes
service names (`www http https ssh telnet ftp smtp dns pop3
rdp`) or a bare port number; the default is `www` + `https`.

### vlan — deterministic planning

```
cisco vlan eng,sales,iot
cisco vlan eng:120,sales,iot:40      (sizes are host counts)
```

Departments map in the order given to VLAN 10, 20, 30..., each
receiving a /24 carved in order from 10.10.0.0/16; a stated size
over ~250 hosts earns a /23 from 10.20.0.0/16 instead, with the
reason named. The output adds the *why* (broadcast domains,
access vs trunk, the native VLAN and its mismatch trap) and a
config skeleton: VLAN creation, an access-port example, and a
trunk with an off-1 native VLAN.

### ospf

- **basics** — link-state in one sitting: LSDB/SPF, cost, areas
  and the backbone, router-ID selection order, the DR/BDR
  election (multi-access only, priority then router ID,
  non-preemptive), adjacency states down to 2-WAY vs Full.
- **config** — a single-area skeleton with router-id, computed
  wildcard network statements, and passive interfaces, read line
  by line (including what a network statement actually *does*).
- **troubleshoot** — the neighbor-not-forming checklist in
  working order: link, area, timers, authentication, network
  type, duplicate router ID, passive interface, ACL eating the
  multicast, MTU at EXSTART, and why all-2-WAY can be healthy.

### ios — topics: modes, show, boot, recovery, files, ssh

Modes read off the prompt shapes; the essential show commands
each paired with what they *prove*; config-register and boot
basics (0x2102 vs 0x2142); a conceptual password-recovery
outline for lab gear you own; `copy run start`, erase, and
banners; and the SSH enablement ceremony — hostname, domain,
RSA key, local user, VTY lines — the secure way to manage the
box, with the tie to CIS 208's Linux-side SSH when that course
comes.

### wireless — topics: standards, security, design

The 802.11 generations table (a/b/g/n/ac/ax/6E/be) with honest
throughput framing — PHY rates are shared, half-duplex ceilings,
not promises; WPA2 vs WPA3 (SAE, forward secrecy, protected
management frames), why WEP and WPA/TKIP are dead, and the three
802.1X actors; design with 1/6/11 channel reuse, airtime
thinking, and client-decided roaming with the k/v/r helpers.

## Honesty notes

- ACL placement advice follows the textbook rule (standard near
  destination, extended near source) and says so.
- `web-only` is the exam scenario; its output footnotes that the
  list as written also drops DNS and DHCP, and how real designs
  handle that.
- Facts are held to CCNA-exam positions; where a topic is
  platform-variable (password-recovery keystrokes, interface
  naming), the text teaches the transferable moves and says the
  details vary.

## Format

`navi-chip/1` — `root.py` entry adapting Apex's `run(args)` call
to `app_cisco.core.run_command`. Cartridge faces are forged at
install time from the manifest (`terminal` glyph, custom icon).
MIT license (see LICENSE).
