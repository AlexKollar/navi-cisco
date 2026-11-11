"""Navi Cisco command core: dispatch, top-level help, --test.

Grammar:
    cisco                     list the commands
    cisco <command> -h        one command's help
    cisco acl <scenario> ...  ACL builder + explainer
    cisco vlan <plan>         VLAN plan + config skeleton
    cisco ospf <topic>        basics | config | troubleshoot
    cisco ios [topic]         modes | show | boot | recovery |
                              files | ssh   (no topic = all)
    cisco wireless <topic>    standards | security | design
    cisco --test              self-test

Design law of the series: explain, don't just execute. This chip
is knowledge and config TEXT only — it never touches a network or
a device, and every generated config lands wrapped in the
reasoning a student needs to defend it.
"""

import ipaddress

try:
    from . import acl as acl_mod
    from . import ios as ios_mod
    from . import masks
    from . import ospf as ospf_mod
    from . import vlan as vlan_mod
    from . import wireless as wireless_mod
except ImportError:  # imported outside the package (should not happen)
    from app_cisco import acl as acl_mod
    from app_cisco import ios as ios_mod
    from app_cisco import masks
    from app_cisco import ospf as ospf_mod
    from app_cisco import vlan as vlan_mod
    from app_cisco import wireless as wireless_mod

VERSION = "1.0.0"
USAGE = ('usage: cisco <command> [args]  |  cisco --test\n'
         "commands: acl, vlan, ospf, ios, wireless")

_HELP = {
    "acl": acl_mod.HELP,
    "vlan": vlan_mod.HELP,
    "ospf": ospf_mod.HELP,
    "ios": ios_mod.HELP,
    "wireless": wireless_mod.HELP,
}

_RUNNERS = {
    "acl": acl_mod.run,
    "vlan": vlan_mod.run,
    "ospf": ospf_mod.run,
    "ios": ios_mod.run,
    "wireless": wireless_mod.run,
}

# Commands that answer -h/--help themselves when called bare.
_BARE_HELPS = ("acl", "ospf", "wireless")


def print_list():
    print("Navi Cisco %s — the CCNA companion for CIS 170-172."
          % VERSION)
    print(USAGE)
    print("")
    print("  acl       build an IOS access list (scenario + "
          "placement + implicit deny)")
    print("  vlan      plan VLANs for a department list, config "
          "skeleton included")
    print("  ospf      basics, config skeleton, neighbor "
          "troubleshoot checklist")
    print("  ios       modes, show commands, boot, recovery, "
          "files, SSH")
    print("  wireless  standards, WPA2/WPA3, design and roaming")
    print("")
    print("cisco <command> -h shows one command's help. This "
          "chip is knowledge and config TEXT: it never touches "
          "a network or a device — you review, then paste into "
          "Packet Tracer or your lab gear yourself.")


def _run(argv):
    if not argv:
        print_list()
        return 0
    head = argv[0]
    if head == "--test":
        return self_test()
    if head in ("--help", "-h", "help"):
        print_list()
        return 0
    name = head.lower()
    fn = _RUNNERS.get(name)
    if fn is None:
        print("unknown command %r — run cisco with no arguments "
              "for the list." % head)
        return 2
    rest = argv[1:]
    if any(t in ("-h", "--help") for t in rest) or \
            (not rest and name in _BARE_HELPS):
        print(_HELP[name])
        return 0
    return fn(rest)


def run_command(argv):
    """Entry for root.py. Prints everything; never tracebacks on
    bad input — a chip answers honestly or not at all."""
    try:
        return _run(list(argv))
    except ValueError as exc:
        print("error: " + str(exc))
        return 1
    except Exception as exc:  # a chip in a sandbox stays polite
        print("error: " + str(exc))
        return 1


# -------------------------------------------------------------- self-test

def _raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def _wild(prefix):
    """Wildcard for a prefix length, computed via ipaddress."""
    net = ipaddress.ip_network("10.0.0.0/%d" % prefix)
    return str(net.hostmask)


def _ospf_config():
    return ospf_mod.config_text()


