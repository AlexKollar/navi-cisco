"""IOS survival reference for Navi Cisco.

`ios` with no argument prints the whole reference; `ios <topic>`
prints one section: modes, show, boot, recovery, files, ssh.
Every show command is paired with what it PROVES — running a
command whose output you cannot interpret is typing, not
operating.
"""

MODES = """Modes — where you are is written in the prompt

  Router>            user EXEC — look, barely touch. Ping, basic
                     show commands, connect onward.
  Router#            privileged EXEC ("enable") — every show
                     command, debug, file operations, reload.
  Router(config)#    global configuration ("configure terminal")
                     — changes that affect the whole device.
  Router(config-if)# interface configuration ("interface gi0/0"
                     from global config) — one interface's world.
  Router(config-line)#  line configuration (console, VTY).
  Router(config-router)# routing-process configuration.

Movement: 'enable' climbs to privileged; 'configure terminal'
steps into global config; naming a thing (interface, line, router
process) steps into its submode; 'exit' backs up one level;
'end' (or Ctrl-Z) jumps straight back to privileged. The prompt
IS the mode display — read it before Enter, because the same
words do different things in different modes: 'ip address' is a
configuration in (config-if)# and nonsense at Router>.

Two habits that save points and networks: '?' everywhere (IOS
helps those who ask), and Tab to complete — an incomplete command
that executes was unambiguous, which is also how IOS teaches you
its grammar. And 'do show ...' runs a show command from inside
any config mode, so you never lose your place to check a fact."""

SHOW = """Show commands — command: what it PROVES

  show running-config     The ACTIVE config in RAM — what the
                          device is doing right now. Not what
                          survives a reboot (that's startup).
  show startup-config     The config in NVRAM — what the device
                          WILL load at boot. Comparing the two is
                          how you know whether your work is saved.
  show version            IOS version, uptime, the CONFIG
                          REGISTER value, why it last booted, and
                          how much RAM/Flash exists. First stop
                          for "what is this box, really."
  show ip interface brief Every interface, its IP, and the two
                          words that matter: Status (layer 1) and
                          Protocol (layer 2). up/up is the only
                          fully healthy pair.
  show interfaces         The deep version: counters, errors,
                          duplex/speed, MTU — where physical and
                          duplex problems confess.
  show ip route           The routing table. The letter at the
                          left is the path's source (C connected,
                          S static, O OSPF...) and a route that
                          is not here does not exist, whatever
                          the config intended.
  show ip ospf neighbor   Adjacencies and their states — FULL
                          with DR/BDR is health; anything stuck
                          short of it is a diagnosis (see the
                          ospf troubleshoot checklist).
  show vlan brief         (switches) Which VLANs exist and which
                          ports are access members of each.
  show interfaces trunk   Which ports are trunking, the native
                          VLAN, and the VLANs allowed and active.
  show mac address-table  (switches) Which MAC lives on which
                          port/VLAN — the switch's learned map.
  show cdp neighbors      Cisco neighbors on each port, and
      detail              detail adds their IPs and IOS version.
                          A lab gift and a disclosure risk —
                          which is why real designs scope it.
  show access-lists       ACLs with per-line MATCH COUNTERS —
                          counters are how you prove a list is
                          (or is not) the thing dropping traffic.
  show ip protocols       Routing processes running, their
                          router IDs, networks, and passive
                          interfaces — the OSPF summary view."""

BOOT = """Boot basics — the config register and the sequence

Boot sequence, in order: POST (hardware self-test) -> the
bootstrap loads IOS from Flash (fallback paths exist: TFTP, then
ROMmon's minimal IOS) -> IOS finds the startup-config in NVRAM
and merges it into RAM as the running-config.

The CONFIG REGISTER is a 16-bit value (shown by 'show version',
default 0x2102) whose boot field — the last hex digit — steers
that sequence:
  0x2102   Normal: boot IOS per the boot system commands (or the
           first IOS in Flash), then LOAD startup-config.
  0x2142   Boot IOS but IGNORE startup-config. This one value is
           the entire password-recovery mechanism — see the
           recovery section.
  0x2101   Boot into the ROMmon/boot helper image (RxBoot).

Change it from global config: 'config-register 0x2142' (or
0x2102 to restore). It takes effect at the NEXT reload, never
immediately — and the classic self-own is forgetting to set it
back, leaving a device that ignores its saved config on every
future boot. If 'show version' does not read 0x2102 on a device
in normal service, that is a finding, not trivia."""

