"""Wireless explainers for Navi Cisco: standards, security, design.

Textbook positions only. Throughput framing is deliberately
honest: the number on the box is a PHY signaling rate shared by
every station on the channel, under ideal conditions — real
TCP throughput lands far below it, and the chip says so instead
of repeating marketing.
"""

STANDARDS = """802.11 generations — the table worth memorizing (CIS 171)

  Standard   Name     Band(s)        Peak PHY rate   Arrived
  802.11a    —        5 GHz          54 Mbps         1999
  802.11b    —        2.4 GHz        11 Mbps         1999
  802.11g    —        2.4 GHz        54 Mbps         2003
  802.11n    Wi-Fi 4   2.4 + 5 GHz    600 Mbps        2009
  802.11ac   Wi-Fi 5   5 GHz only     ~3.5 Gbps*      2013
  802.11ax   Wi-Fi 6   2.4 + 5 GHz    ~9.6 Gbps*      2019
  802.11ax   Wi-Fi 6E  + 6 GHz        ~9.6 Gbps*      2021
  802.11be   Wi-Fi 7   2.4+5+6 GHz    ~46 Gbps*       2024

* Peaks nobody's laptop reaches: they assume the widest channels
(80/160/320 MHz), the most spatial streams (up to 8), and the
densest modulation — a spec-sheet sum across ideal conditions.
The honest framing for exams AND field work: the PHY rate is the
speed of the CONVERSATION, shared by every station on the
channel, half-duplex (one talker at a time per channel), with
protocol overhead on top. Expect real throughput at a fraction
of the headline — half or less under good conditions is normal,
not a fault.

What each generation actually ADDED (this is the testable part):
  n:  MIMO (multiple spatial streams), 40 MHz channels, frame
      aggregation — the first big jump.
  ac: wider channels (80, optionally 160 MHz), 256-QAM, and
      downlink MU-MIMO — but 5 GHz only; a 2.4 GHz 'ac' client
      is really running n.
  ax: OFDMA (one transmission subdivided among stations — the
      headline feature, built for DENSE crowds, not raw speed),
      BSS coloring against co-channel noise, Target Wake Time
      for battery life. 6E is ax with the 6 GHz band unlocked.
  be: 320 MHz channels, Multi-Link Operation (talk on several
      bands at once), 4096-QAM — Wi-Fi 7's exam silhouette; know
      the features, the deployment stories are still young.

Terminology that keeps answers straight: a BSS is one AP plus
its clients, named by a BSSID (the AP radio's MAC) and an SSID
(the human name, which several BSSs can share as an ESS). Bands:
2.4 GHz reaches farther and penetrates better with few, crowded
channels; 5 GHz offers many more channels and cleaner air at
shorter range; 6 GHz is the widest, emptiest space — shortest
range, newest clients only."""

SECURITY = """Wireless security — WPA2 vs WPA3, and the dead (CIS 171)

  WEP        DEAD. RC4 with a 24-bit IV sent in the clear; the
             IVs repeat, the key falls out of captured traffic
             in minutes with published tools. Never configure it,
             and finding it in a scan is a reportable finding, not
             a quaint antique.
  WPA (TKIP) DEAD TOO. A patch over WEP's hardware: TKIP kept
             RC4, added per-packet keys and a message-integrity
             check (Michael) that was itself weak. Deprecated;
             compatibility mode for museums.
  WPA2       The long-serving standard: AES-CCMP encryption
             (real crypto, properly done) with two authentication
             flavors — Personal (one pre-shared key for everyone)
             and Enterprise (802.1X/EAP against a RADIUS server:
             per-user credentials, can be revoked one person at a
             time). Its known scar is KRACK (2017), a key-
             reinstallation attack against the 4-way handshake —
             patched clients are fine; unpatched legacy gear is
             why 'WPA2' alone is no longer the whole answer. A
             PSK is also only as strong as the passphrase: the
             handshake can be captured and attacked OFFLINE, at
             dictionary speed — see hashlab for why that matters.
  WPA3       The current answer. Personal replaces the PSK
             handshake with SAE (Simultaneous Authentication of
             Equals — a Dragonfly PAKE): no offline dictionary
             attack against a captured handshake, and forward
             secrecy, so a key learned later does not decrypt
             yesterday's traffic. Enterprise raises the bar to a
             192-bit security suite. Management frames are
             PROTECTED by default (PMF/802.11w), killing the
             classic deauthentication attack that WPA2 left open.

Modes on the exam: 'WPA2/WPA3 transition mode' lets old and new
clients share an SSID but inherits the weaker side's exposure —
a migration bridge, not a destination. Open networks encrypt
nothing (OWE/'Enhanced Open' adds unauthenticated encryption —
better than nothing, still no identity). Enterprise vocabulary
to keep straight: the SUPPLICANT (client), the AUTHENTICATOR
(the AP/controller), and the AUTHENTICATION SERVER (RADIUS) —
802.1X is a three-actor play, and the AP never sees the user's
password itself."""

