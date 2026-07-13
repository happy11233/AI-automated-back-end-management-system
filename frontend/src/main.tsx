import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AuditOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  CommentOutlined,
  DatabaseOutlined,
  LoginOutlined,
  DownOutlined,
  FileTextOutlined,
  HistoryOutlined,
  LogoutOutlined,
  MessageOutlined,
  ReloadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  SearchOutlined,
  StopOutlined,
} from "@ant-design/icons";
import {
  App as AntApp,
  Avatar,
  Button,
  Card,
  Col,
  ConfigProvider,
  Empty,
  Form,
  Input,
  Dropdown,
  Modal,
  Radio,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
  theme,
  type UploadFile,
} from "antd";
import {
  PageContainer,
  ProCard,
  ProConfigProvider,
  ProLayout,
  StatisticCard,
} from "@ant-design/pro-components";
import "./styles.css";
import {
  login,
  sendPublicLLMChatStream,
  sendChatStream,
  uploadDocument,
  listApprovals,
  listAuditLogs,
  listRefunds,
  getThreadMessages,
  reviewApproval as reviewApprovalApi,
  type ApprovalItem,
  type AuditLogItem,
  type PublicLLMMessage,
  type RefundItem,
  type ThreadMessageItem,
} from "./api";
import { Contact } from "./portal/components/Contact";
import { Hero } from "./portal/components/Hero";
import { Navbar } from "./portal/components/Navbar";
import { Projects } from "./portal/components/Projects";
import { Skills } from "./portal/components/Skills";
import type { Language } from "./portal/data/content";

const { Paragraph, Text, Title } = Typography;
const { TextArea } = Input;

type Role = "admin" | "employee";
type ChatRoute = "refund_workflow" | "order_agent" | "knowledge_rag";
type View =
  | "dashboard"
  | "chat"
  | "documents"
  | "approvals"
  | "refunds"
  | "audit"
  | "threads";

type NavItem = {
  path: string;
  id: View;
  name: string;
  icon: React.ReactNode;
  roles: Role[];
};

type ChatMessage = {
  id: string;
  threadId: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: string;
  route?: ChatRoute;
};

type PublicLLMChatMessage = PublicLLMMessage & {
  id: string;
};

type Approval = {
  id: string;
  threadId: string;
  actionType: string;
  status: string;
  orderNo: string;
  amount: string;
  reason: string;
  createdAt: string;
};

type Refund = {
  id: string;
  approvalId: string;
  orderNo: string;
  amount: string;
  status: string;
  createdAt: string;
};

type AuditLog = {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  actor: string;
  createdAt: string;
};

const navItems: NavItem[] = [
  { path: "/dashboard", id: "dashboard", name: "概览", icon: <DatabaseOutlined />, roles: ["admin", "employee"] },
  { path: "/chat", id: "chat", name: "客服对话", icon: <MessageOutlined />, roles: ["admin", "employee"] },
  { path: "/documents", id: "documents", name: "知识库", icon: <FileTextOutlined />, roles: ["admin"] },
  { path: "/approvals", id: "approvals", name: "审批", icon: <CheckCircleOutlined />, roles: ["admin"] },
  { path: "/refunds", id: "refunds", name: "退款流水", icon: <HistoryOutlined />, roles: ["admin"] },
  { path: "/audit", id: "audit", name: "审计日志", icon: <AuditOutlined />, roles: ["admin"] },
  { path: "/threads", id: "threads", name: "会话详情", icon: <RobotOutlined />, roles: ["admin", "employee"] },
];