RECOVERY = """Password recovery — the outline, and why it works (lab context)

The concept: if you can touch the console port, the device
trusts you — physical access is the root password of all
networking, which is why real sites lock the rack. The procedure
never reveals the old password; it walks AROUND it:

 1. Console in, power-cycle, and send BREAK during boot to land
    in ROMmon (rommon 1 >).
 2. 'confreg 0x2142' — tell the box to boot ignoring the
    startup-config — then 'reset' (or confreg's own prompt) to
    reboot. The device boots with a factory-empty running-config,
    and every password with it is... not loaded.
 3. 'enable' — no password stands in your way, because none was
    loaded. Now the move that matters: 'copy startup-config
    running-config' merges the saved config IN, passwords and
    all, with you already privileged inside it.
 4. Set NEW passwords ('enable secret', console/VTY lines),
    restore the interfaces the merge left shut ('no shutdown'
    where needed — merged interfaces arrive shut on many
    platforms; check 'show ip interface brief').
 5. 'config-register 0x2102' — skip this and step 2 repeats on
    every future reboot — then 'copy running-config
    startup-config' to save, and reload to prove a clean,
    normal boot.

Exact keystrokes vary a little by platform and terminal (the
Break sequence especially); the five moves above are the
transferable part, and they are what exams test. Every step of
this is a lab-and-owner procedure: on gear you do not own, the
same knowledge is a policy topic, not a technique."""

FILES = """Saving, erasing, banners — the housekeeping set

  copy running-config startup-config
      THE save. RAM -> NVRAM. ('wr' and 'copy run start' are the
      spoken forms.) Until this runs, a power cut deletes your
      whole afternoon.
  copy startup-config running-config
      Merges NVRAM into RAM (used by password recovery; a merge,
      not a replace — stale lines in RAM survive it).
  erase startup-config   (or: write erase)
      Deletes the saved config. The device still runs on its
      running-config until reload — erase + reload is the true
      factory reset of the config (the VLAN database on switches
      is a separate file, vlan.dat — delete it too for a truly
      clean switch).
  reload
      Reboot, with a prompt to save if the config changed.
  banner motd # text #
      The login banner; '#' is the delimiter character (any
      character works — it just cannot appear inside the text).
      A banner is a legal notice and a courtesy label: name the
      owner, state that access is authorized-only, and never —
      ever — write "welcome."

The distinction that ties it together: running-config is the
present tense, startup-config is the future tense. Most "the
router forgot my config" stories are a tense error."""

SSH = """SSH — managing the box the secure way (and the CIS 208 tie-in)

Telnet sends everything, passwords included, in cleartext — on a
security course it is the cautionary tale, not a management
protocol. SSH encrypts the session; enabling it is a small
ceremony with real prerequisites, in this order:

  hostname R1                          (NOT the default
                                        "Router" — key generation
                                        needs a real name)
  ip domain-name lab.local             (the key is named for
                                        hostname.domain)
  crypto key generate rsa              (generates the host key;
      general-keys modulus 2048         2048 bits is the sane
                                        modern choice; the key
                                        existing at all is what
                                        switches SSH on)
  ip ssh version 2                     (v1 is broken history)
  username admin privilege 15 secret <strong-secret>
                                        (a LOCAL user database —
                                        'secret' hashes, unlike the
                                        weakly-obfuscated 'password')
  line vty 0 4
   login local                         (authenticate against
                                        that local database)
   transport input ssh                 (SSH ONLY — telnet is now
                                        refused at the door)

Where it lands in the degree: CIS 170/171 teach this as device
management; if he takes CIS 208 (Linux Operating Systems) the
same ideas return from the other side of the wire — sshd, key
pairs, authorized_keys — and the habit transfers whole: key-based
identity, no cleartext management, secrets hashed at rest. The
verify step for both worlds is the same too: connect from
another device ('ssh -l admin <address>') and prove the refused
protocol is actually refused."""

SECTIONS = {
    "modes": MODES,
    "show": SHOW,
    "boot": BOOT,
    "recovery": RECOVERY,
    "files": FILES,
    "ssh": SSH,
}

HELP = (
    "ios — IOS survival reference.\n"
    "use: cisco ios            the whole reference\n"
    "     cisco ios modes      prompts and what each mode is for\n"
    "     cisco ios show       the essential show commands, each "
    "with what it proves\n"
    "     cisco ios boot       config register and boot sequence\n"
    "     cisco ios recovery   password-recovery outline (lab "
    "context)\n"
    "     cisco ios files      copy run start, erase, banners\n"
    "     cisco ios ssh        SSH enablement, the secure ceremony"
)


def run(args):
    if not args:
        for name in ("modes", "show", "boot", "recovery", "files",
                     "ssh"):
            print(SECTIONS[name])
            print("")
        return 0
    name = args[0].lower()
    text = SECTIONS.get(name)
    if text is None:
        print("unknown topic %r — topics are: %s. Run 'cisco ios' "
              "for the whole reference."
              % (args[0], ", ".join(sorted(SECTIONS))))
        return 2
    print(text)
    return 0
