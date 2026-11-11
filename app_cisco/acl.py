"""ACL scenario builder for Navi Cisco.

`acl <scenario> [args]` generates correctly ordered IOS access-list
lines with the reasoning attached: standard vs extended chosen on
principle, wildcard masks computed (never hand-typed), remarks in
the list, the application point named, and the implicit deny —
the invisible last line of every ACL — called out every time.

Scenarios:
    block-host     HOST                 deny one host, permit rest
    block-net      NET/CIDR             deny one network, permit rest
    web-only       NET/CIDR             permit ports 80/443 out only
    protect-server HOST [SERVICE ...]   permit services to a server

Standard ACLs (numbered 1-99, 1300-1999) filter on SOURCE address
only, so they are placed as close to the DESTINATION as possible —
put one near the source and its broad permit-any tail would let
the denied host reach everything else. Extended ACLs (100-199,
2000-2699) match source, destination, protocol and port, so they
sit as close to the SOURCE as possible and drop bad traffic early.
"""

try:
    from . import masks
except ImportError:  # imported outside the package (should not happen)
    from app_cisco import masks

IMPLICIT = (
    "IMPLICIT DENY — read this before you apply anything: every ACL "
    "ends with an invisible 'deny any' (extended: 'deny ip any "
    "any'). Any traffic no line permits is dropped, whether you "
    "wrote that line or not. The permit lines above are what keep "
    "legitimate traffic alive — apply this list without them and "
    "you have built a very effective outage."
)

# Service name -> (protocol, port). The classic CCNA set; IOS itself
# accepts these names in place of numbers, but the number is what
# the exam wants to see you understand.
SERVICES = {
    "www": ("tcp", 80),
    "http": ("tcp", 80),
    "https": ("tcp", 443),
    "ssh": ("tcp", 22),
    "telnet": ("tcp", 23),
    "ftp": ("tcp", 21),
    "smtp": ("tcp", 25),
    "dns": ("udp", 53),
    "pop3": ("tcp", 110),
    "rdp": ("tcp", 3389),
}

DEFAULT_SERVER_SERVICES = ("www", "https")


def build_block_host(host_text):
    host = masks.parse_host(host_text)
    lines = [
        "access-list 10 remark Block %s, permit everything else"
        % host,
        "access-list 10 deny host %s" % host,
        "access-list 10 permit any",
    ]
    why = [
        "Why standard: the rule names one SOURCE host and nothing "
        "else — no destination, no port — so a standard ACL "
        "(1-99) does the whole job and an extended list would be "
        "ceremony.",
        "Why this order: IOS tests lines top-down and stops at the "
        "first match. The deny must come first — permit-any above "
        "it would match the host too and the deny would never be "
        "reached. General lines go below specific ones.",
        "Why 'host': a single host gets the all-zeros wildcard "
        "(every bit must match), and the 'host' keyword writes "
        "exactly that. Wildcard = inverse of the subnet mask; a "
        "/32's inverse is 0.0.0.0.",
    ]
    apply = [
        "Apply it INBOUND on the interface nearest the DESTINATION "
        "side of the traffic you are policing — standard ACLs go "
        "close to the destination. Placed near the source instead, "
        "the host would be blocked from everywhere, not just the "
        "network you meant, because the list cannot name a "
        "destination.",
        "  interface <interface-toward-the-destination>",
        "  ip access-group 10 in",
    ]
    return lines, why, apply


def build_block_net(net_text):
    net = masks.parse_network(net_text)
    lines = [
        "access-list 10 remark Block %s, permit everything else"
        % net,
        "access-list 10 deny %s" % masks.fmt_network_wildcard(net),
        "access-list 10 permit any",
    ]
    why = [
        "Why standard: source-only filtering again — the whole "
        "network is the source, and no destination or port is "
        "named. Standard list, close-to-destination placement.",
        "Wildcard check: the subnet mask of %s is %s, so the "
        "wildcard is its inverse, %s — each wildcard octet is 255 "
        "minus the mask octet. The wildcard's 1-bits ('don't "
        "care') line up exactly with the host portion." % (
            net, net.netmask, net.hostmask),
        "Order: deny the specific network first, then the general "
        "permit — top-down, first match wins.",
    ]
    apply = [
        "Apply it INBOUND on the interface nearest the DESTINATION "
        "side — same standard-ACL rule as block-host, and for the "
        "same reason: the list cannot name a destination, so "
        "position is what aims it.",
        "  interface <interface-toward-the-destination>",
        "  ip access-group 10 in",
    ]
    return lines, why, apply


