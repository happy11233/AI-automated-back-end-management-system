from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.config import settings


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirectHandler)


def validate_platform_action_executor_url(value: str) -> str:
    url = str(value or "").strip()
    if not url:
        raise ValueError("Webhook URL 不能为空")

    parsed = urlsplit(url)
    allowed_schemes = _allowed_schemes()
    if parsed.scheme not in allowed_schemes:
        raise ValueError(f"Webhook URL 协议不被允许，请使用：{', '.join(sorted(allowed_schemes))}")
    if not parsed.hostname:
        raise ValueError("Webhook URL 必须包含有效主机名")
    if parsed.username or parsed.password:
        raise ValueError("Webhook URL 不允许包含用户名或密码")
    if parsed.fragment:
        raise ValueError("Webhook URL 不允许包含片段标识")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Webhook URL 端口无效") from error

    port = port or (443 if parsed.scheme == "https" else 80)
    if port not in _allowed_ports():
        raise ValueError("Webhook URL 端口不在 PLATFORM_ACTION_EXECUTOR_ALLOWED_PORTS allowlist 中")

    _ensure_host_allowed(parsed.hostname, port)
    return url


def preview_platform_action_executor_url(value: str) -> str:
    parsed = urlsplit(str(value or ""))
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/***"
    return "***"


def open_platform_action_request(request: Request, *, timeout: int):
    validate_platform_action_executor_url(request.full_url)
    try:
        return _NO_REDIRECT_OPENER.open(request, timeout=timeout)
    except HTTPError as error:
        if 300 <= error.code < 400:
            raise RuntimeError("外部执行器返回重定向，已按安全策略拒绝") from error
        raise


def _ensure_host_allowed(hostname: str, port: int | None) -> None:
    normalized_host = _normalize_host(hostname)
    host_allowlist, network_allowlist = _allowed_targets()
    if _host_allowed(normalized_host, host_allowlist):
        return

    ips = _resolve_host_ips(normalized_host, port)
    if network_allowlist and any(any(ip in network for network in network_allowlist) for ip in ips):
        return

    if settings.platform_action_executor_require_allowlist:
        raise ValueError("Webhook URL 主机不在 PLATFORM_ACTION_EXECUTOR_ALLOWED_HOSTS allowlist 中")

    if _is_ip_literal(normalized_host):
        raise ValueError("Webhook URL 不允许使用裸 IP，请改用 allowlist 中的可信域名")

    blocked_ips = [str(ip) for ip in ips if _is_blocked_ip(ip)]
    if blocked_ips and not settings.platform_action_executor_allow_private_network:
        raise ValueError("Webhook URL 指向内网、环回、链路本地或保留地址，请先加入 allowlist")


def _resolve_host_ips(hostname: str, port: int | None) -> list[ipaddress._BaseAddress]:
    try:
        return [ipaddress.ip_address(hostname)]
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(hostname, port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ValueError(f"Webhook URL 主机无法解析：{hostname}") from error

    addresses: list[ipaddress._BaseAddress] = []
    for info in infos:
        raw_address = info[4][0]
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError:
            continue
        if address not in addresses:
            addresses.append(address)

    if not addresses:
        raise ValueError(f"Webhook URL 主机无法解析：{hostname}")
    return addresses


def _allowed_targets() -> tuple[list[str], list[ipaddress._BaseNetwork]]:
    host_patterns: list[str] = []
    networks: list[ipaddress._BaseNetwork] = []
    raw = settings.platform_action_executor_allowed_hosts or ""
    for item in raw.replace("\n", ",").replace(" ", ",").split(","):
        value = item.strip().lower().rstrip(".")
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
            continue
        except ValueError:
            pass
        host_patterns.append(value)
    return host_patterns, networks


def _allowed_schemes() -> set[str]:
    values = {
        item.strip().lower()
        for item in (settings.platform_action_executor_allowed_schemes or "https").replace(" ", ",").split(",")
        if item.strip()
    }
    return values & {"http", "https"} or {"https"}


def _allowed_ports() -> set[int]:
    values: set[int] = set()
    raw = settings.platform_action_executor_allowed_ports or "443"
    for item in raw.replace(" ", ",").split(","):
        text = item.strip()
        if not text:
            continue
        try:
            port = int(text)
        except ValueError:
            continue
        if 1 <= port <= 65535:
            values.add(port)
    return values or {443}


def _host_allowed(hostname: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.startswith("*.") and hostname.endswith(pattern[1:]):
            return True
        if hostname == pattern:
            return True
    return False


def _normalize_host(hostname: str) -> str:
    return hostname.strip().lower().rstrip(".")


def _is_ip_literal(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        return True
    except ValueError:
        return False


def _is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )
