"""Safe, bounded HTTP health checks."""
import ipaddress
import socket
import time
from urllib.parse import urlsplit

import requests


def validate_destination(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL must use http:// or https:// and include a hostname.")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing credentials are not allowed.")
        if parsed.port and not 1 <= parsed.port <= 65535:
            raise ValueError("URL port is invalid.")
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            raise ValueError("Local and internal hostnames are not allowed.")
        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            try:
                records = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80),
                                             type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise ValueError("Hostname could not be resolved.") from exc
            addresses = [ipaddress.ip_address(record[4][0]) for record in records]
        if not addresses or any(not address.is_global for address in addresses):
            raise ValueError("Private, loopback, reserved, and internal destinations are not allowed.")
        return parsed
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, ValueError) and str(exc):
            raise
        raise ValueError("Invalid URL.") from exc


def check_url(url, timeout=8, dry_run=False):
    """Validate target, then do a no-redirect streamed GET and close it immediately."""
    validate_destination(url)
    if dry_run:
        return {"success": False, "status_code": None, "latency_ms": None, "error": None}
    started = time.perf_counter()
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.get(url, timeout=timeout, allow_redirects=False, stream=True) as response:
                latency = round((time.perf_counter() - started) * 1000, 2)
                status = response.status_code
                return {"success": 200 <= status < 400, "status_code": status,
                        "latency_ms": latency, "error": None if 200 <= status < 400 else f"HTTP {status}"}
    except requests.RequestException as exc:
        return {"success": False, "status_code": None, "latency_ms": round((time.perf_counter()-started)*1000, 2),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
