from __future__ import annotations

import math
import platform
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from urllib.error import URLError
from urllib.request import urlopen

import psutil

from app.config import settings
from app.db import fetch_one


FEATURES = {
    "auth": "登录认证",
    "chat": "AI 对话",
    "rag": "知识库",
    "erp": "ERP",
    "ai-workflows": "AI 工作流",
    "automation": "自动化",
    "customer-service": "客服",
    "files": "文件中心",
    "platform-drafts": "业务草稿",
    "approvals": "审批",
}
WINDOW_SECONDS = 60
_requests: deque[tuple[float, str, float, int]] = deque(maxlen=10000)
_requests_lock = Lock()


def record_request(path: str, duration_ms: float, status_code: int) -> None:
    feature = path.strip("/").split("/", 1)[0]
    if path.startswith(("/admin/documents", "/documents", "/rag-teams")):
        feature = "rag"
    elif path.startswith(("/agent/chat", "/public/llm/chat")):
        feature = "chat"
    if feature not in FEATURES:
        return
    with _requests_lock:
        _requests.append((time.monotonic(), feature, duration_ms, status_code))


def build_live_metrics() -> dict:
    checked_at = datetime.now(timezone.utc).isoformat()
    return {
        "checked_at": checked_at,
        "interval_seconds": 5,
        "host": _host_metrics(),
        "api_container": _container_metrics(),
        "database": _database_metrics(),
        "aiops": _aiops_health(),
        "features": _feature_metrics(),
    }


def _host_metrics() -> dict:
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/app/data" if Path("/app/data").exists() else ".")
    return {
        "source": "Linux 宿主机 / Docker VM" if platform.system() == "Linux" else "本机",
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory.percent, 1),
        "memory_used_bytes": memory.used,
        "memory_total_bytes": memory.total,
        "disk_percent": round(disk.percent, 1),
        "disk_used_bytes": disk.used,
        "disk_total_bytes": disk.total,
    }


def _container_metrics() -> dict:
    cpu_percent = _cgroup_cpu_percent()
    used = _read_int("/sys/fs/cgroup/memory.current")
    limit = _read_int("/sys/fs/cgroup/memory.max")
    if used is None:
        process = psutil.Process()
        used = process.memory_info().rss
    has_cgroup = Path("/sys/fs/cgroup/memory.current").exists()
    source = "API 容器 cgroup" if has_cgroup else "API 进程"
    if limit is None:
        limit = psutil.virtual_memory().total
        source += "（无内存配额）" if has_cgroup else "（占主机内存）"
    return {
        "source": source,
        "cpu_percent": cpu_percent,
        "memory_percent": round(min(100, used / limit * 100), 1) if limit and limit > 0 else None,
        "memory_used_bytes": used,
        "memory_total_bytes": limit,
    }


def _cgroup_cpu_percent() -> float | None:
    cpu_stat = Path("/sys/fs/cgroup/cpu.stat")
    if not cpu_stat.exists():
        return None
    start = _cpu_usage_usec(cpu_stat)
    start_time = time.monotonic()
    time.sleep(0.1)
    end = _cpu_usage_usec(cpu_stat)
    elapsed = time.monotonic() - start_time
    if start is None or end is None or elapsed <= 0:
        return None
    quota = Path("/sys/fs/cgroup/cpu.max")
    capacity = 1.0
    if quota.exists():
        parts = quota.read_text().split()
        if len(parts) == 2 and parts[0] != "max":
            capacity = int(parts[0]) / int(parts[1])
        else:
            capacity = psutil.cpu_count() or 1
    return round(min(100.0, max(0.0, (end - start) / 1_000_000 / elapsed / capacity * 100)), 1)


def _cpu_usage_usec(path: Path) -> int | None:
    try:
        for line in path.read_text().splitlines():
            if line.startswith("usage_usec "):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def _read_int(path: str) -> int | None:
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


def _database_metrics() -> dict:
    start = time.monotonic()
    try:
        connections, database_bytes = fetch_one(
            "SELECT (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()), "
            "pg_database_size(current_database())"
        )
        return {
            "status": "ok",
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
            "connections": connections,
            "size_bytes": database_bytes,
        }
    except Exception:
        return {"status": "error", "latency_ms": None, "connections": None, "size_bytes": None}


def _aiops_health() -> dict:
    base_url = (settings.aiops_service_url or "").rstrip("/")
    if not base_url:
        return {"status": "unconfigured", "latency_ms": None}
    start = time.monotonic()
    try:
        with urlopen(f"{base_url}/health", timeout=2) as response:
            status = "ok" if response.status == 200 else "error"
    except (OSError, URLError, ValueError):
        status = "error"
    return {"status": status, "latency_ms": round((time.monotonic() - start) * 1000, 1)}


def _feature_metrics() -> list[dict]:
    cutoff = time.monotonic() - WINDOW_SECONDS
    grouped: dict[str, list[tuple[float, int]]] = {key: [] for key in FEATURES}
    with _requests_lock:
        while _requests and _requests[0][0] < cutoff:
            _requests.popleft()
        for _, feature, duration_ms, status_code in _requests:
            grouped[feature].append((duration_ms, status_code))
    result = []
    for key, label in FEATURES.items():
        samples = grouped[key]
        durations = sorted(item[0] for item in samples)
        errors = sum(1 for _, status in samples if status >= 500)
        result.append({
            "key": key,
            "label": label,
            "requests_1m": len(samples),
            "errors_1m": errors,
            "avg_latency_ms": round(sum(durations) / len(durations), 1) if durations else None,
            "p95_latency_ms": round(durations[math.ceil(len(durations) * 0.95) - 1], 1) if durations else None,
        })
    return result
