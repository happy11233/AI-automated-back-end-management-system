from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    checks = {
        "admin_routes": _contains_all(
            ROOT / "app/api/connectors.py",
            [
                "/wechat-work/management",
                "/wechat-work/settings",
                "/wechat-work/sync",
                "/wechat-work/contacts",
                "/wechat-work/groups",
                "/wechat-work/test-send",
                "Depends(require_admin)",
                "admin.enterprise_wechat.settings_update",
                "admin.enterprise_wechat.sync",
                "admin.enterprise_wechat.group_upsert",
                "admin.enterprise_wechat.test_send",
            ],
        ),
        "service_guards": _contains_all(
            ROOT / "app/services/enterprise_wechat_service.py",
            [
                "enterprise_wechat_settings",
                "get_enterprise_wechat_effective_settings",
                "get_enterprise_wechat_settings_public",
                "real_send_enabled",
                "真实发送开关未启用",
                "_mask_secret",
                "send_enterprise_wechat_test_file",
                "sync_enterprise_wechat_departments_and_users",
            ],
        ),
        "sql_migration": _contains_all(
            ROOT / "sql/021_enterprise_wechat_settings.sql",
            [
                "CREATE TABLE IF NOT EXISTS enterprise_wechat_settings",
                "corp_id TEXT",
                "agent_id TEXT",
                "secret TEXT",
                "real_send_enabled BOOLEAN",
                "last_sync_result JSONB",
            ],
        ),
        "frontend_management_panel": _contains_all(
            ROOT / "frontend/src/main.tsx",
            [
                "EnterpriseWechatManagementPanel",
                "getEnterpriseWechatManagement",
                "updateEnterpriseWechatSettings",
                "syncEnterpriseWechatContacts",
                "upsertEnterpriseWechatGroup",
                "testEnterpriseWechatSend",
                "发送安全测试文件",
            ],
        ),
    }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise AssertionError(f"企业微信连接器管理 Spec 静态验证失败：{failed}")

    print(json.dumps({"ok": True, "checks": checks}, ensure_ascii=False, indent=2))


def _contains_all(path: Path, needles: list[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    return all(needle in text for needle in needles)


if __name__ == "__main__":
    main()
