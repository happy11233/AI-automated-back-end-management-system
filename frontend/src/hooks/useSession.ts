import { useState } from "react";
import { message } from "antd";
import { login, type LoginResponse, type Position } from "../api";
import type { ProjectTarget, Role, View } from "../workspace/types";
import { canRoleAccessView, readStoredAllowedAiAppIds, readStoredPosition } from "../workspace/shared";
import { navigateToView, readPositionFromToken, readRoleFromToken, readStoredRole } from "../workspace/appHelpers";

export function useSession({ activeView, setStatusMessage, onAuthenticated }: {
  activeView: View;
  setStatusMessage: (value: string) => void;
  onAuthenticated: (session: LoginResponse, role: Role, position: Position | null) => void;
}) {
  const [role, setRole] = useState<Role>(readStoredRole);

  const [position, setPosition] = useState<Position | null>(readStoredPosition);

  const [allowedAiAppIds, setAllowedAiAppIds] = useState<string[] | null>(readStoredAllowedAiAppIds);

  const [username, setUsername] = useState(localStorage.getItem("username") ?? "");

  const [displayName, setDisplayName] = useState(localStorage.getItem("display_name") ?? "");

  const [userEmail, setUserEmail] = useState(localStorage.getItem("user_email") ?? "");

  const [password, setPassword] = useState("");

  const [token, setToken] = useState(localStorage.getItem("access_token") ?? "");

  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  const [pendingProjectTarget, setPendingProjectTarget] = useState<ProjectTarget | null>(null);

  const [isLoginErrorOpen, setIsLoginErrorOpen] = useState(false);

  const [isSessionExpiredOpen, setIsSessionExpiredOpen] = useState(false);

  const [lastForbiddenPath, setLastForbiddenPath] = useState("");

  async function handleLogin() {
    try {
      setIsLoginErrorOpen(false);
      const result = await login(username, password);
      const nextProjectTarget = pendingProjectTarget;
      setPendingProjectTarget(null);
      closeLoginModal();
      setIsSessionExpiredOpen(false);
      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("username", result.username || username);
      localStorage.setItem("display_name", result.display_name || "");
      localStorage.setItem("user_email", result.email || "");
      setToken(result.access_token);
      setUsername(result.username || username);
      setDisplayName(result.display_name || "");
      setUserEmail(result.email || "");

      const nextRole = result.role || readRoleFromToken(result.access_token);
      const nextPosition = result.position || readPositionFromToken(result.access_token);
      localStorage.setItem("role", nextRole);
      if (nextPosition) {
        localStorage.setItem("position", nextPosition);
      } else {
        localStorage.removeItem("position");
      }
      const nextAllowedAiAppIds = result.allowed_ai_app_ids || [];
      localStorage.setItem("allowed_ai_app_ids", JSON.stringify(nextAllowedAiAppIds));
      setRole(nextRole);
      setPosition(nextPosition);
      setAllowedAiAppIds(nextAllowedAiAppIds);
      if (!canRoleAccessView(nextRole, activeView, nextPosition, nextAllowedAiAppIds)) {
        const text = "当前账号没有权限访问该页面，已返回概览。";
        setLastForbiddenPath(window.location.pathname);
        setStatusMessage(text);
        message.warning(text);
        navigateToView("dashboard", { replace: true });
      }
      setStatusMessage(`已登录：${username}`);
      message.success("登录成功");

      if (nextProjectTarget === "gateway") {
        window.location.assign(import.meta.env.VITE_GATEWAY_URL || "http://localhost:8082");
      } else if (nextProjectTarget === "automation") {
        navigateToView("dashboard");
      }

      onAuthenticated(result, nextRole, nextPosition);
    } catch (error) {
      setPassword("");
      const rawMessage = error instanceof Error ? error.message : "登录失败";
      const isInvalidCredentials = rawMessage.includes("用户名或密码错误");
      const text = isInvalidCredentials ? "账号密码错误" : rawMessage;
      setStatusMessage(text);
      if (isInvalidCredentials) {
        setIsLoginErrorOpen(true);
      } else {
        message.error(text);
      }
    }
  }

  function closeLoginModal() {
    setIsLoginModalOpen(false);
    setPassword("");
  }

  function resetSession() {
    for (const key of ["access_token", "username", "display_name", "user_email", "role", "position", "allowed_ai_app_ids"]) localStorage.removeItem(key);
    setToken("");
    setUsername("");
    setDisplayName("");
    setUserEmail("");
    setPassword("");
    setIsLoginModalOpen(false);
    setPendingProjectTarget(null);
    setIsLoginErrorOpen(false);
    setRole("employee");
    setPosition(null);
    setAllowedAiAppIds(null);
    setLastForbiddenPath("");
  }

  return {
    role,
    position,
    allowedAiAppIds,
    username,
    setUsername,
    displayName,
    setDisplayName,
    userEmail,
    setUserEmail,
    password,
    setPassword,
    token,
    isLoginModalOpen,
    setIsLoginModalOpen,
    setPendingProjectTarget,
    isLoginErrorOpen,
    setIsLoginErrorOpen,
    isSessionExpiredOpen,
    setIsSessionExpiredOpen,
    lastForbiddenPath,
    setLastForbiddenPath,
    handleLogin,
    closeLoginModal,
    resetSession,
  };
}