function App() {
  const [language, setLanguage] = useState<Language>("zh");
  const [activeView, setActiveView] = useState<View>("dashboard");
  const [role, setRole] = useState<Role>(readStoredRole);
  const [username, setUsername] = useState(localStorage.getItem("username") ?? "");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("access_token") ?? "");
  const [statusMessage, setStatusMessage] = useState("系统就绪");
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isLoginErrorOpen, setIsLoginErrorOpen] = useState(false);
  const [isPublicLLMOpen, setIsPublicLLMOpen] = useState(false);
  const [publicLLMInput, setPublicLLMInput] = useState("");
  const [publicLLMMessages, setPublicLLMMessages] = useState<PublicLLMChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好，有什么可以帮你的？（当前知识截止2024.6.18，未接入联网搜索）",
    },
  ]);
  const [isPublicLLMLoading, setIsPublicLLMLoading] = useState(false);

  const [messageInput, setMessageInput] = useState("");
  const [threadInput, setThreadInput] = useState("thread-10086");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentVisibility, setDocumentVisibility] = useState<Role>("employee");
  const [documentDepartment, setDocumentDepartment] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const [threadFilter, setThreadFilter] = useState("thread-10086");
  const [threadSummary, setThreadSummary] = useState("");
  const [threadStateText, setThreadStateText] = useState("");

  const pendingCount = approvals.filter((item) => item.status === "pending").length;
  const succeededRefunds = refunds.filter((item) => item.status === "succeeded").length;
  const visibleNavItems = useMemo(
    () => navItems.filter((item) => item.roles.includes(role)),
    [role],
  );
  const route = useMemo(
    () => ({
      path: "/",
      routes: visibleNavItems,
    }),
    [visibleNavItems],
  );
  const safeActiveView = visibleNavItems.some((item) => item.id === activeView) ? activeView : "dashboard";
  const currentPath = visibleNavItems.find((item) => item.id === safeActiveView)?.path || "/dashboard";

  const stats = useMemo(
    () => [
      { title: "待审批", value: pendingCount, suffix: "条" },
      { title: "退款成功", value: succeededRefunds, suffix: "笔" },
      { title: "会话消息", value: messages.length, suffix: "条" },
      { title: "审计日志", value: auditLogs.length, suffix: "条" },
    ],
    [auditLogs.length, messages.length, pendingCount, succeededRefunds],
  );

  async function handleLogin() {
    try {
      setIsLoginErrorOpen(false);
      const result = await login(username, password);
      localStorage.setItem("access_token", result.access_token);
      localStorage.setItem("username", username);
      setToken(result.access_token);

      const nextRole = readRoleFromToken(result.access_token);
      localStorage.setItem("role", nextRole);
      setRole(nextRole);
      if (!canRoleAccessView(nextRole, activeView)) {
        setActiveView("dashboard");
      }
      setStatusMessage(`已登录：${username}`);
      message.success("登录成功");

      if (nextRole === "admin") {
        await refreshAdminData(result.access_token);
      }

      setIsLoginModalOpen(false);
    } catch (error) {
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

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    setToken("");
    setRole("employee");
    setMessages([]);
    setApprovals([]);
    setRefunds([]);
    setAuditLogs([]);
    setThreadSummary("");
    setThreadStateText("");
    setStatusMessage("已退出登录");
    message.success("已退出登录");
  }

  async function refreshAdminData(activeToken = token) {
    if (!activeToken) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      const [approvalResult, refundResult, auditResult] = await Promise.all([
        listApprovals(activeToken),
        listRefunds(activeToken),
        listAuditLogs(activeToken),
      ]);

      setApprovals(approvalResult.items.map(mapApproval));
      setRefunds(refundResult.items.map(mapRefund));
      setAuditLogs(auditResult.items.map(mapAuditLog));
      setStatusMessage("后台数据已刷新");
      message.success("后台数据已刷新");
    } catch (error) {
      const text = error instanceof Error ? error.message : "刷新失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function sendMessage() {
    const messageText = messageInput.trim();

    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!messageText || isChatLoading) {
      return;
    }

    const threadId = threadInput.trim() || `thread-${Date.now()}`;
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      threadId,
      role: "user",
      content: messageText,
      createdAt: "刚刚",
    };
    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      threadId,
      role: "assistant",
      content: "",
      createdAt: "正在生成",
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setMessageInput("");
    setIsChatLoading(true);
    setStatusMessage("正在流式生成回答");

    try {
      await sendChatStream(token, messageText, threadId, {
        onStart: (payload) => {
          const nextThreadId = payload.thread_id || threadId;
          setThreadInput(nextThreadId);
          setThreadFilter(nextThreadId);
        },
        onNode: (payload) => {
          if (payload.node) {
            setStatusMessage(`正在执行节点：${payload.node}`);
          }
        },
        onContent: (payload) => {
          const chunk = payload.content || "";
          const nextThreadId = payload.thread_id || threadId;

          setThreadInput(nextThreadId);
          setThreadFilter(nextThreadId);
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessageId
                ? {
                    ...item,
                    threadId: nextThreadId,
                    content: item.content + chunk,
                  }
                : item,
            ),
          );
        },
        onDone: (payload) => {
          const finalThreadId = payload.thread_id || threadId;

          setThreadInput(finalThreadId);
          setThreadFilter(finalThreadId);
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantMessageId
                ? {
                    ...item,
                    threadId: finalThreadId,
                    content: item.content || payload.answer || "",
                    createdAt: "刚刚",
                    route: routeFromIntent(payload.intent ?? null, payload.risk_level ?? null),
                  }
                : item,
            ),
          );
        },
        onError: (payload) => {
          throw new Error(payload.message || "流式聊天失败");
        },
      });

      setStatusMessage("聊天完成");

      if (role === "admin") {
        await refreshAdminData();
      }
    } catch (error) {
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId && !item.content
            ? {
                ...item,
                content: "生成失败，请稍后重试。",
                createdAt: "刚刚",
              }
            : item,
        ),
      );
      const text = error instanceof Error ? error.message : "发送失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsChatLoading(false);
    }
  }

  async function sendPublicLLMMessage() {
    const messageText = publicLLMInput.trim();

    if (!messageText || isPublicLLMLoading) {
      return;
    }

    const userMessage: PublicLLMChatMessage = {
      id: `public-user-${Date.now()}`,
      role: "user",
      content: messageText,
    };

    const history = [...publicLLMMessages, userMessage]
      .filter((item) => item.id !== "welcome")
      .map(({ role, content }) => ({ role, content }));

    const assistantMessageId = `public-assistant-${Date.now()}`;
    const assistantMessage: PublicLLMChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
    };

    setPublicLLMMessages((current) => [...current, userMessage, assistantMessage]);
    setPublicLLMInput("");
    setIsPublicLLMLoading(true);

    try {
      await sendPublicLLMChatStream(messageText, history, (chunk) => {
        if (!chunk) {
          return;
        }

        setPublicLLMMessages((current) =>
          current.map((item) =>
            item.id === assistantMessageId
              ? {
                  ...item,
                  content: item.content + chunk,
                }
              : item,
          ),
        );
      });

      setPublicLLMMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId && !item.content
            ? {
                ...item,
                content: "我暂时没有生成回答。",
              }
            : item,
        ),
      );
    } catch (error) {
      const text = error instanceof Error ? error.message : "大模型聊天失败";
      setPublicLLMMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId
            ? {
                ...item,
                content: `发送失败：${text}`,
              }
            : item,
        ),
      );
    } finally {
      setIsPublicLLMLoading(false);
    }
  }

  async function reviewApproval(id: string, approved: boolean) {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    try {
      await reviewApprovalApi(token, id, approved);
      await refreshAdminData();
      const text = approved ? "审批已通过" : "审批已拒绝";
      setStatusMessage(text);
      message.success(text);
    } catch (error) {
      const text = error instanceof Error ? error.message : "审批失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  async function handleUploadDocument() {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    if (!documentFile) {
      setStatusMessage("请选择要上传的文件");
      message.warning("请选择要上传的文件");
      return;
    }

    setIsUploading(true);
    setStatusMessage("正在上传并入库");

    try {
      await uploadDocument(token, documentFile, documentVisibility, documentDepartment);
      setDocumentFile(null);
      setStatusMessage("文档上传并入库成功");
      message.success("文档上传并入库成功");

      if (role === "admin") {
        await refreshAdminData();
      }
    } catch (error) {
      const text = error instanceof Error ? error.message : "上传失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsUploading(false);
    }
  }

  async function loadThreadMessages() {
    const threadId = threadFilter.trim();

    if (!token) {
      setStatusMessage("请先登录");
      message.warning("请先登录");
      return;
    }

    if (!threadId) {
      setStatusMessage("请输入 Thread ID");
      message.warning("请输入 Thread ID");
      return;
    }

    try {
      const result = await getThreadMessages(token, threadId);

      setMessages(result.messages.map(mapThreadMessage));
      setThreadSummary(String(result.summary.summary || ""));
      setThreadStateText(JSON.stringify(result.state, null, 2));
      setStatusMessage("会话已加载");
      message.success("会话已加载");
    } catch (error) {
      const text = error instanceof Error ? error.message : "查询会话失败";
      setStatusMessage(text);
      message.error(text);
    }
  }

  if (!token) {
    return (
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: "#1677ff",
            borderRadius: 6,
            wireframe: false,
          },
        }}
      >
        <AntApp>
          <PublicPortal
            language={language}
            onLanguageChange={() => setLanguage((current) => (current === "zh" ? "en" : "zh"))}
            onLoginClick={() => setIsLoginModalOpen(true)}
            onLLMClick={() => setIsPublicLLMOpen(true)}
          />
          <PublicLLMChatWidget
            open={isPublicLLMOpen}
            input={publicLLMInput}
            messages={publicLLMMessages}
            isLoading={isPublicLLMLoading}
            setInput={setPublicLLMInput}
            onClose={() => setIsPublicLLMOpen(false)}
            onSend={sendPublicLLMMessage}
          />
          <LoginModal
            open={isLoginModalOpen}
            username={username}
            password={password}
            setUsername={setUsername}
            setPassword={setPassword}
            onCancel={() => setIsLoginModalOpen(false)}
            onLogin={handleLogin}
          />
          <LoginErrorModal
            open={isLoginErrorOpen}
            onClose={() => setIsLoginErrorOpen(false)}
          />
        </AntApp>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 6,
          wireframe: false,
        },
      }}
    >
      <ProConfigProvider hashed={false}>
        <AntApp>
          <ProLayout
            title="Company RAG Agent"
            logo={<SafetyCertificateOutlined />}
            route={route}
            location={{ pathname: currentPath }}
            layout="mix"
            splitMenus={false}
            siderWidth={224}
            menuItemRender={(item, dom) => (
              <button
                className="menuButton"
                type="button"
                onClick={() => {
                  const matched = visibleNavItems.find((nav) => nav.path === item.path);
                  if (matched) {
                    setActiveView(matched.id);
                  }
                }}
              >
                {dom}
              </button>
            )}
            actionsRender={() =>
              role === "admin"
                ? [
                    <Button key="refresh" icon={<ReloadOutlined />} onClick={() => refreshAdminData()}>
                      刷新
                    </Button>,
                  ]
                : []
            }
            avatarProps={{
              src: undefined,
              title: token ? username : "未登录",
              render: () => (
                <UserMenu
                  username={username}
                  role={role}
                  token={token}
                  openLogin={() => setIsLoginModalOpen(true)}
                  logout={handleLogout}
                />
              ),
            }}
            token={{
              header: {
                colorBgHeader: "#ffffff",
              },
              sider: {
                colorMenuBackground: "#ffffff",
              },
            }}
          >
            <PageContainer
              title={titleForView(safeActiveView)}
              subTitle={pageSubtitle(role)}
              extra={[
                <Text key="status" type="secondary">
                  {statusMessage}
                </Text>,
              ]}
            >
              <Space direction="vertical" size={16} className="pageStack">
                {safeActiveView === "dashboard" && (
                  <Dashboard
                    stats={stats}
                    approvals={approvals}
                    refunds={refunds}
                    role={role}
                  />
                )}
                {safeActiveView === "chat" && (
                  <ChatPanel
                    messageInput={messageInput}
                    setMessageInput={setMessageInput}
                    threadInput={threadInput}
                    setThreadInput={setThreadInput}
                    sendMessage={sendMessage}
                    messages={messages}
                    isLoading={isChatLoading}
                  />
                )}
                {safeActiveView === "documents" && role === "admin" && (
                  <DocumentsPanel
                    file={documentFile}
                    setFile={setDocumentFile}
                    visibility={documentVisibility}
                    setVisibility={setDocumentVisibility}
                    department={documentDepartment}
                    setDepartment={setDocumentDepartment}
                    uploadDocument={handleUploadDocument}
                    role={role}
                    isUploading={isUploading}
                  />
                )}
                {safeActiveView === "approvals" && role === "admin" && (
                  <ApprovalsPanel approvals={approvals} reviewApproval={reviewApproval} role={role} />
                )}
                {safeActiveView === "refunds" && role === "admin" && <RefundsPanel refunds={refunds} />}
                {safeActiveView === "audit" && role === "admin" && <AuditPanel logs={auditLogs} />}
                {safeActiveView === "threads" && (
                  <ThreadsPanel
                    threadFilter={threadFilter}
                    setThreadFilter={setThreadFilter}
                    loadThreadMessages={loadThreadMessages}
                    messages={messages.filter((item) => item.threadId === threadFilter)}
                    summary={threadSummary}
                    stateText={threadStateText}
                  />
                )}
              </Space>
            </PageContainer>
            <LoginModal
              open={isLoginModalOpen}
              username={username}
              password={password}
              setUsername={setUsername}
              setPassword={setPassword}
              onCancel={() => setIsLoginModalOpen(false)}
              onLogin={handleLogin}
            />
            <LoginErrorModal
              open={isLoginErrorOpen}
              onClose={() => setIsLoginErrorOpen(false)}
            />
          </ProLayout>
        </AntApp>
      </ProConfigProvider>
    </ConfigProvider>
  );
}

