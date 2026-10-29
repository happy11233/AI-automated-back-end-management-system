import { useState } from "react";
import { DeleteOutlined, ReloadOutlined, UserAddOutlined } from "@ant-design/icons";
import { Button, Drawer, Empty, Form, Input, Modal, Radio, Select, Space, Switch, Table, Tag } from "antd";
import { ProCard } from "@ant-design/pro-components";
import type { Position } from "../api";
import { type UserRecord, type NewUserForm, type Role } from "../workspace/types";
import { roleLabel, positionLabel, positionConfigs, Paragraph, Text, Title } from "../workspace/shared";

export function UsersPanel(props: {
  users: UserRecord[];
  newUser: NewUserForm;
  setNewUser: (value: NewUserForm) => void;
  createUser: () => void;
  deleteUser: (userId: string) => void;
  toggleUserAiApp: (userId: string, appId: string, enabled: boolean) => void;
  refreshUsers: () => void;
  isCreating: boolean;
  deletingUserId: string;
  updatingUserAppKey: string;
  currentUsername: string;
}) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const selectedPosition = props.newUser.position || "customer_service";

  function patchNewUser(patch: Partial<NewUserForm>) {
    props.setNewUser({
      ...props.newUser,
      ...patch,
    });
  }

  return (
    <>
      <ProCard
        title="用户详细与 AI 应用权限"
        bordered
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={props.refreshUsers}>
              刷新
            </Button>
            <Button type="primary" icon={<UserAddOutlined />} onClick={() => setIsCreateOpen(true)}>
              新建用户
            </Button>
          </Space>
        }
      >
        <Table<UserRecord>
          rowKey="id"
          dataSource={props.users}
          locale={{ emptyText: <Empty description="暂无用户数据" /> }}
          scroll={{ x: 980 }}
          expandable={{
            expandedRowRender: (user) => (
              <UserAiAppPermissionGrid
                user={user}
                updatingUserAppKey={props.updatingUserAppKey}
                toggleUserAiApp={props.toggleUserAiApp}
              />
            ),
            rowExpandable: (user) => user.aiAppPermissions.length > 0,
          }}
          columns={[
            { title: "用户名", dataIndex: "username", width: 150 },
            {
              title: "角色",
              dataIndex: "role",
              width: 110,
              render: (value) => <Tag>{roleLabel(value as Role)}</Tag>,
            },
            {
              title: "岗位",
              dataIndex: "position",
              width: 110,
              render: (value) => (value ? <Tag color="purple">{positionLabel(value as Position)}</Tag> : "-"),
            },
            { title: "部门", dataIndex: "department", width: 130 },
            {
              title: "AI 应用",
              dataIndex: "capabilities",
              render: (_, user) => (
                <Space size={[4, 4]} wrap>
                  <Tag color="green">{user.allowedAiAppIds.length} 个已启用</Tag>
                  <Tag>{user.aiAppPermissions.length} 个可配置</Tag>
                </Space>
              ),
            },
            { title: "创建时间", dataIndex: "createdAt", width: 150 },
            {
              title: "操作",
              width: 120,
              fixed: "right",
              render: (_, user) => {
                const canDelete = user.username !== props.currentUsername;
                return (
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    disabled={!canDelete}
                    loading={props.deletingUserId === user.id}
                    onClick={() => {
                      Modal.confirm({
                        title: `删除用户 ${user.username}`,
                        content: "删除后该用户无法再登录，历史记录中的用户关联会按数据库外键规则处理。",
                        okText: "确认删除",
                        cancelText: "取消",
                        okButtonProps: { danger: true },
                        onOk: () => props.deleteUser(user.id),
                      });
                    }}
                  >
                    删除
                  </Button>
                );
              },
            },
          ]}
        />
      </ProCard>
      <Drawer
        title="创建用户"
        open={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        width="min(640px, 100vw)"
      >
        <div className="workspaceLayout">
          <ProCard title="管理员创建用户" bordered>
            <Form layout="vertical" className="userCreateForm">
              <Form.Item label="用户名">
                <Input
                  value={props.newUser.username}
                  onChange={(event) => patchNewUser({ username: event.target.value })}
                  placeholder="例如 service_01"
                />
              </Form.Item>
              <Form.Item label="密码">
                <Input.Password
                  value={props.newUser.password}
                  onChange={(event) => patchNewUser({ password: event.target.value })}
                  placeholder="至少 6 位"
                />
              </Form.Item>
              <Form.Item label="系统角色">
                <Radio.Group
                  optionType="button"
                  buttonStyle="solid"
                  value={props.newUser.role}
                  onChange={(event) => {
                    const nextRole = event.target.value as Role;
                    patchNewUser({
                      role: nextRole,
                      position: nextRole === "employee" ? selectedPosition : null,
                    });
                  }}
                  options={[
                    { label: "员工", value: "employee" },
                    { label: "管理员", value: "admin" },
                  ]}
                />
              </Form.Item>
              {props.newUser.role === "employee" ? (
                <Form.Item label="岗位">
                  <Select
                    value={selectedPosition}
                    onChange={(value) =>
                      patchNewUser({
                        position: value,
                        department: props.newUser.department || positionConfigs[value].department,
                      })
                    }
                    options={(Object.keys(positionConfigs) as Position[]).map((item) => ({
                      label: positionConfigs[item].label,
                      value: item,
                    }))}
                  />
                </Form.Item>
              ) : null}
              <Form.Item label="部门">
                <Input
                  value={props.newUser.department}
                  onChange={(event) => patchNewUser({ department: event.target.value })}
                  placeholder={
                    props.newUser.role === "employee"
                      ? positionConfigs[selectedPosition].department
                      : "管理部"
                  }
                />
              </Form.Item>
              <Form.Item className="userCreateActions">
                <Space>
                  <Button type="primary" loading={props.isCreating} onClick={props.createUser}>
                    创建用户
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={props.refreshUsers}>
                    刷新
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </ProCard>
        </div>
      </Drawer>
    </>
  );
}

export function UserAiAppPermissionGrid({
  user,
  updatingUserAppKey,
  toggleUserAiApp,
}: {
  user: UserRecord;
  updatingUserAppKey: string;
  toggleUserAiApp: (userId: string, appId: string, enabled: boolean) => void;
}) {
  return (
    <div className="userAiAppGrid">
      {user.aiAppPermissions.map((app) => {
        const loading = updatingUserAppKey === `${user.id}:${app.id}`;

        return (
          <div key={`${user.id}-${app.id}`} className="userAiAppItem">
            <div className="userAiAppInfo">
              <Text strong>{app.name}</Text>
              <Space size={[4, 4]} wrap>
                <Tag>{app.position_label}</Tag>
                <Tag color="blue">{app.category}</Tag>
              </Space>
            </div>
            <Switch
              checked={app.enabled}
              loading={loading}
              checkedChildren="启用"
              unCheckedChildren="禁用"
              onChange={(checked) => toggleUserAiApp(user.id, app.id, checked)}
            />
          </div>
        );
      })}
    </div>
  );
}
