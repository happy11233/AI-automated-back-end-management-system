import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.erp.diagnostics import build_erp_diagnostics


def main() -> None:
    diagnostics = build_erp_diagnostics()
    diagnostics["network_checks"] = _build_network_checks()

    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))


def _build_network_checks() -> list[dict]:
    base_url = (settings.erp_base_url or "").rstrip("/")
    if not base_url:
        return [
            {
                "name": "erpnext_base_url",
                "ok": False,
                "status": "not_configured",
                "message": "ERP_BASE_URL 未配置，无法做网络连通性检查。",
            }
        ]

    return [
        _probe_url(
            name="erpnext_home",
            url=base_url,
            authenticated=False,
        ),
        _probe_url(
            name="erpnext_logged_user",
            url=f"{base_url}/api/method/frappe.auth.get_logged_user",
            authenticated=True,
        ),
    ]


def _probe_url(name: str, url: str, authenticated: bool) -> dict:
    headers = {"Accept": "application/json"}

    if authenticated and settings.erp_api_key and settings.erp_api_secret:
        headers["Authorization"] = (
            f"token {settings.erp_api_key}:{settings.erp_api_secret}"
        )

    request = Request(url, headers=headers, method="GET")

    try:
        with urlopen(request, timeout=settings.erp_timeout_seconds) as response:
            body = response.read(300).decode("utf-8", errors="replace")
            return {
                "name": name,
                "url": url,
                "ok": 200 <= response.status < 400,
                "http_status": response.status,
                "content_type": response.headers.get("content-type"),
                "body_preview": _normalize_body(body),
            }
    except HTTPError as error:
        body = error.read(300).decode("utf-8", errors="replace")
        return {
            "name": name,
            "url": url,
            "ok": False,
            "http_status": error.code,
            "content_type": error.headers.get("content-type"),
            "body_preview": _normalize_body(body),
        }
    except URLError as error:
        return {
            "name": name,
            "url": url,
            "ok": False,
            "status": "connection_error",
            "message": str(error.reason),
        }
    except TimeoutError:
        return {
            "name": name,
            "url": url,
            "ok": False,
            "status": "timeout",
            "message": f"请求超过 {settings.erp_timeout_seconds} 秒未响应。",
        }


def _normalize_body(body: str) -> str:
    return " ".join(body.split())[:300]


if __name__ == "__main__":
    main()