function PublicPortal(props: {
  language: Language;
  onLanguageChange: () => void;
  onLoginClick: () => void;
  onLLMClick: () => void;
}) {
  return (
    <main className="portfolioShell">
      <Navbar
        language={props.language}
        onLanguageChange={props.onLanguageChange}
        onLoginClick={props.onLoginClick}
        onLLMClick={props.onLLMClick}
      />
      <Hero language={props.language} />
      <Skills language={props.language} />
      <Projects language={props.language} />
      <Contact language={props.language} />
    </main>
  );
}

function PublicLLMChatWidget(props: {
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

function UserMenu(props: {
  username: string;
  role: Role;
  token: string;
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
      <Button type="text" className="userMenuButton">
        <Space size={8}>
          <Avatar size="small" style={{ backgroundColor: "#1677ff" }}>
            {props.username.slice(0, 1).toUpperCase()}
          </Avatar>
          <Text>{props.username}</Text>
          <Tag color={props.role === "admin" ? "blue" : "green"}>{roleLabel(props.role)}</Tag>
          <DownOutlined />
        </Space>
      </Button>
    </Dropdown>
  );
}

function LoginModal(props: {
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
      title="登录 Company RAG Agent"
      open={props.open}
      okText="登录"
      cancelText="取消"
      centered
      onOk={props.onLogin}
      onCancel={props.onCancel}
    >
      <Form layout="vertical" className="loginModalForm">
        <Form.Item label="用户名">
          <Input
            value={props.username}
            onChange={(event) => props.setUsername(event.target.value)}
            onPressEnter={props.onLogin}
          />
        </Form.Item>
        <Form.Item label="密码">
          <Input.Password
            value={props.password}
            onChange={(event) => props.setPassword(event.target.value)}
            onPressEnter={props.onLogin}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function LoginErrorModal(props: {
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

function Dashboard({
  stats,
  approvals,
  refunds,
  role,
}: {
  stats: Array<{ title: string; value: number; suffix: string }>;
  approvals: Approval[];
  refunds: Refund[];
  role: Role;
}) {
  const visibleStats = role === "admin"
    ? stats
    : stats.filter((item) => item.title === "会话消息");

  return (
    <Space direction="vertical" size={16} className="pageStack">
      <StatisticCard.Group direction="row">
        {visibleStats.map((item) => (
          <StatisticCard
            key={item.title}
            statistic={{
              title: item.title,
              value: item.value,
              suffix: item.suffix,
            }}
          />
        ))}
      </StatisticCard.Group>

      {role === "admin" ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={14}>
            <ProCard title="待处理事项" bordered>
              <Table<Approval>
                rowKey="id"
                size="middle"
                pagination={false}
                dataSource={approvals.slice(0, 5)}
                locale={{ emptyText: <Empty description="暂无待审批数据" /> }}
                columns={[
                  { title: "订单", dataIndex: "orderNo" },
                  { title: "金额", dataIndex: "amount" },
                  { title: "状态", dataIndex: "status", render: (value) => <StatusTag value={String(value)} /> },
                  { title: "创建时间", dataIndex: "createdAt" },
                ]}
              />
            </ProCard>
          </Col>
          <Col xs={24} xl={10}>
            <ProCard title="最近退款" bordered>
              <Table<Refund>
                rowKey="id"
                size="middle"
                pagination={false}
                dataSource={refunds.slice(0, 5)}
                locale={{ emptyText: <Empty description="暂无退款流水" /> }}
                columns={[
                  { title: "订单", dataIndex: "orderNo" },
                  { title: "金额", dataIndex: "amount" },
                  { title: "状态", dataIndex: "status", render: (value) => <StatusTag value={String(value)} /> },
                ]}
              />
            </ProCard>
          </Col>
        </Row>
      ) : (
        <ProCard title="工作台" bordered>
          <Empty description="可从左侧进入客服对话或查询自己的会话详情" />
        </ProCard>
      )}
    </Space>
  );
}

function ChatPanel(props: {
  messageInput: string;
  setMessageInput: (value: string) => void;
  threadInput: string;
  setThreadInput: (value: string) => void;
  sendMessage: () => void;
  messages: ChatMessage[];
  isLoading: boolean;
}) {
  return (
    <ProCard bordered className="chatWorkspace" bodyStyle={{ padding: 0, height: "100%" }}>
      <div className="chatMessagesPane">
        <MessageList messages={props.messages} />
      </div>

      <div className="chatComposerWrap">
        <div className="chatThreadBar">
          <Text type="secondary">会话 ID</Text>
          <Input
            size="small"
            value={props.threadInput}
            onChange={(event) => props.setThreadInput(event.target.value)}
          />
        </div>
        <div className="chatComposer">
          <TextArea
            variant="borderless"
            placeholder="输入客服问题，按按钮发送到后端"
            value={props.messageInput}
            onChange={(event) => props.setMessageInput(event.target.value)}
            autoSize={{ minRows: 3, maxRows: 8 }}
            onPressEnter={(event) => {
              if (!event.shiftKey) {
                event.preventDefault();
                props.sendMessage();
              }
            }}
          />
          <div className="chatComposerFooter">
            <Space size={8}>
              <Tag color="blue">SSE 流式</Tag>
              <Tag color="green">LangGraph</Tag>
            </Space>
            <Button
              type="primary"
              shape="circle"
              icon={<CommentOutlined />}
              loading={props.isLoading}
              onClick={props.sendMessage}
            />
          </div>
        </div>
      </div>
    </ProCard>
  );
}

function DocumentsPanel(props: {
  file: File | null;
  setFile: (value: File | null) => void;
  visibility: Role;
  setVisibility: (value: Role) => void;
  department: string;
  setDepartment: (value: string) => void;
  uploadDocument: () => void;
  role: Role;
  isUploading: boolean;
}) {
  const disabled = props.role !== "admin" || props.isUploading;
  const uploadFileList: UploadFile[] = props.file
    ? [
        {
          uid: props.file.name,
          name: props.file.name,
          status: "done",
        },
      ]
    : [];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <ProCard title="上传知识库" bordered>
          <Form layout="vertical">
            <Form.Item label="文件">
              <Upload.Dragger
                accept=".txt,.md,.pdf,.docx,.csv,.xlsx,.xls"
                multiple={false}
                maxCount={1}
                fileList={uploadFileList}
                beforeUpload={(file) => {
                  props.setFile(file);
                  return false;
                }}
                onRemove={() => props.setFile(null)}
              >
                <p className="uploadIcon">
                  <CloudUploadOutlined />
                </p>
                <p className="uploadTitle">点击或拖拽文件到此区域</p>
                <p className="uploadHint">支持 .txt / .md / .pdf / .docx / .csv / .xlsx / .xls</p>
              </Upload.Dragger>
            </Form.Item>
            <Form.Item label="可见范围">
              <Radio.Group
                optionType="button"
                buttonStyle="solid"
                value={props.visibility}
                onChange={(event) => props.setVisibility(event.target.value)}
                options={[
                  { label: "员工", value: "employee" },
                  { label: "管理员", value: "admin" },
                ]}
              />
            </Form.Item>
            <Form.Item label="部门">
              <Input value={props.department} onChange={(event) => props.setDepartment(event.target.value)} />
            </Form.Item>
            <Button
              type="primary"
              block
              icon={<CloudUploadOutlined />}
              disabled={disabled}
              loading={props.isUploading}
              onClick={props.uploadDocument}
            >
              上传到后端
            </Button>
          </Form>
        </ProCard>
      </Col>
      <Col xs={24} xl={14}>
        <ProCard title="入库流程" bordered>
          <div className="processList">
            {[
              "管理员上传文档",
              "LangChain Loader 解析原始文件",
              "LangChain Splitter 切分文档",
              "阿里百炼生成 embedding",
              "PGVector 写入向量库",
              "审计日志记录上传行为",
            ].map((item, index) => (
              <div className="processItem" key={item}>
                <Avatar size="small" style={{ backgroundColor: "#1677ff" }}>
                  {index + 1}
                </Avatar>
                <Text>{item}</Text>
              </div>
            ))}
          </div>
        </ProCard>
      </Col>
    </Row>
  );
}

function ApprovalsPanel({
  approvals,
  reviewApproval,
  role,
}: {
  approvals: Approval[];
  reviewApproval: (id: string, approved: boolean) => void;
  role: Role;
}) {
  return (
    <ProCard title="审批列表" bordered>
      <Table<Approval>
        rowKey="id"
        dataSource={approvals}
        locale={{ emptyText: <Empty description="暂无审批记录，发送退款请求后会产生审批" /> }}
        columns={[
          { title: "审批 ID", dataIndex: "id", ellipsis: true },
          { title: "订单", dataIndex: "orderNo", width: 140 },
          { title: "金额", dataIndex: "amount", width: 140 },
          { title: "状态", dataIndex: "status", width: 120, render: (value) => <StatusTag value={String(value)} /> },
          { title: "原因", dataIndex: "reason", ellipsis: true },
          { title: "时间", dataIndex: "createdAt", width: 150 },
          {
            title: "操作",
            width: 150,
            render: (_, item) => (
              <Space>
                <Button
                  size="small"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  disabled={role !== "admin" || item.status !== "pending"}
                  onClick={() => reviewApproval(item.id, true)}
                >
                  通过
                </Button>
                <Button
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  disabled={role !== "admin" || item.status !== "pending"}
                  onClick={() => reviewApproval(item.id, false)}
                >
                  拒绝
                </Button>
              </Space>
            ),
          },
        ]}
      />
    </ProCard>
  );
}

function RefundsPanel({ refunds }: { refunds: Refund[] }) {
  return (
    <ProCard title="退款流水" bordered>
      <Table<Refund>
        rowKey="id"
        dataSource={refunds}
        locale={{ emptyText: <Empty description="暂无退款流水" /> }}
        columns={[
          { title: "订单", dataIndex: "orderNo" },
          { title: "金额", dataIndex: "amount" },
          { title: "状态", dataIndex: "status", render: (value) => <StatusTag value={String(value)} /> },
          { title: "时间", dataIndex: "createdAt" },
          { title: "审批 ID", dataIndex: "approvalId", ellipsis: true },
        ]}
      />
    </ProCard>
  );
}

function AuditPanel({ logs }: { logs: AuditLog[] }) {
  return (
    <ProCard title="审计日志" bordered>
      <Table<AuditLog>
        rowKey="id"
        dataSource={logs}
        locale={{ emptyText: <Empty description="暂无审计日志" /> }}
        columns={[
          { title: "动作", dataIndex: "action" },
          { title: "资源", dataIndex: "resourceType" },
          { title: "操作者", dataIndex: "actor" },
          { title: "时间", dataIndex: "createdAt" },
          { title: "资源 ID", dataIndex: "resourceId", ellipsis: true },
        ]}
      />
    </ProCard>
  );
}

function ThreadsPanel({
  threadFilter,
  setThreadFilter,
  loadThreadMessages,
  messages,
  summary,
  stateText,
}: {
  threadFilter: string;
  setThreadFilter: (value: string) => void;
  loadThreadMessages: () => void;
  messages: ChatMessage[];
  summary: string;
  stateText: string;
}) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <ProCard title="查询会话" bordered>
          <Form layout="vertical">
            <Form.Item label="Thread ID">
              <Input value={threadFilter} onChange={(event) => setThreadFilter(event.target.value)} />
            </Form.Item>
            <Button type="primary" block icon={<SearchOutlined />} onClick={loadThreadMessages}>
              查询后端会话
            </Button>
          </Form>

          {summary ? (
            <Card size="small" title="会话摘要" className="contextCard">
              <Paragraph>{summary}</Paragraph>
            </Card>
          ) : null}

          {stateText ? (
            <Card size="small" title="业务状态" className="contextCard">
              <pre className="statePre">{stateText}</pre>
            </Card>
          ) : null}
        </ProCard>
      </Col>
      <Col xs={24} xl={15}>
        <ProCard title="消息记录" bordered>
          <MessageList messages={messages} />
        </ProCard>
      </Col>
    </Row>
  );
}

function MessageList({ messages }: { messages: ChatMessage[] }) {
  if (messages.length === 0) {
    return (
      <div className="chatEmptyState">
        <Empty description="暂无消息，开始一次客服对话" />
      </div>
    );
  }

  return (
    <div className="messageList">
      {messages.map((item) => (
        <div key={item.id} className={`messageRow ${item.role}`}>
          <div className={`messageBubble ${item.role}`}>
            <div className="messageHeader">
              <Space size={8}>
                <Tag color={roleColor(item.role)}>{roleLabelForMessage(item.role)}</Tag>
                {item.route ? <Tag color={routeColor(item.route)}>{labelForRoute(item.route)}</Tag> : null}
              </Space>
              <Text type="secondary">{item.createdAt}</Text>
            </div>
            <Paragraph className="messageContent">{item.content || "正在生成..."}</Paragraph>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusTag({ value }: { value: string }) {
  const colorMap: Record<string, string> = {
    pending: "gold",
    approved: "green",
    rejected: "red",
    succeeded: "green",
    failed: "red",
  };

  return <Tag color={colorMap[value] || "default"}>{labelForBadge(value)}</Tag>;
}

function readStoredRole(): Role {
  if (!localStorage.getItem("access_token")) {
    return "employee";
  }

  return localStorage.getItem("role") === "admin" ? "admin" : "employee";
}

function readRoleFromToken(token: string): Role {
  const [, payload] = token.split(".");

  if (!payload) {
    return "employee";
  }

  try {
    const decoded = JSON.parse(window.atob(toBase64(payload))) as { role?: unknown };
    return decoded.role === "admin" ? "admin" : "employee";
  } catch {
    return "employee";
  }
}

function toBase64(value: string) {
  return value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
}

function titleForView(view: View) {
  const found = navItems.find((item) => item.id === view);
  return found?.name ?? "概览";
}

function canRoleAccessView(role: Role, view: View) {
  const item = navItems.find((nav) => nav.id === view);
  return item ? item.roles.includes(role) : false;
}

function pageSubtitle(role: Role) {
  if (role === "admin") {
    return "RAG、LangGraph、Agent 和后台审批控制台";
  }

  return "客服对话与个人会话工作台";
}

function mapApproval(item: ApprovalItem): Approval {
  const payload = item.payload || {};
  const orderNo = String(payload.order_no || "待确认");
  const amount = moneyFromOrderResult(payload.order_result);

  return {
    id: item.id,
    threadId: item.thread_id,
    actionType: item.action_type,
    status: item.status,
    orderNo,
    amount,
    reason: String(payload.user_input || item.action_type),
    createdAt: formatDate(item.created_at),
  };
}

function mapRefund(item: RefundItem): Refund {
  return {
    id: item.id,
    approvalId: item.approval_id,
    orderNo: item.order_no,
    amount: formatCents(item.amount_cents),
    status: item.status,
    createdAt: formatDate(item.created_at),
  };
}

function mapAuditLog(item: AuditLogItem): AuditLog {
  const username = typeof item.metadata.username === "string" ? item.metadata.username : item.user_id || "-";

  return {
    id: item.id,
    action: item.action,
    resourceType: item.resource_type || "-",
    resourceId: item.resource_id || "-",
    actor: username,
    createdAt: formatDate(item.created_at),
  };
}

function mapThreadMessage(item: ThreadMessageItem): ChatMessage {
  const route = routeFromIntent(
    typeof item.metadata.intent === "string" ? item.metadata.intent : null,
    typeof item.metadata.risk_level === "string" ? item.metadata.risk_level : null,
  );

  return {
    id: item.id,
    threadId: item.thread_id,
    role: item.role,
    content: item.content,
    createdAt: formatDate(item.created_at),
    route,
  };
}

function moneyFromOrderResult(value: unknown) {
  if (typeof value === "object" && value !== null && "amount" in value) {
    return String((value as { amount?: unknown }).amount || "-");
  }

  return "-";
}

function formatCents(value: number) {
  return `${(value / 100).toFixed(2)}元`;
}

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function routeFromIntent(intent: string | null, riskLevel: string | null): ChatRoute | undefined {
  if (intent === "refund" || riskLevel === "high") {
    return "refund_workflow";
  }

  if (intent === "order") {
    return "order_agent";
  }

  if (intent === "policy" || intent === "agent") {
    return "knowledge_rag";
  }

  return undefined;
}

function labelForRoute(route: ChatRoute) {
  const labels: Record<ChatRoute, string> = {
    refund_workflow: "高风险退款审批",
    order_agent: "订单工具查询",
    knowledge_rag: "知识库问答",
  };

  return labels[route];
}

function routeColor(route: ChatRoute) {
  const colors: Record<ChatRoute, string> = {
    refund_workflow: "gold",
    order_agent: "blue",
    knowledge_rag: "green",
  };

  return colors[route];
}

function roleLabel(role: Role) {
  return role === "admin" ? "管理员" : "员工";
}

function roleLabelForMessage(role: ChatMessage["role"]) {
  const labels: Record<ChatMessage["role"], string> = {
    user: "用户",
    assistant: "助手",
    system: "系统",
    tool: "工具",
  };

  return labels[role];
}

function roleColor(role: ChatMessage["role"]) {
  const colors: Record<ChatMessage["role"], string> = {
    user: "blue",
    assistant: "green",
    system: "gold",
    tool: "purple",
  };

  return colors[role];
}

function labelForBadge(value: string) {
  const labels: Record<string, string> = {
    pending: "待审批",
    approved: "已通过",
    rejected: "已拒绝",
    succeeded: "成功",
    failed: "失败",
  };

  return labels[value] ?? value;
}

createRoot(document.getElementById("root")!).render(<App />);
