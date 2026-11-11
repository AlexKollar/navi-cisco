"""OSPF explainers for Navi Cisco: basics, config, troubleshoot.

Exam-level depth, textbook positions only. Wildcards in the config
skeleton are computed from the example networks via the masks
module — never hand-typed — and the self-test re-derives them
against ipaddress.
"""

try:
    from . import masks
except ImportError:  # imported outside the package (should not happen)
    from app_cisco import masks

EXAMPLE_NET = "192.168.1.0/24"
EXAMPLE_NET2 = "10.1.1.0/30"

BASICS = """OSPF basics — the shape of it (CIS 172)

OSPF is a link-state protocol: every router builds the same map
(the LSDB) of its AREA and runs Dijkstra's SPF over that map to
find the cheapest path to every network. Routers flood LINK-STATE
Advertisements (LSAs) describing their links; identical maps in,
identical answers out — that agreement is why link-state
converges cleanly and loops so rarely. Cost is the metric:
cost = reference bandwidth / interface bandwidth (default
reference 100 Mbps, so Fast Ethernet and everything faster all
cost 1 until you raise the reference with auto-cost — a favorite
exam trap).

Areas: a single area is usually area 0, and in multi-area designs
area 0 is the BACKBONE — every other area must connect to it, and
traffic between areas crosses it. Areas bound the flooding: an
LSA storm or a topology change in one area does not make every
router in the company re-run SPF. Small networks (and the CCNA)
live happily in a single area 0.

Router ID: each router picks a 32-bit ID, written like an IP
address. Selection order, memorized cold: (1) a manually set
router-id wins; (2) else the highest IP of any UP loopback; (3)
else the highest IP of any active physical interface. It is
chosen at process start and does not change just because an
interface flapped — which is why setting it by hand is the
professional habit: deterministic elections, readable maps.

DR/BDR elections happen ONLY on multi-access networks (Ethernet
segments — broadcast network type). On point-to-point links
there is no election at all; the two routers simply become full
neighbors. On a multi-access segment:
  - The DR (Designated Router) is the segment's speaker: every
    other router (DROTHERs) forms a FULL adjacency with the DR
    and BDR only, and stays at 2-WAY with each other. That is
    what shrinks a 10-router segment from 45 adjacencies to a
    handful — the entire point of the election.
  - Election: highest OSPF interface PRIORITY wins (default 1;
    set 0 and the router can never be DR/BDR). Ties break on the
    highest ROUTER ID.
  - The election is NON-preemptive: when a better router joins
    later, the sitting DR keeps the job. A DR is replaced only
    when it actually fails (then the BDR steps up and a new BDR
    is elected). Do not reboot a segment expecting a re-vote.
  - DROTHERs reach the DR with multicast to 224.0.0.6 (AllDRouters);
    the DR floods out to 224.0.0.5 (AllSPFRouters).

Adjacency states, in order, because the troubleshoot list leans
on them: Down -> Init (a hello seen, ours not in it yet) ->
2-Way (bidirectional; DR/BDR election happens here, and
DROTHER-to-DROTHER conversations STOP here by design) -> ExStart
(master/slave for database exchange) -> Exchange (DBD packets)
-> Loading (LSRs fill the gaps) -> Full. 'Full with the wrong
router' and 'stuck before Full' are both diagnoses, not moods.
Hello/dead timers on Ethernet default to 10/40 seconds, and
neighbors must agree on them, the area ID, the subnet, and any
authentication before any of this starts."""


def config_text():
    net1 = masks.parse_network(EXAMPLE_NET)
    net2 = masks.parse_network(EXAMPLE_NET2)
    lines = [
        "OSPF config — single area, done properly (CIS 172)",
        "",
        "router ospf 1",
        " router-id 1.1.1.1",
        " network %s area 0" % masks.fmt_network_wildcard(net1),
        " network %s area 0" % masks.fmt_network_wildcard(net2),
        " passive-interface GigabitEthernet0/1",
        "",
        "Reading it line by line:",
        "- 'router ospf 1': the 1 is a PROCESS ID — locally "
        "significant only. Two routers with different process IDs "
        "still become neighbors; the area is what must match, not "
        "the process.",
        "- 'router-id 1.1.1.1': set it by hand (see basics) so "
        "elections and the LSDB are deterministic and readable.",
        "- The network statements use WILDCARD masks: %s is %s "
        "inverted, and %s is %s inverted. A network statement does "
        "not advertise the network — it selects which INTERFACES "
        "run OSPF (interfaces whose IP falls in the statement's "
        "range), and those interfaces' networks are what get "
        "advertised." % (
            net1, net1.netmask, net2, net2.netmask),
        "- Wildcard 0.0.0.0 on a network statement matches exactly "
        "one interface address — the precise, modern habit: "
        "'network 192.168.1.1 0.0.0.0 area 0'. Even cleaner on "
        "current IOS: skip network statements and enable OSPF on "
        "the interface itself with 'ip ospf 1 area 0'. All three "
        "forms are the same skill at CCNA depth.",
        "- 'passive-interface' on the LAN-facing interface: the "
        "network is still advertised, but no hellos are sent — no "
        "adjacencies form toward end devices, no routing chatter "
        "on a segment that has no routers to talk to. Pair it "
        "with 'passive-interface default' and un-passive only the "
        "links that face routers, on bigger designs.",
        "",
        "Prove it afterwards: 'show ip ospf neighbor' (FULL with "
        "the DR and BDR, 2-WAY between DROTHERs), 'show ip ospf "
        "interface brief', 'show ip route ospf' (O routes), and "
        "'show ip protocols' for the process summary.",
    ]
    return "\n".join(lines)


