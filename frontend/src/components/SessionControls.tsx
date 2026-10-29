import { LoginOutlined, DownOutlined, LogoutOutlined, SendOutlined, StopOutlined } from "@ant-design/icons";
import { Avatar, Button, Form, Input, Dropdown, Modal, Tag } from "antd";
import { type Position } from "../api";
import type { Role, PublicLLMChatMessage } from "../workspace/types";
import { Paragraph, Text, TextArea, roleLabel, positionLabel } from "../workspace/shared";

export function PublicLLMChatWidget(props: {
  open: boolean;
  input: string;
  messages: PublicLLMChatMessage[];
  isLoading: boolean;
  setInput: (value: string) => void;
  onClose: () => void;
  onSend: () => void;
}) {
  if (!props.open) {
    return null;
  }

  return (
    <div className="publicLlmWidget">
      <div className="publicLlmHeader">
        <div>
          <Text strong>大模型聊天</Text>
          <Paragraph type="secondary" className="publicLlmSubtitle">
            普通 AI 对话，不接入 RAG
          </Paragraph>
        </div>
        <Button size="small" type="text" icon={<StopOutlined />} onClick={props.onClose} />
      </div>

      <div className="publicLlmMessages">
        {props.messages.map((item) => (
          <div key={item.id} className={`publicLlmMessageRow ${item.role}`}>
            <div className={`publicLlmBubble ${item.role}`}>
              {item.content || (props.isLoading && item.role === "assistant" ? "正在思考..." : "")}
            </div>
          </div>
        ))}
      </div>

      <div className="publicLlmComposer">
        <TextArea
          value={props.input}
          placeholder="问我任何普通问题"
          autoSize={{ minRows: 2, maxRows: 4 }}
          onChange={(event) => props.setInput(event.target.value)}
          onPressEnter={(event) => {
            if (!event.shiftKey) {
              event.preventDefault();
              props.onSend();
            }
          }}
        />
        <Button
          type="primary"
          shape="circle"
          icon={<SendOutlined />}
          loading={props.isLoading}
          onClick={props.onSend}
        />
      </div>
    </div>
  );
}

export function UserMenu(props: {
  username: string;
  displayName: string;
  role: Role;
  position: Position | null;
  token: string;
  collapsed?: boolean;
  openLogin: () => void;
  logout: () => void;
}) {
  if (!props.token) {
    return (
      <Button type="text" icon={<LoginOutlined />} onClick={props.openLogin}>
        未登录
      </Button>
    );
  }
  const label = props.displayName || props.username;

  return (
    <Dropdown
      menu={{
        items: [
          {
            key: "logout",
            icon: <LogoutOutlined />,
            label: "退出登录",
            onClick: props.logout,
          },
        ],
      }}
      trigger={["click"]}
    >
      <Button
        type="text"
        className={props.collapsed ? "userMenuButton compact" : "userMenuButton"}
        title={label}
        aria-label={`${label}，${roleLabel(props.role)}${props.position ? `，${positionLabel(props.position)}` : ""}，账号菜单`}
      >
        {props.collapsed ? (
          <Avatar size="small" style={{ backgroundColor: "#1677ff" }}>
            {label.slice(0, 1).toUpperCase()}
          </Avatar>
        ) : (
          <span className="userMenuContent">
            <Avatar size="small" style={{ backgroundColor: "#1677ff" }}>
              {label.slice(0, 1).toUpperCase()}
            </Avatar>
            <span className="userMenuDetails">
              <span className="userMenuName">{label}</span>
              <span className="userMenuBadges">
                <Tag color={props.role === "admin" ? "blue" : "green"}>{roleLabel(props.role)}</Tag>
                {props.position ? <Tag color="purple">{positionLabel(props.position)}</Tag> : null}
              </span>
            </span>
            <DownOutlined className="userMenuChevron" />
          </span>
        )}
      </Button>
    </Dropdown>
  );
}

export function LoginModal(props: {
  open: boolean;
  username: string;
  password: string;
  setUsername: (value: string) => void;
  setPassword: (value: string) => void;
  onCancel: () => void;
  onLogin: () => void;
}) {
  return (
    <Modal
      title="登录企业内部后台"
      open={props.open}
      okText="登录"
      cancelText="取消"
      centered
      onOk={props.onLogin}
      onCancel={props.onCancel}
    >
      <Form layout="vertical" className="loginModalForm" autoComplete="off">
        <Form.Item label="用户名">
          <Input
            value={props.username}
            onChange={(event) => props.setUsername(event.target.value)}
            onPressEnter={props.onLogin}
            autoComplete="off"
          />
        </Form.Item>
        <Form.Item label="密码">
          <Input.Password
            value={props.password}
            onChange={(event) => props.setPassword(event.target.value)}
            onPressEnter={props.onLogin}
            autoComplete="new-password"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function LoginErrorModal(props: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Modal
      title="登录失败"
      open={props.open}
      width={360}
      centered
      okText="知道了"
      cancelButtonProps={{ style: { display: "none" } }}
      onOk={props.onClose}
      onCancel={props.onClose}
    >
      <Paragraph style={{ marginBottom: 0 }}>账号密码错误，请重新输入。</Paragraph>
    </Modal>
  );
}

export function SessionExpiredModal(props: {
  open: boolean;
  onLogin: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      open={props.open}
      title="登录失效"
      onCancel={props.onClose}
      footer={[
        <Button key="close" onClick={props.onClose}>
          稍后登录
        </Button>,
        <Button key="login" type="primary" onClick={props.onLogin}>
          重新登录
        </Button>,
      ]}
    >
      <Paragraph style={{ marginBottom: 0 }}>登录失效，需要重新登录。</Paragraph>
    </Modal>
  );
}