def self_test():
    checks = []

    def add(label, fn):
        checks.append((label, fn))

    # Wildcard truth: the masks module against ipaddress-derived
    # values, for the three prefixes the brief names.
    for prefix, dotted in ((24, "255.255.255.0"), (16, "255.255.0.0"),
                           (27, "255.255.255.224")):
        net = masks.parse_network("192.168.1.0/%d" % prefix)
        add("wildcard for /%d matches ipaddress hostmask" % prefix,
            lambda n=net, p=prefix: masks.wildcard_of(n)
            == str(ipaddress.ip_network("10.0.0.0/%d" % p).hostmask))
        add("netmask /%d is %s" % (prefix, dotted),
            lambda n=net, d=dotted: str(n.netmask) == d)

    # ACL scenarios, captured as data (builders return lines/why/apply).
    import io
    from contextlib import redirect_stdout

    def acl_out(*a):
        buf = io.StringIO()
        with redirect_stdout(buf):
            acl_mod.run(list(a))
        return buf.getvalue()

    host = acl_out("block-host", "192.168.1.50")
    add("acl block-host denies the host before the permit",
        lambda: host.index("deny host 192.168.1.50")
        < host.index("permit any"))
    add("acl block-host carries the implicit-deny warning",
        lambda: "IMPLICIT DENY" in host and "deny any" in host)
    add("acl block-host is a standard list (10)",
        lambda: "access-list 10 deny host 192.168.1.50" in host)
    bnet = acl_out("block-net", "192.168.1.0/24")
    add("acl block-net wildcard is 0.0.0.255",
        lambda: "deny 192.168.1.0 0.0.0.255" in bnet)
    add("acl block-net explains the wildcard arithmetic",
        lambda: "255 minus the mask octet" in bnet)
    web = acl_out("web-only", "192.168.10.0/24")
    add("acl web-only permits 80 before 443 before the deny",
        lambda: web.index("eq 80") < web.index("eq 443")
        < web.index(" deny ip "))
    add("acl web-only source wildcard is 0.0.0.255",
        lambda: "192.168.10.0 0.0.0.255" in web)
    prot = acl_out("protect-server", "192.168.1.10", "www", "https")
    add("acl protect-server permits www+https to the host",
        lambda: "host 192.168.1.10 eq 80" in prot
        and "host 192.168.1.10 eq 443" in prot)
    add("acl protect-server deny is scoped to the server",
        lambda: "deny ip any host 192.168.1.10" in prot)
    add("every ACL output carries the implicit-deny warning",
        lambda: all("IMPLICIT DENY" in o for o in (host, bnet,
                                                   web, prot)))
    add("acl unknown scenario refused in plain words",
        lambda: acl_out("bogus").startswith("unknown scenario"))
    add("acl bad host refused in plain words",
        lambda: acl_out("block-host", "999.1.1.1")
        .startswith("error:"))

    # VLAN plan determinism and shape.
    rows1 = vlan_mod.build_plan("eng,sales,iot")
    rows2 = vlan_mod.build_plan("eng,sales,iot")
    sig = lambda rows: [(r["id"], r["name"], str(r["subnet"]))
                        for r in rows]
    add("vlan plan is deterministic",
        lambda: sig(rows1) == sig(rows2))
    add("vlan ids step 10, 20, 30 in the order given",
        lambda: [r["id"] for r in rows1] == [10, 20, 30]
        and [r["name"] for r in rows1] == ["ENG", "SALES", "IOT"])
    add("vlan subnets carve in order from 10.10.0.0/16",
        lambda: [str(r["subnet"]) for r in rows1]
        == ["10.10.0.0/24", "10.10.1.0/24", "10.10.2.0/24"])
    add("vlan oversize earns a /23 from 10.20.0.0/16",
        lambda: str(vlan_mod.build_plan("hq:900")[0]["subnet"])
        == "10.20.0.0/23")
    add("vlan duplicate department refused",
        lambda: _raises(lambda: vlan_mod.build_plan("eng,eng")))

    # Every topic key resolves to real text.
    add("ospf topics resolve",
        lambda: all(len(ospf_mod.TOPICS[k]()) > 400
                    for k in ("basics", "config", "troubleshoot")))
    add("ios sections resolve",
        lambda: all(len(t) > 400 for t in ios_mod.SECTIONS.values()))
    add("wireless topics resolve",
        lambda: all(len(t) > 400
                    for t in wireless_mod.TOPICS.values()))
    add("ospf config network statement wildcard is computed",
        lambda: "network 192.168.1.0 0.0.0.255 area 0"
        in _ospf_config())
    add("ospf config /30 wildcard is 0.0.0.3",
        lambda: "network 10.1.1.0 0.0.0.3 area 0" in _ospf_config())

    passed = 0
    for label, fn in checks:
        try:
            ok = bool(fn())
            detail = ""
        except Exception as exc:
            ok = False
            detail = ": " + str(exc)
        print("%s %s%s" % ("PASS" if ok else "FAIL", label, detail))
        if ok:
            passed += 1
    print("self-test: %d/%d passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1
