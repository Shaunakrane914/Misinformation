"""
Aegis Protocol — SSRF (Server-Side Request Forgery) Defense Service
===================================================================
Provides robust validation, DNS resolution, and IP range restriction
for external URLs before any HTTP fetching is initiated by scrapers
or evidence retrieval agents.
"""

import ipaddress
import logging
import math
import queue
import socket
import threading
import time
import urllib.parse
from typing import Set, Tuple

logger = logging.getLogger(__name__)

# Allowed protocols
ALLOWED_SCHEMES: Set[str] = {"http", "https"}

# Allowed ports for public web fetching
ALLOWED_PORTS: Set[int] = {80, 443}

# Approved zero-auth social evidence mirror hostnames (HTTPS port 443 only)
APPROVED_SOCIAL_MIRROR_HOSTNAMES: Set[str] = {
    "api.fxtwitter.com",
    "arctic-shift.photon-reddit.com",
}

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


# Thread-safe in-memory DNS resolution cache: host -> (is_valid, error_msg, expiry_timestamp)
_DNS_CACHE: dict = {}
_DNS_CACHE_TTL = 300.0  # 5 minutes
_DNS_SLOTS = threading.BoundedSemaphore(8)
_DNS_CACHE_LOCK = threading.Lock()
_DNS_FAILURE_TTL = 1.0  # Resolver errors are not durable security decisions.


class DNSResolutionError(OSError):
    """A failed bounded lookup, not evidence that a destination is private."""

    def __init__(self, kind: str, message: str, *, attempts: int = 1):
        super().__init__(message)
        self.failure_kind = kind
        self.resolver_attempts = attempts


def validation_failure_kind(reason: str) -> str:
    """Classify the legacy (bool, reason) API without weakening its deny result."""
    reason = str(reason or "").lower()
    if "deadline exhausted" in reason:
        return "BUDGET_EXHAUSTED"
    if "dns validation capacity exhausted" in reason:
        return "DNS_CAPACITY"
    if "dns validation timed out" in reason:
        return "DNS_TIMEOUT"
    if "dns resolution failed" in reason:
        return "DNS_ERROR"
    return "SSRF_BLOCKED"


def _resolve_once(host: str, port: int, timeout: float) -> list:
    if timeout <= 0:
        raise DNSResolutionError("DNS_TIMEOUT", "DNS validation timed out", attempts=0)
    if not _DNS_SLOTS.acquire(blocking=False):
        raise DNSResolutionError("DNS_CAPACITY", "DNS validation capacity exhausted")
    results = queue.Queue(maxsize=1)

    def resolve():
        try:
            results.put((socket.getaddrinfo(host, port, type=socket.SOCK_STREAM), None))
        except Exception as error:
            results.put((None, error))
        finally:
            _DNS_SLOTS.release()

    threading.Thread(target=resolve, name="public-dns-validation", daemon=True).start()
    try:
        addresses, error = results.get(timeout=max(0.001, timeout))
    except queue.Empty as error:
        raise DNSResolutionError("DNS_TIMEOUT", "DNS validation timed out") from error
    if error is not None:
        raise error
    return addresses


