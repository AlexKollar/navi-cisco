"""VLAN plan generator for Navi Cisco.

`vlan eng,sales,iot` (sizes optional: `vlan eng:120,sales,iot:40`)
produces a deterministic plan plus the IOS config skeleton:

- Departments map, IN THE ORDER GIVEN, to VLAN IDs 10, 20, 30...
- Names are uppercased for the plan and the config.
- Each VLAN gets a /24 carved in order from 10.10.0.0/16 — big
  enough for any lab, boring on purpose. The address math is
  netkit's job; this chip only assigns and explains.
- A stated size above ~250 hosts earns a wider suggested subnet
  (next /23s from 10.20.0.0/16) with the reason named.

The explainer covers the parts that fail exams and labs alike:
access vs trunk ports, the native VLAN and its mismatch trap,
and why VLANs exist at all (broadcast domains, not magic walls).
"""

import ipaddress

try:
    from . import masks
except ImportError:  # imported outside the package (should not happen)
    from app_cisco import masks

FIRST_POOL = ipaddress.ip_network("10.10.0.0/16")
WIDE_POOL = ipaddress.ip_network("10.20.0.0/16")

SIZE_LIMIT = 250  # usable hosts a /24 comfortably serves (254)


def parse_plan(spec_text):
    """'eng:120,sales,iot:40' -> [(name, size_or_None), ...]."""
    plan = []
    seen = set()
    for chunk in str(spec_text).split(","):
        chunk = chunk.strip()
        if not chunk:
            raise ValueError(
                "empty department in the list — write departments "
                "comma-separated, e.g. vlan eng,sales,iot")
        if ":" in chunk:
            name, _, size_text = chunk.partition(":")
            name = name.strip()
            try:
                size = int(size_text.strip())
            except ValueError:
                raise ValueError(
                    "size %r after %r is not a number — sizes are "
                    "host counts, e.g. eng:120" % (size_text, name))
            if size < 1:
                raise ValueError(
                    "size for %r must be at least 1 host." % name)
        else:
            name, size = chunk, None
        if not name:
            raise ValueError(
                "a department needs a name — e.g. eng, sales, iot.")
        key = name.lower()
        if key in seen:
            raise ValueError(
                "department %r appears twice — each department "
                "gets one VLAN." % name)
        seen.add(key)
        plan.append((name, size))
    if not plan:
        raise ValueError("no departments given — try: "
                         "cisco vlan eng,sales,iot")
    if len(plan) > 40:
        raise ValueError(
            "%d departments is more than this planner lays out "
            "(40) — split the plan by site or building." % len(plan))
    return plan


def build_plan(spec_text):
    """Deterministic plan rows: dicts with id/name/subnet/wide."""
    plan = parse_plan(spec_text)
    small = list(FIRST_POOL.subnets(new_prefix=24))
    wide = list(WIDE_POOL.subnets(new_prefix=23))
    rows = []
    si = wi = 0
    for idx, (name, size) in enumerate(plan):
        is_wide = size is not None and size > SIZE_LIMIT
        if is_wide:
            subnet = wide[wi]
            wi += 1
        else:
            subnet = small[si]
            si += 1
        rows.append({
            "id": (idx + 1) * 10,
            "name": name.upper(),
            "size": size,
            "subnet": subnet,
            "wide": is_wide,
        })
    return rows


def run(args):
    if not args:
        print(HELP)
        return 0
    if len(args) > 1:
        print("error: vlan takes one comma-separated list — quote "
              "it if your shell splits on commas: cisco vlan "
              "\"eng,sales,iot\"")
        return 1
    try:
        rows = build_plan(args[0])
    except ValueError as exc:
        print("error: " + str(exc))
        return 1
    print("VLAN plan for %s" % args[0])
    print("")
    for row in rows:
        line = "  VLAN %-4d %-12s %s" % (
            row["id"], row["name"], row["subnet"])
        if row["size"] is not None:
            line += "  (~%d hosts)" % row["size"]
        print(line)
    print("")
    if any(r["wide"] for r in rows):
        print("Sizing note: a department over ~250 hosts does not "
              "fit a /24 (254 usable), so oversized departments "
              "were given /23s from 10.20.0.0/16 instead. Netkit "
              "does the full math: ./netkit subnet <address>.")
        print("")
    print("Why VLANs at all: a VLAN is a broadcast domain. Every "
          "host in a VLAN hears every broadcast in it, so VLANs "
          "bound the noise, group people by function instead of "
          "by which floor their desk is on, and give the router "
          "(or Layer 3 switch) a place to police traffic BETWEEN "
          "groups with ACLs — see 'cisco acl'. A VLAN is not a "
          "security wall by itself; it is the wall's floor plan.")
    print("")
    print("Config skeleton (review, then paste device by device):")
    print("")
    print("! --- on the switch: create the VLANs")
    for row in rows:
        print("vlan %d" % row["id"])
        print(" name %s" % row["name"])
    print("!")
    print("! --- access ports: ONE untagged VLAN per port, for "
          "end devices (PCs, printers, phones' data side)")
    print("interface GigabitEthernet0/1")
    print(" switchport mode access")
    print(" switchport access vlan %d" % rows[0]["id"])
    print("!  (repeat per port, with that port's department VLAN)")
    print("!")
    print("! --- trunk port: carries MANY VLANs, tagged, toward "
          "the other switch or the router")
    print("interface GigabitEthernet0/24")
    print(" switchport mode trunk")
    vlan_list = ",".join(str(r["id"]) for r in rows)
    print(" switchport trunk allowed vlan %s" % vlan_list)
    print(" switchport trunk native vlan 99")
    print("")
    print("Access vs trunk — the one-line exam answer: an access "
          "port belongs to exactly one VLAN and tags nothing (the "
          "end device knows no VLANs); a trunk carries many VLANs "
          "and tags frames with 802.1Q headers so the far end "
          "knows which VLAN each frame belongs to — except frames "
          "of the NATIVE VLAN, which cross untagged.")
    print("Native VLAN warnings, plural: (1) both ends of a trunk "
          "must agree on the native VLAN or untagged traffic leaks "
          "into the wrong VLAN and CDP will scold you with a "
          "native-mismatch message — read it, don't ignore it. "
          "(2) Change the native VLAN off VLAN 1 (99 above is a "
          "placeholder with no user ports in it): VLAN-hopping "
          "attacks start from the native VLAN, so the textbook "
          "habit is a native VLAN that carries no users at all.")
    print("And VLAN 1 itself: it exists by default and cannot be "
          "deleted; the standing advice is to put no user ports "
          "in it and let it carry nothing but control traffic.")
    print("Routing between these VLANs is a separate step — a "
          "router-on-a-stick subinterface per VLAN or SVIs on a "
          "Layer 3 switch; 'show vlan brief' and 'show interfaces "
          "trunk' are how you prove the plan landed.")
    return 0


HELP = (
    "vlan — plan VLANs for a department list and get the IOS "
    "skeleton.\n"
    "use: cisco vlan eng,sales,iot\n"
    "     cisco vlan eng:120,sales,iot:40   (sizes are host "
    "counts)\n"
    "Deterministic: departments map in the order given to VLAN "
    "10, 20, 30..., each gets a /24 in order from 10.10.0.0/16 "
    "(a size over ~250 hosts earns a /23 from 10.20.0.0/16). "
    "Output: the plan, the why, and a config skeleton — VLAN "
    "creation, an access-port example, and a trunk with the "
    "native-VLAN rules. Subnet math lives in netkit."
)
