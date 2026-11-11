"""Shared mask arithmetic for the app_cisco package.

ACLs and OSPF network statements speak in WILDCARD masks, not
subnet masks: a wildcard bit of 1 means "don't care" and 0 means
"must match", so the wildcard is the bitwise inverse of the subnet
mask — wildcard octet = 255 minus the subnet octet. Everything
here goes through Python's ipaddress module, and the chip's
self-test cross-checks these helpers against ipaddress-derived
truth so a hand-typed constant can never quietly drift.
"""

import ipaddress


def parse_network(text):
    """'192.168.1.0/24' -> IPv4Network (host bits tolerated)."""
    try:
        net = ipaddress.ip_network(str(text).strip(), strict=False)
    except ValueError:
        raise ValueError(
            "%r is not a network in CIDR form — a network looks "
            "like 192.168.1.0/24 (address, slash, prefix length)."
            % text)
    if net.version != 4:
        raise ValueError(
            "ACLs and OSPF statements on the CCNA are IPv4 — %r is "
            "IPv6. (IPv6 ACLs are a different command family.)"
            % text)
    return net


def parse_host(text):
    """'192.168.1.50' -> IPv4Address (a single host, no mask)."""
    try:
        addr = ipaddress.ip_address(str(text).strip())
    except ValueError:
        raise ValueError(
            "%r is not an IP address — a host looks like "
            "192.168.1.50 (no mask needed; a single host gets the "
            "all-zeros wildcard)." % text)
    if addr.version != 4:
        raise ValueError(
            "ACLs and OSPF statements on the CCNA are IPv4 — %r "
            "is IPv6." % text)
    return addr


def wildcard_of(net):
    """Wildcard mask string for an IPv4Network."""
    return str(net.hostmask)


def fmt_network_wildcard(net):
    """'192.168.1.0 0.0.0.255' — the form IOS statements take."""
    return "%s %s" % (net.network_address, net.hostmask)
