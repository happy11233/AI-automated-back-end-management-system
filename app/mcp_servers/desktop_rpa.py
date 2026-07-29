from pathlib import Path
import json
import platform
import shutil
import subprocess
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.config import settings


mcp = FastMCP(
    "company-desktop-rpa",
    instructions="桌面 RPA 适配工具。只打开外部软件并准备内容，不自动点击最终发送按钮。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """返回桌面 RPA 适配层状态。"""
    is_mac = platform.system() == "Darwin"
    osascript_path = shutil.which("osascript")
    enabled = bool(settings.finance_wechat_mac_rpa_enabled)
    status = "configured" if is_mac and osascript_path and enabled else "stub_ready"
    if not is_mac:
        message = "当前不是 macOS，真实个人微信执行器暂不启用；Windows 分支已预留。"
    elif not osascript_path:
        message = "未找到 osascript，Mac 个人微信执行器不可用。"
    elif not enabled:
        message = "Mac 个人微信执行器已安装但未启用；设置 FINANCE_WECHAT_MAC_RPA_ENABLED=true 后可真实打开微信。"
    else:
        message = "Mac 个人微信执行器已启用；会打开微信、搜索联系人并粘贴附件，停止在最终发送前。"

    return {
        "ok": True,
        "status": status,
        "message": message,
        "platforms": ["mac", "windows_reserved"],
        "mac_rpa_enabled": enabled,
        "osascript_available": bool(osascript_path),
        "wechat_app_name": settings.finance_wechat_mac_app_name,
    }


@mcp.tool()
def prepare_wechat_attachment(
    recipient_name: str,
    artifact_id: str | None = None,
    filename: str | None = None,
    download_path: str | None = None,
    local_file_path: str | None = None,
    platform_name: str = "mac",
) -> dict[str, Any]:
    """准备个人微信附件发送任务；停止在最终发送前。"""
    recipient = str(recipient_name or "").strip()
    if not recipient:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "微信联系人不能为空。",
        }

    normalized_platform = str(platform_name or "mac").strip().lower()
    if normalized_platform in {"windows", "win"}:
        return {
            "ok": True,
            "status": "waiting_executor",
            "executor_type": "windows_reserved",
            "message": "Windows 个人微信执行器已预留，第一版先跑通 Mac 本机演示。",
            "recipient_name": recipient,
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": download_path,
            "manual_final_send_required": True,
            "auto_click_send_allowed": False,
        }

    if platform.system() != "Darwin":
        return {
            "ok": True,
            "status": "waiting_executor",
            "executor_type": "tagui_mac",
            "message": "当前环境不是 macOS，已生成个人微信准备任务，等待 Mac 执行器处理。",
            "recipient_name": recipient,
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": download_path,
            "manual_final_send_required": True,
            "auto_click_send_allowed": False,
        }

    if not settings.finance_wechat_mac_rpa_enabled:
        return {
            "ok": True,
            "status": "waiting_executor",
            "executor_type": "tagui_mac",
            "message": "Mac 个人微信执行器未启用；设置 FINANCE_WECHAT_MAC_RPA_ENABLED=true 后可真实打开微信并粘贴附件。",
            "recipient_name": recipient,
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": download_path,
            "manual_final_send_required": True,
            "auto_click_send_allowed": False,
            "script_hint": _script_hint(),
        }

    file_path = Path(str(local_file_path or "")).expanduser()
    if not local_file_path or not file_path.exists() or not file_path.is_file():
        return {
            "ok": False,
            "status": "failed",
            "executor_type": "tagui_mac",
            "message": "未找到可附加到微信的本机文件，请检查生成文件是否仍存在。",
            "recipient_name": recipient,
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": download_path,
            "manual_final_send_required": True,
            "auto_click_send_allowed": False,
        }

    result = _run_macos_wechat_prepare(recipient_name=recipient, file_path=file_path)
    if not result["ok"]:
        return {
            "ok": False,
            "status": "failed",
            "executor_type": "tagui_mac",
            "message": result["message"],
            "recipient_name": recipient,
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": download_path,
            "manual_final_send_required": True,
            "auto_click_send_allowed": False,
            "script_hint": _script_hint(),
        }

    return {
        "ok": True,
        "status": "waiting_manual_send",
        "executor_type": "tagui_mac",
        "message": "已尝试打开个人微信、搜索联系人并粘贴附件；请你复核微信窗口后手动点击发送。",
        "recipient_name": recipient,
        "artifact_id": artifact_id,
        "filename": filename,
        "download_path": download_path,
        "manual_final_send_required": True,
        "auto_click_send_allowed": False,
        "opened_contact": True,
        "attached_file": True,
        "diagnostics": result.get("diagnostics") or {},
        "script_hint": _script_hint(),
    }


def _run_macos_wechat_prepare(*, recipient_name: str, file_path: Path) -> dict[str, Any]:
    osascript_path = shutil.which("osascript")
    if not osascript_path:
        return {
            "ok": False,
            "message": "未找到 macOS osascript，无法执行个人微信自动化。",
        }

    contact_result = _open_wechat_contact(recipient_name=recipient_name)
    if not contact_result["ok"]:
        return contact_result

    clipboard_result = _set_macos_file_clipboard(file_path)
    if not clipboard_result["ok"]:
        return clipboard_result

    paste_result = _paste_wechat_attachment()
    if not paste_result["ok"]:
        return paste_result

    return {
        "ok": True,
        "message": "Mac 微信窗口已准备好。",
        "diagnostics": {
            "contact": contact_result.get("diagnostics") or {},
            "clipboard": clipboard_result.get("diagnostics") or {},
            "paste": paste_result.get("diagnostics") or {},
        },
    }


def _open_wechat_contact(*, recipient_name: str) -> dict[str, Any]:
    osascript_path = shutil.which("osascript")
    if not osascript_path:
        return {
            "ok": False,
            "message": "未找到 macOS osascript，无法打开个人微信联系人。",
        }

    script = r'''
on run argv
    set recipientName to item 1 of argv
    set appName to item 2 of argv

    do shell script "open -a " & quoted form of appName
    delay 1.0
    tell application appName to activate
    delay 1.0

    set the clipboard to recipientName
    tell application "System Events"
        if UI elements enabled is false then
            error "macOS 辅助功能权限未开启"
        end if
        tell process appName
            set frontmost to true
            delay 0.4
            if (count of windows) is 0 then
                error "微信没有可操作窗口，请确认微信已登录。"
            end if

            -- 微信 4.x 的辅助功能树几乎不可读，直接点搜索框在不同窗口位置下不稳定。
            -- 优先用微信自己的搜索快捷键聚焦搜索，再用 Enter 选择第一条搜索结果。
            keystroke "f" using {command down}
            delay 0.45
            keystroke "a" using {command down}
            delay 0.1
            keystroke "v" using {command down}
            delay 1.1
            key code 36
            delay 1.2
        end tell
        set activeApp to name of first application process whose frontmost is true
        if activeApp is not appName then
            error "微信没有成功切到前台，当前前台应用为：" & activeApp
        end if
    end tell
    return "contact-prepared"
end run
'''.strip()

    try:
        completed = subprocess.run(
            [
                osascript_path,
                "-e",
                script,
                recipient_name,
                settings.finance_wechat_mac_app_name,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=max(3, settings.finance_wechat_executor_timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "message": "Mac 微信联系人准备执行超时，请检查微信是否已登录以及辅助功能权限是否开启。",
        }

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return {
            "ok": False,
            "message": (
                "Mac 微信联系人准备没有执行成功，请确认微信已安装并登录，且已给运行后端的终端/应用开启“系统设置 > 隐私与安全性 > 辅助功能”权限。"
                f" 技术线索：{detail[:180]}"
            ),
        }

    return {
        "ok": True,
        "message": "Mac 微信联系人窗口已准备好。",
        "diagnostics": {
            "stdout": (completed.stdout or "").strip(),
        },
    }


def _set_macos_file_clipboard(file_path: Path) -> dict[str, Any]:
    osascript_path = shutil.which("osascript")
    if not osascript_path:
        return {
            "ok": False,
            "message": "未找到 macOS osascript，无法设置文件剪贴板。",
        }

    script = r'''
ObjC.import('AppKit')
function run(argv) {
  const filePath = argv[0]
  const pasteboard = $.NSPasteboard.generalPasteboard
  pasteboard.clearContents
  const fileUrl = $.NSURL.fileURLWithPath(filePath)
  const objects = $.NSArray.arrayWithObject(fileUrl)
  const written = pasteboard.writeObjects(objects)
  const types = ObjC.deepUnwrap(pasteboard.types)
  return JSON.stringify({ written, types })
}
'''.strip()

    try:
        completed = subprocess.run(
            [
                osascript_path,
                "-l",
                "JavaScript",
                "-e",
                script,
                str(file_path),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "message": "Mac 文件剪贴板设置超时，未继续粘贴到微信。",
        }

    detail = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return {
            "ok": False,
            "message": f"Mac 文件剪贴板设置失败，未继续粘贴到微信。技术线索：{detail[:180]}",
        }

    diagnostics: dict[str, Any] = {}
    try:
        diagnostics = json.loads(detail)
    except json.JSONDecodeError:
        diagnostics = {"raw": detail}

    types = diagnostics.get("types") if isinstance(diagnostics.get("types"), list) else []
    has_file_url = "public.file-url" in types
    has_filenames = "NSFilenamesPboardType" in types
    if not diagnostics.get("written") or not (has_file_url and has_filenames):
        return {
            "ok": False,
            "message": "Mac 文件剪贴板没有写入可被微信识别的文件格式，已停止自动粘贴。",
            "diagnostics": diagnostics,
        }

    return {
        "ok": True,
        "message": "Mac 文件剪贴板已写入文件 URL。",
        "diagnostics": diagnostics,
    }


def _paste_wechat_attachment() -> dict[str, Any]:
    osascript_path = shutil.which("osascript")
    if not osascript_path:
        return {
            "ok": False,
            "message": "未找到 macOS osascript，无法粘贴微信附件。",
        }

    script = r'''
on run argv
    set appName to item 1 of argv
    tell application appName to activate
    delay 0.35
    tell application "System Events"
        if UI elements enabled is false then
            error "macOS 辅助功能权限未开启"
        end if
        tell process appName
            set frontmost to true
            if (count of windows) is 0 then
                error "微信没有可操作窗口，请确认微信已登录。"
            end if
            -- 搜索结果通过 Enter 打开后，微信会把焦点留在当前聊天输入框。
            -- 这里不再用坐标点击输入区，避免点偏后把附件粘到错误区域。
            keystroke "v" using {command down}
            delay 1.2
        end tell
    end tell
    return "attachment-pasted"
end run
'''.strip()

    try:
        completed = subprocess.run(
            [
                osascript_path,
                "-e",
                script,
                settings.finance_wechat_mac_app_name,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=max(3, settings.finance_wechat_executor_timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "message": "Mac 微信附件粘贴执行超时，未确认附件已进入微信窗口。",
        }

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return {
            "ok": False,
            "message": f"Mac 微信附件粘贴失败，未确认附件已进入微信窗口。技术线索：{detail[:180]}",
        }

    return {
        "ok": True,
        "message": "Mac 微信附件粘贴动作已完成。",
        "diagnostics": {
            "stdout": (completed.stdout or "").strip(),
        },
    }


def _script_hint() -> list[str]:
    return [
        "open personal WeChat on macOS",
        "search confirmed recipient by WeChat window coordinates",
        "write file URL to macOS pasteboard",
        "paste generated workbook as attachment",
        "stop before final send click",
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
