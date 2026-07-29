from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def assert_contains(path: str, expected: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [item for item in expected if item not in text]
    if missing:
        raise AssertionError(f"{path} missing: {missing}")


def main() -> None:
    assert_contains(
        "app/main.py",
        [
            "_should_handle_generated_file_wechat_send",
            "get_latest_generated_file_for_thread",
            "build_enterprise_wechat_file_confirmation_task",
            "enterprise_wechat_file_send",
            "source_message",
        ],
    )
    assert_contains(
        "app/api/automation.py",
        [
            "/files/enterprise-wechat-send/confirm",
            "source_message_id",
            "update_chat_message",
            "update_latest_chat_message_by_artifact",
            "automation.enterprise_wechat_file_send",
            "admin_error_detail",
        ],
    )
    assert_contains(
        "app/services/finance_salary_wechat_service.py",
        [
            "allow_manual_recipient",
            "manual_recipient_types",
            "build_enterprise_wechat_file_confirmation_task",
            "requires_sensitive_confirmation",
        ],
    )
    assert_contains(
        "app/services/generated_file_service.py",
        [
            "get_latest_generated_file_for_thread",
            "owner_user_id",
            "owner_position",
        ],
    )
    assert_contains(
        "frontend/src/api.ts",
        [
            "source_message_id",
            "/automation/files/enterprise-wechat-send/confirm",
        ],
    )
    assert_contains(
        "frontend/src/main.tsx",
        [
            "manual_chat_input",
            "source_message_id: chatMessage.id",
            "chatMessageContainsArtifact",
            "enterprise_wechat_file_send",
            "allowManualRecipient",
        ],
    )
    print("enterprise wechat chat file send spec checks passed")


if __name__ == "__main__":
    main()
