"""
generate_dataset_and_dashboard.py — NetSage AI
Generates cases.csv, review_log.csv, and prints dashboard metrics.
"""

import csv
import os
import json
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASES_CSV    = os.path.join(BASE_DIR, "cases.csv")
REVIEW_CSV   = os.path.join(BASE_DIR, "review_log.csv")

# ---------------------------------------------------------------------------
# 1. 30 Troubleshooting Cases
# ---------------------------------------------------------------------------

CASES = [
    # ── VLAN / Trunking (1-5) ───────────────────────────────────────────────
    {
        "case_id": "C01",
        "symptom": "PC in VLAN 10 cannot reach PC in VLAN 20; both are on the same switch.",
        "topology_note": "Single SW1; Fa0/1 access VLAN 10, Fa0/2 access VLAN 20, no router attached.",
        "show_outputs": "show vlan brief: VLAN 10 active Fa0/1 | VLAN 20 active Fa0/2 | show ip interface brief: Vlan10 unassigned YES unset up up",
        "expected_fault": "No inter-VLAN routing device; Layer-2 VLANs are isolated by design.",
        "osi_layer": "Layer 2",
        "concept_tag": "VLAN",
        "severity": "High",
    },
    {
        "case_id": "C02",
        "symptom": "Trunk between SW1 and SW2 passes only VLAN 1 traffic.",
        "topology_note": "SW1 Gi0/1 trunk to SW2 Gi0/1; VLANs 10,20,30 defined on both switches.",
        "show_outputs": "show interfaces Gi0/1 trunk: allowed VLANs 1 | show run: switchport trunk allowed vlan 1",
        "expected_fault": "Trunk allowed-VLAN list not updated; VLANs 10,20,30 pruned.",
        "osi_layer": "Layer 2",
        "concept_tag": "Trunking",
        "severity": "High",
    },
    {
        "case_id": "C03",
        "symptom": "New VLAN 40 ports cannot communicate even within the same switch.",
        "topology_note": "SW1; Fa0/5-Fa0/8 assigned access VLAN 40.",
        "show_outputs": "show vlan brief: VLAN 40 not listed | show run: switchport access vlan 40",
        "expected_fault": "VLAN 40 not created in VLAN database; ports inactive.",
        "osi_layer": "Layer 2",
        "concept_tag": "VLAN",
        "severity": "Medium",
    },
    {
        "case_id": "C04",
        "symptom": "Voice VLAN phones register but data VLAN PCs on same port get no IP.",
        "topology_note": "SW1 Fa0/3 configured as access VLAN 10 voice VLAN 20.",
        "show_outputs": "show interfaces Fa0/3 switchport: Voice VLAN 20 active | Access VLAN 10 inactive",
        "expected_fault": "Port mode set to access instead of multi-VLAN; data VLAN not active on port.",
        "osi_layer": "Layer 2",
        "concept_tag": "Voice VLAN",
        "severity": "Medium",
    },
    {
        "case_id": "C05",
        "symptom": "SW2 does not learn MAC addresses from SW3 after adding a new trunk link.",
        "topology_note": "SW2 Gi0/2 to SW3 Gi0/1; native VLAN mismatch suspected.",
        "show_outputs": "show interfaces Gi0/2 trunk: native vlan 1 | SW3 show interfaces Gi0/1 trunk: native vlan 99",
        "expected_fault": "Native VLAN mismatch (1 vs 99) causing CDP/STP errors and traffic drop.",
        "osi_layer": "Layer 2",
        "concept_tag": "Trunking",
        "severity": "High",
    },
    # ── Inter-VLAN Routing & Default Gateways (6-10) ────────────────────────
    {
        "case_id": "C06",
        "symptom": "PC in VLAN 10 gets IP but cannot ping PC in VLAN 20 through router-on-a-stick.",
        "topology_note": "R1 Gi0/0.10 and Gi0/0.20 sub-interfaces; SW1 trunk to R1.",
        "show_outputs": "show ip interface brief: Gi0/0.10 up/up 192.168.10.1 | Gi0/0.20 up/up 192.168.20.1 | show interfaces trunk: Gi0/0 not in trunk list",
        "expected_fault": "SW1 port connected to R1 not configured as trunk; sub-interfaces receive no tagged frames.",
        "osi_layer": "Layer 3",
        "concept_tag": "Inter-VLAN Routing",
        "severity": "High",
    },
    {
        "case_id": "C07",
        "symptom": "PC1 (192.168.10.5) cannot reach default gateway 192.168.10.1.",
        "topology_note": "R1 Gi0/0 = 192.168.10.1/24; PC1 gateway set to 192.168.1.1 (typo).",
        "show_outputs": "ipconfig: Default Gateway 192.168.1.1 | ping 192.168.10.1: Request timed out",
        "expected_fault": "Wrong default gateway configured on PC1; gateway unreachable.",
        "osi_layer": "Layer 3",
        "concept_tag": "Default Gateway",
        "severity": "Medium",
    },
    {
        "case_id": "C08",
        "symptom": "All VLANs lose inter-VLAN routing after SVI is added to L3 switch.",
        "topology_note": "SW1 L3; SVI Vlan10 and Vlan20 created; ip routing not enabled.",
        "show_outputs": "show ip route: no routes | show run: no ip routing",
        "expected_fault": "ip routing command missing on L3 switch; SVIs created but routing disabled.",
        "osi_layer": "Layer 3",
        "concept_tag": "Inter-VLAN Routing",
        "severity": "High",
    },
    {
        "case_id": "C09",
        "symptom": "Sub-interface Gi0/0.30 is up but VLAN 30 hosts cannot reach router.",
        "topology_note": "R1 Gi0/0.30; encapsulation dot1Q 30 missing.",
        "show_outputs": "show run interface Gi0/0.30: ip address 192.168.30.1 255.255.255.0 | no encapsulation command",
        "expected_fault": "Missing encapsulation dot1Q 30 on sub-interface; tagged frames not processed.",
        "osi_layer": "Layer 3",
        "concept_tag": "Inter-VLAN Routing",
        "severity": "High",
    },
    {
        "case_id": "C10",
        "symptom": "PC in VLAN 50 can ping its SVI but not hosts in other VLANs.",
        "topology_note": "L3 SW; Vlan50 SVI up; Vlan60 SVI admin-down.",
        "show_outputs": "show ip interface brief: Vlan50 up/up | Vlan60 administratively down",
        "expected_fault": "Vlan60 SVI is admin-down; no shutdown needed.",
        "osi_layer": "Layer 3",
        "concept_tag": "Inter-VLAN Routing",
        "severity": "Medium",
    },
    # ── DHCP & DNS (11-15) ───────────────────────────────────────────────────
    {
        "case_id": "C11",
        "symptom": "PCs on VLAN 10 receive 169.254.x.x APIPA addresses.",
        "topology_note": "R1 DHCP server; pool for 192.168.10.0/24; helper-address not set on SVI.",
        "show_outputs": "show ip dhcp pool: pool VLAN10 exists | show run int Vlan10: no ip helper-address",
        "expected_fault": "ip helper-address missing on SVI; DHCP Discover not forwarded to server.",
        "osi_layer": "Layer 3",
        "concept_tag": "DHCP",
        "severity": "High",
    },
    {
        "case_id": "C12",
        "symptom": "DHCP clients get addresses but cannot reach internet; DNS fails.",
        "topology_note": "R1 DHCP pool; dns-server option points to 8.8.4.4 but NAT blocks UDP 53.",
        "show_outputs": "show ip dhcp binding: leases present | show access-lists: deny udp any any eq 53",
        "expected_fault": "ACL blocking UDP port 53 outbound; DNS queries dropped.",
        "osi_layer": "Layer 4",
        "concept_tag": "DNS / ACL",
        "severity": "High",
    },
    {
        "case_id": "C13",
        "symptom": "DHCP pool exhausted; new devices get no IP.",
        "topology_note": "R1 pool 192.168.1.0/24; excluded range too small; 250 clients.",
        "show_outputs": "show ip dhcp pool: utilization 100% | show ip dhcp binding: 253 entries",
        "expected_fault": "DHCP pool exhausted; excluded range or pool size needs adjustment.",
        "osi_layer": "Layer 3",
        "concept_tag": "DHCP",
        "severity": "High",
    },
    {
        "case_id": "C14",
        "symptom": "Clients get IPs from wrong subnet after adding second DHCP pool.",
        "topology_note": "R1 two pools: VLAN10 192.168.10.0/24 and VLAN20 192.168.20.0/24; network statements overlap.",
        "show_outputs": "show ip dhcp pool: Pool VLAN10 network 192.168.10.0 | Pool VLAN20 network 192.168.10.0 (typo)",
        "expected_fault": "VLAN20 pool has wrong network statement; clients get VLAN10 addresses.",
        "osi_layer": "Layer 3",
        "concept_tag": "DHCP",
        "severity": "Medium",
    },
    {
        "case_id": "C15",
        "symptom": "Hostname resolution fails inside the LAN; IP pings work fine.",
        "topology_note": "Internal DNS server 192.168.1.53; clients point to 192.168.1.54 (wrong IP).",
        "show_outputs": "ipconfig /all: DNS Server 192.168.1.54 | nslookup server1: timeout",
        "expected_fault": "Wrong DNS server IP in DHCP options; clients cannot resolve hostnames.",
        "osi_layer": "Layer 7",
        "concept_tag": "DNS",
        "severity": "Medium",
    },
    # ── Static & OSPF Routing (16-20) ────────────────────────────────────────
    {
        "case_id": "C16",
        "symptom": "R2 cannot reach 10.0.3.0/24 network behind R3.",
        "topology_note": "R1-R2-R3 serial links; static route on R2 missing for 10.0.3.0/24.",
        "show_outputs": "show ip route R2: no entry for 10.0.3.0 | show run R2: no ip route 10.0.3.0",
        "expected_fault": "Missing static route on R2 for 10.0.3.0/24 via R3 next-hop.",
        "osi_layer": "Layer 3",
        "concept_tag": "Static Routing",
        "severity": "High",
    },
    {
        "case_id": "C17",
        "symptom": "OSPF neighbours stuck in EXSTART state between R1 and R2.",
        "topology_note": "R1 and R2 FastEthernet link; MTU mismatch 1500 vs 1476.",
        "show_outputs": "show ip ospf neighbor: EXSTART | show interfaces Fa0/0: MTU 1476 bytes",
        "expected_fault": "MTU mismatch prevents OSPF DBD exchange; ip ospf mtu-ignore needed.",
        "osi_layer": "Layer 3",
        "concept_tag": "OSPF",
        "severity": "High",
    },
    {
        "case_id": "C18",
        "symptom": "OSPF routes appear then disappear every 40 seconds.",
        "topology_note": "R1-R2 OSPF area 0; hello/dead timers mismatched.",
        "show_outputs": "show ip ospf interface: Hello 10 Dead 40 on R1 | Hello 30 Dead 120 on R2",
        "expected_fault": "OSPF hello/dead timer mismatch; adjacency flaps.",
        "osi_layer": "Layer 3",
        "concept_tag": "OSPF",
        "severity": "High",
    },
    {
        "case_id": "C19",
        "symptom": "Floating static route takes over even when primary link is up.",
        "topology_note": "R1 primary route AD 1; floating static AD 5; primary interface up.",
        "show_outputs": "show ip route: S 10.0.0.0 [5/0] active | primary interface up/up",
        "expected_fault": "Primary static route missing or misconfigured; floating route incorrectly preferred.",
        "osi_layer": "Layer 3",
        "concept_tag": "Static Routing",
        "severity": "Medium",
    },
    {
        "case_id": "C20",
        "symptom": "R3 not receiving OSPF routes from area 1 into area 0.",
        "topology_note": "R2 ABR between area 0 and area 1; area 1 not defined on R2.",
        "show_outputs": "show ip ospf: R2 area 0 only | show run R2: no network in area 1",
        "expected_fault": "R2 not configured as ABR; area 1 network statement missing.",
        "osi_layer": "Layer 3",
        "concept_tag": "OSPF",
        "severity": "High",
    },
    # ── Standard / Extended ACLs (21-25) ─────────────────────────────────────
    {
        "case_id": "C21",
        "symptom": "All traffic from 192.168.10.0/24 is blocked including permitted hosts.",
        "topology_note": "R1 inbound ACL on Gi0/0; deny statement before permit.",
        "show_outputs": "show access-lists: 10 deny 192.168.10.0 0.0.0.255 (matched) | 20 permit any",
        "expected_fault": "Deny rule placed before permit; all subnet traffic denied due to ACL order.",
        "osi_layer": "Layer 3",
        "concept_tag": "Standard ACL",
        "severity": "High",
    },
    {
        "case_id": "C22",
        "symptom": "FTP (port 21) blocked but HTTP works fine from same host.",
        "topology_note": "R1 extended ACL 101 applied outbound on Gi0/1.",
        "show_outputs": "show access-lists 101: deny tcp any any eq 21 (45 matches) | permit ip any any",
        "expected_fault": "Extended ACL explicitly denying TCP port 21; FTP control channel blocked.",
        "osi_layer": "Layer 4",
        "concept_tag": "Extended ACL",
        "severity": "Medium",
    },
    {
        "case_id": "C23",
        "symptom": "ACL applied but traffic still passes; no matches on deny rule.",
        "topology_note": "R1 ACL 102 created but not applied to any interface.",
        "show_outputs": "show access-lists 102: deny ip 10.0.0.0 0.255.255.255 any (0 matches) | show run: no ip access-group on interfaces",
        "expected_fault": "ACL defined but not applied to interface with ip access-group command.",
        "osi_layer": "Layer 3",
        "concept_tag": "Standard ACL",
        "severity": "Medium",
    },
    {
        "case_id": "C24",
        "symptom": "Guest VLAN can reach internal servers; isolation expected.",
        "topology_note": "R1 ACL for guest VLAN 99 missing; all traffic permitted by default.",
        "show_outputs": "show access-lists: no ACL referencing 172.16.99.0 | show run int Gi0/0.99: no ip access-group",
        "expected_fault": "No ACL applied to guest sub-interface; guest traffic reaches internal subnets.",
        "osi_layer": "Layer 3",
        "concept_tag": "Extended ACL",
        "severity": "Critical",
    },
    {
        "case_id": "C25",
        "symptom": "Return traffic for established TCP sessions blocked by ACL.",
        "topology_note": "R1 inbound ACL permits only specific source IPs; no established keyword.",
        "show_outputs": "show access-lists: permit tcp 192.168.1.0 0.0.0.255 any | no established keyword",
        "expected_fault": "ACL missing 'established' keyword; return TCP packets (ACK set) dropped.",
        "osi_layer": "Layer 4",
        "concept_tag": "Extended ACL",
        "severity": "High",
    },
    # ── NAT/PAT & Wireless LAN (26-30) ───────────────────────────────────────
    {
        "case_id": "C26",
        "symptom": "Internal hosts cannot reach internet after NAT configured on R1.",
        "topology_note": "R1 NAT overload; inside/outside interfaces not marked.",
        "show_outputs": "show ip nat translations: empty | show run: ip nat inside source list 1 interface Gi0/1 overload | no ip nat inside on Gi0/0",
        "expected_fault": "ip nat inside not applied to LAN interface; NAT translations not created.",
        "osi_layer": "Layer 3",
        "concept_tag": "NAT",
        "severity": "High",
    },
    {
        "case_id": "C27",
        "symptom": "Static NAT entry exists but external host cannot reach internal server.",
        "topology_note": "R1 static NAT 203.0.113.10 → 192.168.1.10; ACL blocks inbound on outside interface.",
        "show_outputs": "show ip nat translations: 203.0.113.10 → 192.168.1.10 | show access-lists: deny ip any 203.0.113.0 0.0.0.255",
        "expected_fault": "Inbound ACL on outside interface blocking translated traffic before NAT lookup.",
        "osi_layer": "Layer 3",
        "concept_tag": "NAT / ACL",
        "severity": "High",
    },
    {
        "case_id": "C28",
        "symptom": "PAT stops working after ISP changes public IP; all sessions drop.",
        "topology_note": "R1 PAT using fixed public IP 203.0.113.5; ISP assigned new IP.",
        "show_outputs": "show ip nat translations: no active translations | show run: ip nat inside source list 1 pool MYPOOL",
        "expected_fault": "NAT pool contains old public IP; update pool or use interface keyword for dynamic IP.",
        "osi_layer": "Layer 3",
        "concept_tag": "PAT",
        "severity": "High",
    },
    {
        "case_id": "C29",
        "symptom": "Wireless clients associate to AP but get no IP address.",
        "topology_note": "WLC + AP; SSID mapped to VLAN 30; DHCP scope for VLAN 30 missing on server.",
        "show_outputs": "show wireless client: associated | DHCP server: no scope for 192.168.30.0/24",
        "expected_fault": "DHCP scope for WLAN VLAN 30 not configured; clients get APIPA.",
        "osi_layer": "Layer 3",
        "concept_tag": "Wireless / DHCP",
        "severity": "High",
    },
    {
        "case_id": "C30",
        "symptom": "Wireless clients on guest SSID can reach corporate internal servers.",
        "topology_note": "WLC; guest SSID on VLAN 99; client isolation disabled; no ACL on VLAN 99 SVI.",
        "show_outputs": "show wlan: client isolation disabled | show run int Vlan99: no ip access-group",
        "expected_fault": "Client isolation disabled and no ACL; guest traffic reaches corporate network.",
        "osi_layer": "Layer 2/3",
        "concept_tag": "Wireless Security",
        "severity": "Critical",
    },
]

