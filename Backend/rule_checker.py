"""
rule_checker.py — NetSage AI
Deterministic Cisco IOS CLI parser for common network misconfigurations.
"""

import re
from ipaddress import ip_interface, ip_network, IPv4Interface, AddressValueError
from collections import defaultdict


# ---------------------------------------------------------------------------
# 1. Interface Status  (`show ip interface brief`)
# ---------------------------------------------------------------------------

_INTF_BRIEF_RE = re.compile(
    r"^(\S+)\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)",
    re.MULTILINE,
)

def check_interface_brief(output: str, issues: list, checks: set) -> None:
    """Flag admin-down and down/down interfaces."""
    for match in _INTF_BRIEF_RE.finditer(output):
        intf, ip, status, proto = match.groups()
        if intf.lower() == "interface":          # header row
            continue
        if status.lower() == "administratively":
            issues.append(f"Interface {intf} is administratively down.")
            checks.add("show interfaces " + intf)
        elif status.lower() == "down" and proto.lower() == "down":
            issues.append(f"Interface {intf} is down/down (possible cable or encapsulation issue).")
            checks.add("show interfaces " + intf)


# ---------------------------------------------------------------------------
# 2. IP / Subnet validation  (`show ip interface brief` + `show run`)
# ---------------------------------------------------------------------------

_IP_INTF_RE = re.compile(
    r"interface\s+(\S+).*?ip address\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+\.\d+\.\d+\.\d+)",
    re.IGNORECASE | re.DOTALL,
)
_GW_RE = re.compile(r"ip default-gateway\s+(\S+)", re.IGNORECASE)
_SUBINTF_RE = re.compile(r"interface\s+(\S+\.\d+)", re.IGNORECASE)

_VALID_MASKS = {
    "255.255.255.0", "255.255.254.0", "255.255.252.0", "255.255.248.0",
    "255.255.240.0", "255.255.224.0", "255.255.192.0", "255.255.128.0",
    "255.255.0.0",   "255.254.0.0",   "255.252.0.0",   "255.248.0.0",
    "255.240.0.0",   "255.224.0.0",   "255.192.0.0",   "255.128.0.0",
    "255.0.0.0",     "255.255.255.128","255.255.255.192","255.255.255.224",
    "255.255.255.240","255.255.255.248","255.255.255.252","255.255.255.255",
}

def check_ip_config(run_output: str, issues: list, checks: set) -> None:
    """Detect duplicate IPs, invalid masks, and missing default gateways."""
    seen_ips: dict[str, str] = {}
    networks: list[tuple[str, ip_network]] = []
    has_subintf = bool(_SUBINTF_RE.search(run_output))

    for match in _IP_INTF_RE.finditer(run_output):
        intf, ip, mask = match.groups()
        # Duplicate IP check
        if ip in seen_ips:
            issues.append(
                f"Duplicate IP {ip} on {intf} (already assigned to {seen_ips[ip]})."
            )
            checks.add("show ip interface brief")
        else:
            seen_ips[ip] = intf

        # Invalid mask check
        if mask not in _VALID_MASKS:
            issues.append(f"Possibly invalid subnet mask {mask} on {intf}.")
            checks.add("show run interface " + intf)

        # Overlapping subnet check
        try:
            net = ip_network(f"{ip}/{mask}", strict=False)
            for prev_intf, prev_net in networks:
                if net.overlaps(prev_net) and intf != prev_intf:
                    issues.append(
                        f"Overlapping subnets: {intf} ({net}) overlaps {prev_intf} ({prev_net})."
                    )
                    checks.add("show ip route")
            networks.append((intf, net))
        except ValueError:
            pass

    # Default gateway check (relevant for Layer-2 switches / sub-interface configs)
    if has_subintf and not _GW_RE.search(run_output):
        issues.append("Sub-interfaces detected but no 'ip default-gateway' found.")
        checks.add("show run | include ip default-gateway")


# ---------------------------------------------------------------------------
# 3. VLAN checks  (`show vlan brief` + `show run`)
# ---------------------------------------------------------------------------