def resolve_public_addresses(host: str, port: int, timeout: float = 2.5,
                             *, allow_custom_ports: bool = False) -> list:
    """Resolve fresh addresses for a connection, rejecting mixed/private answers.

    A validation-cache hit is deliberately not sufficient for establishing a
    connection. Callers must connect to one of these exact numeric addresses,
    without performing a second hostname lookup.
    """
    if not host or not (0 < port < 65536) or (port not in ALLOWED_PORTS and not allow_custom_ports):
        raise ValueError("Invalid public HTTP destination")
    if not math.isfinite(timeout) or timeout <= 0:
        raise DNSResolutionError("DNS_TIMEOUT", "DNS validation timed out", attempts=0)
    from backend.infrastructure.acquisition.network.budget import remaining_timeout
    deadline = time.monotonic() + remaining_timeout(timeout)
    # Retry only an OS-declared transient lookup failure. NXDOMAIN/11001,
    # unsafe answers, timeout/capacity and HTTP failures are not retry signals.
    transient_codes = {socket.EAI_AGAIN, 11002}  # EAI_AGAIN / Windows WSATRY_AGAIN
    for attempt in (1, 2):
        try:
            addresses = _resolve_once(host, port, deadline - time.monotonic())
            break
        except socket.gaierror as error:
            if error.errno in transient_codes and attempt == 1 and time.monotonic() < deadline:
                continue
            raise DNSResolutionError("DNS_ERROR", f"DNS lookup failed ({error.errno})", attempts=attempt) from error
        except DNSResolutionError:
            raise
        except OSError as error:
            # OS resource/socket failures during getaddrinfo are still failed
            # DNS observations, not evidence that an IP violated SSRF policy.
            raise DNSResolutionError("DNS_ERROR", f"DNS lookup failed ({error.errno})", attempts=attempt) from error
    if not addresses or any(not item[4] or is_ip_blocked(item[4][0]) for item in addresses):
        raise ValueError("DNS resolved to a private, reserved, or empty address set")
    return addresses


def clear_dns_cache() -> None:
    """Clear internal DNS cache."""
    with _DNS_CACHE_LOCK:
        _DNS_CACHE.clear()


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
    try:
        port = parsed.port
    except ValueError:
        return False, "Invalid URL port"
    if port is not None and not allow_custom_ports:
        if port not in ALLOWED_PORTS:
            return False, f"Port {port} is not permitted. Only standard web ports (80, 443) are allowed."

    # 6. Check DNS cache
    now = time.monotonic()
    with _DNS_CACHE_LOCK:
        cached = _DNS_CACHE.get(host_lower)
    if cached and now < cached[2]:
        return cached[0], cached[1]

    # 7. Check if hostname is directly an IP literal
    try:
        ip_obj = ipaddress.ip_address(host_lower)
        if is_ip_blocked(str(ip_obj)):
            _DNS_CACHE[host_lower] = (False, f"Direct access to private or reserved IP '{host}' is blocked (SSRF protection).", now + _DNS_CACHE_TTL)
            return False, f"Direct access to private or reserved IP '{host}' is blocked (SSRF protection)."
    except ValueError:
        # Do not mutate the process-wide socket timeout from concurrent workers.
        try:
            addr_info = resolve_public_addresses(
                host_lower, port or (443 if parsed.scheme.lower() == "https" else 80),
                allow_custom_ports=allow_custom_ports,
            )
            resolved_ips = {item[4][0] for item in addr_info if item[4]}
            for ip in resolved_ips:
                if is_ip_blocked(ip):
                    err = f"Hostname '{host}' resolved to restricted IP address '{ip}' (SSRF protection)."
                    _DNS_CACHE[host_lower] = (False, err, now + _DNS_CACHE_TTL)
                    return False, err
            _DNS_CACHE[host_lower] = (True, "", now + _DNS_CACHE_TTL)
        except (DNSResolutionError, socket.gaierror) as e:
            err = f"DNS resolution failed for hostname '{host}': {e}"
            # Keep brief negative caching for bursts, but do not turn an OS
            # resolver outage into a 60s unsafe-host decision across requests.
            _DNS_CACHE[host_lower] = (False, err, time.monotonic() + _DNS_FAILURE_TTL)
            return False, err
        except TimeoutError as e:
            err = f"DNS resolution failed for hostname '{host}': {e}"
            _DNS_CACHE[host_lower] = (False, err, time.monotonic() + _DNS_FAILURE_TTL)
            return False, err
        except Exception as e:
            err = f"Error validating host '{host}': {e}"
            _DNS_CACHE[host_lower] = (False, err, now + 60.0)
            return False, err

    return True, ""


# Alias for backward compatibility
is_safe_url = validate_url_safe
