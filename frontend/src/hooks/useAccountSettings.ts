import { useState } from "react";
import { message } from "antd";
import { getMySettings, isAuthExpiredError, updateMyPassword, updateMyProfile, type UserSettingsItem } from "../api";
import type { UserProfileFormState, UserPasswordFormState } from "../workspace/types";

export function useAccountSettings({ token, setUsername, setDisplayName, setUserEmail, setStatusMessage }: { token: string; setUsername: (value: string) => void; setDisplayName: (value: string) => void; setUserEmail: (value: string) => void; setStatusMessage: (value: string) => void }) {
  const [userSettings, setUserSettings] = useState<UserSettingsItem | null>(null);

  const [profileForm, setProfileForm] = useState<UserProfileFormState>({
    displayName: localStorage.getItem("display_name") ?? "",
    email: localStorage.getItem("user_email") ?? "",
  });

  const [passwordForm, setPasswordForm] = useState<UserPasswordFormState>({
    oldPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  const [isLoadingUserSettings, setIsLoadingUserSettings] = useState(false);

  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const [isSavingPassword, setIsSavingPassword] = useState(false);

  function applyUserSettings(item: UserSettingsItem) {
    const nextDisplayName = item.display_name || "";
    const nextEmail = item.email || "";
    setUserSettings(item);
    setDisplayName(nextDisplayName);
    setUserEmail(nextEmail);
    setProfileForm({
      displayName: nextDisplayName,
      email: nextEmail,
    });
    localStorage.setItem("display_name", nextDisplayName);
    localStorage.setItem("user_email", nextEmail);
  }

  async function refreshUserSettings(activeToken = token) {
    if (!activeToken) {
      setUserSettings(null);
      return;
    }

    setIsLoadingUserSettings(true);
    try {
      const result = await getMySettings(activeToken);
      applyUserSettings(result.item);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "用户设置加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsLoadingUserSettings(false);
    }
  }

  async function handleSaveUserProfile() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    setIsSavingProfile(true);
    try {
      const result = await updateMyProfile(token, {
        display_name: profileForm.displayName.trim() || null,
        email: profileForm.email.trim() || null,
      });
      applyUserSettings(result.item);
      setStatusMessage("用户资料已保存");
      message.success("用户资料已保存");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "用户资料保存失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handleSaveUserPassword() {
    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setStatusMessage("两次输入的新密码不一致");
      message.warning("两次输入的新密码不一致");
      return;
    }

    setIsSavingPassword(true);
    try {
      await updateMyPassword(token, {
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      });
      setPasswordForm({ oldPassword: "", newPassword: "", confirmPassword: "" });
      setStatusMessage("密码已修改");
      message.success("密码已修改");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "密码修改失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsSavingPassword(false);
    }
  }
  function resetAccountSettings() {
    setUserSettings(null);
    setProfileForm({ displayName: "", email: "" });
    setPasswordForm({
      oldPassword: "",
      newPassword: "",
      confirmPassword: "",
    });
    setIsLoadingUserSettings(false);
    setIsSavingProfile(false);
    setIsSavingPassword(false);
  }

  return {
    profileForm,
    setProfileForm,
    passwordForm,
    setPasswordForm,
    isLoadingUserSettings,
    isSavingProfile,
    isSavingPassword,
    refreshUserSettings,
    handleSaveUserProfile,
    handleSaveUserPassword,
    resetAccountSettings,
  };
}
