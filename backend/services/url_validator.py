"""
Aegis Protocol — SSRF (Server-Side Request Forgery) Defense Service
===================================================================
Provides robust validation, DNS resolution, and IP range restriction
for external URLs before any HTTP fetching is initiated by scrapers
or evidence retrieval agents.
"""

import ipaddress
import logging
import socket
import urllib.parse
from typing import Set, Tuple

logger = logging.getLogger(__name__)

# Allowed protocols
ALLOWED_SCHEMES: Set[str] = {"http", "https"}

# Allowed ports for public web fetching
ALLOWED_PORTS: Set[int] = {80, 443}

# Known cloud metadata hostnames
BLOCKED_HOSTNAMES: Set[str] = {
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}

# Forbidden IP networks (IPv4 and IPv6)
BLOCKED_NETWORKS = [
    # IPv4 loopback & unspecified
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/8"),
    # IPv4 private RFC 1918
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # IPv4 link-local & cloud metadata (RFC 3927)
    ipaddress.ip_network("169.254.0.0/16"),
    # IPv4 carrier-grade NAT
    ipaddress.ip_network("100.64.0.0/10"),
    # IPv4 multicast & future reservation
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 loopback & unspecified
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    # IPv6 unique local (ULA)
    ipaddress.ip_network("fc00::/7"),
    # IPv6 link-local
    ipaddress.ip_network("fe80::/10"),
    # IPv6 multicast
    ipaddress.ip_network("ff00::/8"),
    # IPv6 IPv4-mapped
    ipaddress.ip_network("::ffff:0:0/96"),
]


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address belongs to any private, loopback, or reserved network."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        # Check standard properties
        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return True

        # Check explicit network definitions
        for net in BLOCKED_NETWORKS:
            if ip_obj in net:
                return True
        return False
    except ValueError:
        return True


def validate_url_safe(url: str, allow_custom_ports: bool = False) -> Tuple[bool, str]:
    """
    Validate whether a given URL is safe to fetch from the server.
    
    Checks:
    1. Valid HTTP/HTTPS scheme
    2. Non-empty host
    3. No credentials embedded in URL
    4. Safe port (80 or 443 unless allow_custom_ports is True)
    5. Host does not match blocked metadata hostnames
    6. DNS resolution of host does not resolve to private/loopback/cloud metadata IP
    
    Returns:
        (is_safe, error_reason_if_unsafe)
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL"

    url_clean = url.strip()
    try:
        parsed = urllib.parse.urlsplit(url_clean)
    except Exception as e:
        return False, f"Malformed URL syntax: {e}"

    # 1. Enforce scheme
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are permitted."

    # 2. Enforce hostname presence
    host = parsed.hostname
    if not host:
        return False, "Missing hostname in URL"
    host_lower = host.lower()

    # 3. Check for embedded credentials
    if parsed.username or parsed.password:
        return False, "URLs containing embedded user credentials are not permitted."

    # 4. Check blocked hostnames
    if host_lower in BLOCKED_HOSTNAMES:
        return False, f"Hostname '{host}' is a forbidden internal metadata address."

    # 5. Check port
    port = parsed.port
    if port is not None and not allow_custom_ports:
        if port not in ALLOWED_PORTS:
            return False, f"Port {port} is not permitted. Only standard web ports (80, 443) are allowed."

    # 6. Check if hostname is directly an IP literal
    try:
        ip_obj = ipaddress.ip_address(host_lower)
        if is_ip_blocked(str(ip_obj)):
            return False, f"Direct access to private or reserved IP '{host}' is blocked (SSRF protection)."
    except ValueError:
        # Hostname is a domain name, resolve via DNS
        try:
            addr_info = socket.getaddrinfo(host_lower, None)
            resolved_ips = {item[4][0] for item in addr_info if item[4]}
            for ip in resolved_ips:
                if is_ip_blocked(ip):
                    return False, f"Hostname '{host}' resolved to restricted IP address '{ip}' (SSRF protection)."
        except socket.gaierror as e:
            return False, f"DNS resolution failed for hostname '{host}': {e}"
        except Exception as e:
            return False, f"Error validating host '{host}': {e}"

    return True, ""


# Alias for backward compatibility
is_safe_url = validate_url_safe