DESIGN = """Wireless design — channels, overlap, roaming (CIS 171)

The 2.4 GHz band is 14 channels wide on paper and about THREE
channels wide in truth: each signal spreads ~20 MHz (4-5 channel
numbers), so only 1, 6, and 11 do not overlap each other (in
North America; the channel plan varies by regulatory domain).
Any other combination is two conversations talking over each
other — co-channel and adjacent-channel interference — and the
radios pay for overlap with retransmissions and airtime, the
only currency wireless really has. 1/6/11 is the reuse pattern:
neighboring APs take turns through the three, like a checkerboard.

In 5 GHz the channels are numerous and non-overlapping at
20 MHz, which is WHY 5 GHz designs breathe: more channels means
real channel reuse plans, and the design dial becomes channel
WIDTH — 40/80 MHz channels are faster per conversation but
consume the very channels your reuse plan needed, so dense
deployments often choose 20/40 MHz and buy capacity with more
APs at lower power instead. (6 GHz: same lesson, more room.)

Airtime thinking: Wi-Fi is half-duplex and contention-based —
one station talks per channel at a time, and slow stations talk
LONGEST (a legacy client at 11 Mbps holds the channel ~50x
longer per byte than an ax client). The slowest client on the
channel is everyone's problem; that is why designs raise minimum
basic rates and why one distant, struggling laptop can tax a
whole room.

Roaming is the CLIENT's decision — always. The client watches
its signal (RSSI) decay and chooses when to jump and to whom;
the network can only encourage (band steering toward 5/6 GHz,
and the k/v/r family: 802.11k neighbor reports, 802.11v steering
suggestions, 802.11r fast transition that pre-stages keys so a
roam takes milliseconds instead of a full re-authentication —
r is what makes voice calls survive a hallway walk). Sticky
clients that cling to a far AP at 1 bar are a physics-and-vendor
problem, not a config error: the fix is cell sizing (AP power
matched to coverage intent), not shouting louder with more power
— the client hears a loud AP it cannot answer at range, and
symmetry is what links are made of.

Survey honesty: all of the above is why real WLANs get a site
survey — predictive (floor-plan software) before, and validation
after measuring what the walls actually did. Exam designs are
drawn on clean floors; buildings decline to cooperate."""

TOPICS = {
    "standards": STANDARDS,
    "security": SECURITY,
    "design": DESIGN,
}

HELP = (
    "wireless — 802.11 at CCNA depth.\n"
    "use: cisco wireless standards  generations table (a/b/g/n/"
    "ac/ax/be), bands, honest throughput framing\n"
    "     cisco wireless security   WPA2 vs WPA3, why WEP and "
    "WPA/TKIP are dead, 802.1X actors\n"
    "     cisco wireless design     1/6/11 channel reuse, "
    "airtime, roaming and the k/v/r family"
)


def run(args):
    if not args:
        print(HELP)
        return 0
    name = args[0].lower()
    text = TOPICS.get(name)
    if text is None:
        print("unknown topic %r — topics are: %s. Run 'cisco "
              "wireless' for the list."
              % (args[0], ", ".join(sorted(TOPICS))))
        return 2
    print(text)
    return 0