# ---------------------------------------------------------------------------
# 2. Review Log — simulated AI verdicts + human decisions
#    verdict : Accepted | Edited | Rejected
#    ai_correct: True if AI root-cause matched expected_fault
# ---------------------------------------------------------------------------

REVIEW_LOG = [
    # case_id, ai_root_cause_summary, confidence, verdict, human_note
    ("C01", "No routing device present; VLANs isolated at Layer 2.", "High", "Accepted", ""),
    ("C02", "Trunk allowed-VLAN list restricts to VLAN 1 only.", "High", "Accepted", ""),
    ("C03", "VLAN 40 not in VLAN database; ports inactive.", "High", "Accepted", ""),
    ("C04", "Port mode misconfiguration; data VLAN inactive.", "Medium", "Edited", "AI missed voice-VLAN multi-mode detail; corrected port mode explanation."),
    ("C05", "Native VLAN mismatch causing STP/CDP errors.", "High", "Accepted", ""),
    ("C06", "SW1 uplink to R1 not trunked; sub-interfaces receive no tagged frames.", "High", "Accepted", ""),
    ("C07", "Wrong default gateway on PC1.", "High", "Accepted", ""),
    ("C08", "ip routing not enabled on L3 switch.", "High", "Accepted", ""),
    ("C09", "Missing encapsulation dot1Q on sub-interface.", "High", "Accepted", ""),
    ("C10", "Vlan60 SVI admin-down; no shutdown required.", "High", "Accepted", ""),
    ("C11", "DHCP helper-address missing on SVI.", "High", "Accepted", ""),
    ("C12", "ACL blocking UDP 53; DNS queries dropped.", "Medium", "Edited", "AI initially blamed NAT; human identified ACL deny rule for port 53."),
    ("C13", "DHCP pool exhausted; 253 bindings active.", "High", "Accepted", ""),
    ("C14", "VLAN20 pool has duplicate network statement.", "Medium", "Accepted", ""),
    ("C15", "Wrong DNS server IP in DHCP options.", "High", "Accepted", ""),
    ("C16", "Missing static route on R2 for 10.0.3.0/24.", "High", "Accepted", ""),
    ("C17", "MTU mismatch prevents OSPF DBD exchange.", "High", "Accepted", ""),
    ("C18", "OSPF hello/dead timer mismatch causing adjacency flap.", "High", "Accepted", ""),
    ("C19", "Primary static route missing; floating route active.", "Medium", "Edited", "AI suggested wrong next-hop; human corrected to check primary route config."),
    ("C20", "R2 area 1 network statement missing; not acting as ABR.", "High", "Accepted", ""),
    ("C21", "Deny rule before permit in ACL; all subnet traffic blocked.", "High", "Accepted", ""),
    ("C22", "ACL denying TCP port 21 explicitly.", "High", "Accepted", ""),
    ("C23", "ACL not applied to any interface.", "Medium", "Edited", "AI diagnosed wrong interface direction; human confirmed ACL not applied at all."),
    ("C24", "No ACL on guest sub-interface; unrestricted access.", "High", "Rejected", "AI suggested VLAN issue; human identified missing ACL as root cause."),
    ("C25", "ACL missing established keyword; return traffic dropped.", "Medium", "Accepted", ""),
    ("C26", "ip nat inside not applied to LAN interface.", "High", "Accepted", ""),
    ("C27", "Inbound ACL blocking translated traffic on outside interface.", "Medium", "Edited", "AI blamed NAT order; human confirmed ACL applied before NAT on outside."),
    ("C28", "NAT pool contains outdated public IP.", "High", "Accepted", ""),
    ("C29", "DHCP scope for WLAN VLAN 30 missing.", "High", "Accepted", ""),
    ("C30", "Client isolation disabled; no ACL on guest SVI.", "High", "Accepted", ""),
]