TROUBLESHOOT = """OSPF troubleshoot — neighbor not forming, in checklist order

Work it in this order; each step is cheap and eliminates a whole
family of causes before you touch the expensive ones. The order
mirrors what must agree before hellos can succeed, then what must
succeed for the database exchange.

 1. Layer 1/2 up? 'show ip interface brief' — interface and line
    protocol up on BOTH ends; same subnet and mask on the link.
    No adjacency survives a dead link, and "OSPF is broken" is
    often "the cable is."
 2. Same AREA on the link? The single most common cause. An area
    mismatch means hellos are quietly ignored — check the network
    statements and the interface's area with 'show ip ospf
    interface'.
 3. Hello and dead timers equal? They must match on the segment
    (10/40 by default on Ethernet). A mismatch prints in the
    hello and the neighbor never forms — 'show ip ospf interface'
    shows yours; compare both ends.
 4. Authentication agreeing? Type AND key/secret on both ends.
    Auth mismatch drops hellos the same silent way an area
    mismatch does.
 5. Network types the same? Broadcast on one end and
    point-to-point (or point-to-multipoint) on the other gives
    you a neighbor that flaps, sticks, or forms with wrong
    next-hops — timers differ by type, which alone breaks it.
    'show ip ospf interface' names the type.
 6. Router IDs duplicated? Two routers with the same ID corrupt
    each other's view of the map; set router-ids by hand so this
    is impossible by construction.
 7. Is the interface PASSIVE? A passive interface advertises its
    network but sends no hellos — by design, no neighbor forms.
    Check 'show ip protocols' before suspecting anything deeper.
 8. ACL or firewall eating the multicast? OSPF rides 224.0.0.5 /
    224.0.0.6 (protocol 89). An ACL applied to the link that
    forgets OSPF will pass pings and kill adjacencies — verify
    with 'show access-lists' counters. (Yes, students block their
    own routing protocol. See 'cisco acl'.)
 9. Stuck in EXSTART/EXCHANGE? Now suspect MTU mismatch: DBD
    packets carry the interface MTU, and a mismatch stalls the
    exchange exactly there. Compare interface MTUs on both ends.
10. Stuck at 2-WAY everywhere? On a multi-access segment that is
    NORMAL between DROTHERs — check whether the DR and BDR show
    FULL before calling it a fault.

Tools that earn their keep: 'show ip ospf neighbor' (state per
neighbor), 'debug ip ospf hello' and 'debug ip ospf adj' (live,
noisy, lab-only — debug on production gear is a self-inflicted
outage), and 'clear ip ospf process' when you change a router-id
and need the process to re-pick it (it restarts adjacencies —
that is the point, and the warning)."""

TOPICS = {
    "basics": lambda: BASICS,
    "config": config_text,
    "troubleshoot": lambda: TROUBLESHOOT,
}

HELP = (
    "ospf — OSPF at CCNA depth.\n"
    "use: cisco ospf basics        areas, LSDB/SPF, router ID, "
    "DR/BDR election rules and when they apply\n"
    "     cisco ospf config        single-area config skeleton "
    "(wildcards computed) with line-by-line reading\n"
    "     cisco ospf troubleshoot  neighbor-not-forming checklist "
    "in order: link, area, timers, auth, network type, router "
    "ID, passive, ACL, MTU, 2-WAY"
)


def run(args):
    if not args:
        print(HELP)
        return 0
    name = args[0].lower()
    fn = TOPICS.get(name)
    if fn is None:
        print("unknown topic %r — topics are: %s. Run 'cisco "
              "ospf' for the list."
              % (args[0], ", ".join(sorted(TOPICS))))
        return 2
    print(fn())
    return 0