def build_web_only(net_text):
    net = masks.parse_network(net_text)
    src = masks.fmt_network_wildcard(net)
    lines = [
        "ip access-list extended WEB-ONLY",
        " remark Users in %s: web out, nothing else" % net,
        " permit tcp %s any eq 80" % src,
        " permit tcp %s any eq 443" % src,
        " deny ip %s any" % src,
    ]
    why = [
        "Why extended: the rule names ports — 80 and 443 — and "
        "only an extended ACL can match on protocol and port. "
        "Numbered (100) or named; named is shown because the name "
        "says what the list IS, which is what remarks are for.",
        "Source wildcard: %s (mask %s inverted). Netkit does the "
        "subnet math if you want the long version: ./netkit "
        "subnet." % (net.hostmask, net.netmask),
        "The explicit deny at the end is not required — the "
        "implicit deny would drop everything else anyway — but "
        "writing it makes the intent visible in 'show "
        "access-lists' and gives the deny a counter you can watch. "
        "Know which of your denies are written and which are "
        "inherited.",
    ]
    apply = [
        "Apply it INBOUND on the LAN-facing interface of the "
        "users' gateway — extended ACLs go close to the SOURCE, "
        "so unwanted traffic dies before it crosses the network.",
        "  interface <lan-facing-interface>",
        "  ip access-group WEB-ONLY in",
        "One honest caution: this list also drops DNS (UDP 53) "
        "and DHCP, so names will not resolve and new clients will "
        "not get addresses. Real designs add 'permit udp %s any "
        "eq 53' (and DHCP/bootps where the server is off-subnet) "
        "above the deny. The exam scenario wants web-only; the "
        "field wants the footnote." % src,
    ]
    return lines, why, apply


def build_protect_server(host_text, *service_names):
    host = masks.parse_host(host_text)
    names = [s.lower() for s in service_names] or \
        list(DEFAULT_SERVER_SERVICES)
    bad = [s for s in names
           if s not in SERVICES and not s.isdigit()]
    if bad:
        raise ValueError(
            "unknown service %r — protect-server knows: %s. Or "
            "give a port number, e.g. 'protect-server %s 8080'."
            % (bad[0], ", ".join(sorted(SERVICES)), host_text))
    for s in names:
        if s.isdigit() and not 1 <= int(s) <= 65535:
            raise ValueError(
                "port %s is out of range — ports run 1-65535."
                % s)
    lines = [
        "ip access-list extended PROTECT-SERVER",
        " remark Only the named services may reach %s" % host,
    ]
    for name in names:
        if name.isdigit():
            proto, port = "tcp", int(name)
            label = "port %d" % port
        else:
            proto, port = SERVICES[name]
            label = name
        lines.append(" permit %s any host %s eq %d"
                     % (proto, host, port))
    lines.append(" deny ip any host %s" % host)
    why = [
        "Why extended: destination AND port both matter here — "
        "the definition of an extended list's job.",
        "The final deny names the server as destination, so it "
        "drops everything else TO THE SERVER while leaving "
        "traffic to other destinations untouched — then the "
        "implicit deny waits behind it for everything else this "
        "list is applied to. Scoping a deny to one destination "
        "is the difference between hardening a server and "
        "firewalling a network by accident.",
        "FTP caution, if you permit it: active-mode FTP data "
        "comes BACK from the server's port 20 to a client-chosen "
        "port, and passive FTP uses a server-side range — one "
        "'eq 21' line permits the control channel only. Lab "
        "answers often accept it; production designs plan for "
        "it.",
    ]
    apply = [
        "Apply it INBOUND on the interface where traffic ARRIVES "
        "toward the server (extended: close to the source of the "
        "traffic being filtered, and before the server's segment "
        "where possible).",
        "  interface <interface-toward-incoming-traffic>",
        "  ip access-group PROTECT-SERVER in",
        "Then verify like an operator, not an author: 'show "
        "access-lists' for match counters, and a real connection "
        "attempt to a permitted and a forbidden port.",
    ]
    return lines, why, apply


SCENARIOS = {
    "block-host": (build_block_host, 1),
    "block-net": (build_block_net, 1),
    "web-only": (build_web_only, 1),
    "protect-server": (build_protect_server, None),  # host + services*
}

HELP = (
    "acl — build an IOS access list for a scenario, with the "
    "reasoning.\n"
    "use: cisco acl block-host 192.168.1.50\n"
    "     cisco acl block-net 192.168.1.0/24\n"
    "     cisco acl web-only 192.168.10.0/24\n"
    "     cisco acl protect-server 192.168.1.10 www https\n"
    "Scenarios: block-host HOST | block-net NET/CIDR | web-only "
    "NET/CIDR | protect-server HOST [SERVICE ...] (services: "
    "www, http, https, ssh, telnet, ftp, smtp, dns, pop3, rdp, or "
    "a port number; default www+https).\n"
    "Every list ships with its placement (interface + direction) "
    "and the implicit-deny warning. Standard lists filter source "
    "only and sit near the destination; extended lists match "
    "ports and sit near the source."
)


def run(args):
    if not args:
        print(HELP)
        return 0
    name = args[0].lower()
    if name not in SCENARIOS:
        print("unknown scenario %r — scenarios are: %s. Run "
              "'cisco acl' for the full help."
              % (args[0], ", ".join(sorted(SCENARIOS))))
        return 2
    builder, fixed = SCENARIOS[name]
    rest = args[1:]
    if fixed is not None and len(rest) != fixed:
        print("error: %s takes exactly %d argument(s). Run "
              "'cisco acl' for examples." % (name, fixed))
        return 1
    if fixed is None and not rest:
        print("error: protect-server takes a server address: "
              "cisco acl protect-server 192.168.1.10 www https")
        return 1
    try:
        lines, why, apply_ = builder(*rest)
    except ValueError as exc:
        print("error: " + str(exc))
        return 1
    print("ACL — %s" % name)
    print("")
    for line in lines:
        print(line)
    print("")
    for para in why:
        print(para)
        print("")
    for para in apply_:
        print(para)
    print("")
    print(IMPLICIT)
    return 0