CASES_FIELDNAMES = [
    "case_id", "symptom", "topology_note", "show_outputs",
    "expected_fault", "osi_layer", "concept_tag", "severity",
]

REVIEW_FIELDNAMES = [
    "case_id", "ai_root_cause_summary", "confidence",
    "verdict", "human_note",
]


def write_cases_csv() -> None:
    with open(CASES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CASES_FIELDNAMES)
        writer.writeheader()
        writer.writerows(CASES)
    print(f"[OK] cases.csv written -- {len(CASES)} cases -> {CASES_CSV}")


def write_review_log_csv() -> None:
    with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(REVIEW_FIELDNAMES)
        writer.writerows(REVIEW_LOG)
    print(f"[OK] review_log.csv written -- {len(REVIEW_LOG)} entries -> {REVIEW_CSV}")


# ---------------------------------------------------------------------------
# 3. Dashboard — reads CSVs and prints metrics
# ---------------------------------------------------------------------------

def print_divider(char="-", width=60):
    print(char * width)


def build_dashboard() -> None:
    # ── Load cases ──────────────────────────────────────────────────────────
    if not os.path.exists(CASES_CSV):
        print("[ERROR] cases.csv not found. Run write_cases_csv() first.")
        return
    if not os.path.exists(REVIEW_CSV):
        print("[ERROR] review_log.csv not found. Run write_review_log_csv() first.")
        return

    with open(CASES_CSV, newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    with open(REVIEW_CSV, newline="", encoding="utf-8") as f:
        reviews = list(csv.DictReader(f))

    total = len(cases)
    reviewed = len(reviews)

    # ── OSI layer distribution ───────────────────────────────────────────────
    layer_counts = Counter(c["osi_layer"] for c in cases)

    # ── Concept tag distribution ─────────────────────────────────────────────
    tag_counts = Counter(c["concept_tag"] for c in cases)

    # ── AI vs Human agreement ────────────────────────────────────────────────
    verdict_counts = Counter(r["verdict"] for r in reviews)
    accepted  = verdict_counts.get("Accepted", 0)
    edited    = verdict_counts.get("Edited", 0)
    rejected  = verdict_counts.get("Rejected", 0)
    agreement_pct = round(accepted / reviewed * 100, 1) if reviewed else 0

    # ── Responsible AI log — cases needing human correction ─────────────────
    corrected = [r for r in reviews if r["verdict"] in ("Edited", "Rejected")]
    top5 = corrected[:5]

    # ── Print dashboard ──────────────────────────────────────────────────────
    print()
    print_divider("=")
    print("  NetSage AI -- Dashboard Summary")
    print_divider("=")

    print(f"\n  Total cases in dataset : {total}")
    print(f"  Cases reviewed         : {reviewed}")

    print("\n  Fault Distribution by OSI Layer")
    print_divider()
    for layer, count in sorted(layer_counts.items()):
        bar = "#" * count
        print(f"  {layer:<18} {bar}  ({count})")

    print("\n  Fault Distribution by Concept Tag")
    print_divider()
    for tag, count in tag_counts.most_common():
        bar = "#" * count
        print(f"  {tag:<22} {bar}  ({count})")

    print("\n  AI vs Human Agreement")
    print_divider()
    print(f"  Accepted  (AI correct) : {accepted:>3}  ({agreement_pct}%)")
    print(f"  Edited    (AI partial) : {edited:>3}  ({round(edited/reviewed*100,1)}%)")
    print(f"  Rejected  (AI wrong)   : {rejected:>3}  ({round(rejected/reviewed*100,1)}%)")
    print(f"\n  Agreement Rate : {agreement_pct}%")

    print("\n  Responsible AI Log — Top 5 Human-Corrected Cases")
    print_divider()
    if not top5:
        print("  No corrected cases found.")
    for r in top5:
        case = next((c for c in cases if c["case_id"] == r["case_id"]), {})
        print(f"\n  [{r['case_id']}] Verdict: {r['verdict']}")
        print(f"  Symptom   : {case.get('symptom', 'N/A')}")
        print(f"  AI said   : {r['ai_root_cause_summary']}")
        print(f"  Human note: {r['human_note']}")

    print()
    print_divider("=")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    write_cases_csv()
    write_review_log_csv()
    build_dashboard()
