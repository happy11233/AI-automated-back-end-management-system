import React from "react";
import { EditOutlined, ReloadOutlined } from "@ant-design/icons";
import { Avatar, Button, Form, Input, Space, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import { WorkspaceTabs } from "../components/WorkspaceCharts";
import type { Position } from "../api";
import { type Role, type UserProfileFormState, type UserPasswordFormState } from "../workspace/types";
import { Paragraph, Text, Title, positionLabel, roleLabel } from "../workspace/shared";

export function UserSettingsPanel({
  username,
  displayName,
  email,
  role,
  position,
  profileForm,
  setProfileForm,
  passwordForm,
  setPasswordForm,
  loading,
  savingProfile,
  savingPassword,
  refreshSettings,
  saveProfile,
  savePassword,
}: {
  username: string;
  displayName: string;
  email: string;
  role: Role;
  position: Position | null;
  profileForm: UserProfileFormState;
  setProfileForm: React.Dispatch<React.SetStateAction<UserProfileFormState>>;
  passwordForm: UserPasswordFormState;
  setPasswordForm: React.Dispatch<React.SetStateAction<UserPasswordFormState>>;
  loading: boolean;
  savingProfile: boolean;
  savingPassword: boolean;
  refreshSettings: () => void;
  saveProfile: () => void;
  savePassword: () => void;
}) {
  return (
    <Space direction="vertical" className="pageStack">
      <div className="workspaceIdentity">
        <Avatar size={48} style={{ background: "#e9f0ff", color: "#2563eb" }}>
          {(displayName || username || "U").slice(0, 1)}
        </Avatar>
        <div>
          <Text strong>{displayName || username}</Text>
          <Text type="secondary">
            {username} · {position ? positionLabel(position) : roleLabel(role)}
          </Text>
        </div>
        <Tag color="blue">{roleLabel(role)}</Tag>
      </div>
      <WorkspaceTabs
        storageKey="settings_tab"
        items={[
          {
            key: "profile",
            label: "基本资料",
            children: (
              <ProCard
                title="账号资料"
                subTitle="账号不可修改；AI 邮件自动发送会读取这里设置的邮箱"
                bordered
                extra={
                  <Button size="small" icon={<ReloadOutlined />} onClick={refreshSettings} loading={loading}>
                    刷新
                  </Button>
                }
              >
                <Form layout="vertical" className="userSettingsForm">
                  <Form.Item label="账号">
                    <Input value={username} disabled />
                  </Form.Item>
                  <Form.Item label="角色">
                    <Input value={roleLabel(role)} disabled />
                  </Form.Item>
                  <Form.Item label="岗位">
                    <Input value={position ? positionLabel(position) : "管理员"} disabled />
                  </Form.Item>
                  <Form.Item label="名称">
                    <Input
                      value={profileForm.displayName}
                      maxLength={80}
                      placeholder="例如：财务主管"
                      onChange={(event) =>
                        setProfileForm((current) => ({
                          ...current,
                          displayName: event.target.value,
                        }))
                      }
                    />
                  </Form.Item>
                  <Form.Item label="邮箱">
                    <Input
                      value={profileForm.email}
                      maxLength={180}
                      placeholder="例如：finance@example.com"
                      onChange={(event) =>
                        setProfileForm((current) => ({
                          ...current,
                          email: event.target.value,
                        }))
                      }
                    />
                  </Form.Item>
                  <Form.Item className="userSettingsActions">
                    <Button
                      type="primary"
                      icon={<EditOutlined />}
                      loading={savingProfile}
                      onClick={saveProfile}
                    >
                      保存资料
                    </Button>
                  </Form.Item>
                </Form>
              </ProCard>
            ),
          },
          {
            key: "security",
            label: "账号安全",
            children: (
              <ProCard title="修改密码" subTitle="修改后下一次登录请使用新密码" bordered>
                <Form layout="vertical" className="userSettingsForm password">
                  <Form.Item label="当前密码">
                    <Input.Password
                      value={passwordForm.oldPassword}
                      onChange={(event) =>
                        setPasswordForm((current) => ({
                          ...current,
                          oldPassword: event.target.value,
                        }))
                      }
                    />
                  </Form.Item>
                  <Form.Item label="新密码">
                    <Input.Password
                      value={passwordForm.newPassword}
                      onChange={(event) =>
                        setPasswordForm((current) => ({
                          ...current,
                          newPassword: event.target.value,
                        }))
                      }
                    />
                  </Form.Item>
                  <Form.Item label="确认新密码">
                    <Input.Password
                      value={passwordForm.confirmPassword}
                      onChange={(event) =>
                        setPasswordForm((current) => ({
                          ...current,
                          confirmPassword: event.target.value,
                        }))
                      }
                      onPressEnter={savePassword}
                    />
                  </Form.Item>
                  <Form.Item className="userSettingsActions">
                    <Button type="primary" loading={savingPassword} onClick={savePassword}>
                      修改密码
                    </Button>
                  </Form.Item>
                </Form>
              </ProCard>
            ),
          },
        ]}
      />
    </Space>
  );
}