_VLAN_DEF_RE = re.compile(r"^(\d+)\s+\S+\s+active", re.MULTILINE | re.IGNORECASE)
_TRUNK_ALLOWED_RE = re.compile(
    r"switchport trunk allowed vlan\s+([\d,\-]+)", re.IGNORECASE
)
_ACCESS_VLAN_RE = re.compile(r"switchport access vlan\s+(\d+)", re.IGNORECASE)

def _expand_vlan_range(vlan_str: str) -> set[int]:
    """Expand '10,20-22,30' → {10, 20, 21, 22, 30}."""
    vlans: set[int] = set()
    for part in vlan_str.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            vlans.update(range(int(lo), int(hi) + 1))
        elif part.isdigit():
            vlans.add(int(part))
    return vlans

def check_vlan_config(vlan_output: str, run_output: str, issues: list, checks: set) -> None:
    """Detect undefined VLANs referenced in trunk/access configs."""
    defined_vlans = {int(m.group(1)) for m in _VLAN_DEF_RE.finditer(vlan_output)}
    # VLAN 1 is always implicitly defined on Cisco IOS
    defined_vlans.add(1)

    # Check trunk allowed VLANs
    for match in _TRUNK_ALLOWED_RE.finditer(run_output):
        for vid in _expand_vlan_range(match.group(1)):
            if vid not in defined_vlans:
                issues.append(f"VLAN {vid} is in trunk allowed list but not defined in 'show vlan brief'.")
                checks.add("show vlan brief")
                checks.add("vlan database  # or conf t → vlan " + str(vid))

    # Check access VLANs
    for match in _ACCESS_VLAN_RE.finditer(run_output):
        vid = int(match.group(1))
        if vid not in defined_vlans:
            issues.append(f"Access VLAN {vid} is assigned to a port but not defined.")
            checks.add("show vlan brief")


# ---------------------------------------------------------------------------
# 4. Route table checks  (`show ip route`)
# ---------------------------------------------------------------------------

_DEFAULT_ROUTE_RE = re.compile(r"S\*\s+0\.0\.0\.0", re.MULTILINE)
_ROUTE_LINE_RE = re.compile(r"^[COSRDBEI\*\s]{1,3}\s+(\d+\.\d+\.\d+\.\d+)", re.MULTILINE)

def check_ip_route(route_output: str, issues: list, checks: set) -> None:
    """Warn if no default route is present in the routing table."""
    if route_output and not _DEFAULT_ROUTE_RE.search(route_output):
        issues.append("No default route (S* 0.0.0.0) found in routing table.")
        checks.add("show ip route")
        checks.add("ip route 0.0.0.0 0.0.0.0 <next-hop>  # add default route if needed")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_checks(
    interface_brief: str = "",
    show_run: str = "",
    show_vlan_brief: str = "",
    show_ip_route: str = "",
) -> dict:
    """
    Run all deterministic rule checks against provided Cisco CLI outputs.

    Returns:
        {
            "has_errors": bool,
            "detected_issues": list[str],
            "suggested_checks": list[str],
        }
    """
    issues: list[str] = []
    checks: set[str] = set()

    if interface_brief:
        check_interface_brief(interface_brief, issues, checks)
    if show_run:
        check_ip_config(show_run, issues, checks)
    if show_vlan_brief or show_run:
        check_vlan_config(show_vlan_brief, show_run, issues, checks)
    if show_ip_route:
        check_ip_route(show_ip_route, issues, checks)

    return {
        "has_errors": bool(issues),
        "detected_issues": issues,
        "suggested_checks": sorted(checks),
    }


if __name__ == "__main__":
    import sys, json
    payload = json.loads(sys.stdin.read())
    result = run_checks(
        interface_brief=payload.get("interface_brief", ""),
        show_run=payload.get("show_run", ""),
        show_vlan_brief=payload.get("show_vlan_brief", ""),
        show_ip_route=payload.get("show_ip_route", ""),
    )
    print(json.dumps(result))
