import { useEffect, useMemo, useState } from "react";
import {
  CloudUploadOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  SearchOutlined,
  StopOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import {
  Avatar,
  Button,
  Col,
  Collapse,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Radio,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Upload,
  message,
  type TableColumnsType,
  type UploadFile,
} from "antd";
import { ProCard } from "@ant-design/pro-components";
import { WorkspaceTabs } from "../components/WorkspaceCharts";
import {
  isAuthExpiredError,
  addRagTeamMember,
  createDocumentGrant,
  createRagTeam,
  listDocumentGrants,
  getDocumentAccess,
  removeRagTeamMember,
  revokeDocumentGrant,
  listRagDocuments,
  listRagTeamMembers,
  listRagTeams,
  updateDocumentAccess,
  updateRagTeam,
  type DocumentAccessItem,
  type DocumentGrantItem,
  type DocumentUploadAccessPayload,
  type Position,
  type RagDocumentAccessMode,
  type RagGrantAccessLevel,
  type RagGrantSubjectType,
  type RagMarketScope,
  type RagStoreScope,
  type RagTeamItem,
  type RagTeamMemberItem,
  type RagTeamMemberRole,
  type RagTeamStatus,
} from "../api";
import type {
  DocumentMarketScope,
  DocumentStoreScope,
  DocumentFieldScope,
  DocumentSensitivityLevel,
  Role,
  DocumentPositionScope,
  UserRecord,
  RagTeamFormState,
  RagTeamMemberFormState,
  DocumentAccessFormState,
  DocumentGrantFormState,
} from "../workspace/types";
import {
  Paragraph,
  Text,
  Title,
  isPosition,
  positionLabel,
  roleLabel,
  StatusTag,
  formatTime,
  positionConfigs,
  TextArea,
} from "../workspace/shared";

export const documentMarketScopeOptions: Array<{ label: string; value: DocumentMarketScope }> = [
  { label: "不限站点", value: "all" },
  { label: "美国站", value: "us" },
  { label: "德国站", value: "de" },
  { label: "日本站", value: "jp" },
];

export const documentStoreScopeOptions: Array<{ label: string; value: DocumentStoreScope }> = [
  { label: "不限店铺", value: "all" },
  { label: "US Store", value: "us_store" },
  { label: "DE Store", value: "de_store" },
  { label: "JP Store", value: "jp_store" },
];

export const documentFieldScopeOptions: Array<{ label: string; value: DocumentFieldScope }> = [
  { label: "不限字段", value: "all" },
  { label: "运营 Listing", value: "operations_listing" },
  { label: "运营库存", value: "operations_inventory" },
  { label: "运营销售", value: "operations_sales" },
  { label: "客服客户资料", value: "customer_profile" },
  { label: "客服物流", value: "customer_logistics" },
  { label: "客服售后", value: "customer_after_sales" },
  { label: "财务发票", value: "finance_invoice" },
  { label: "财务收付款", value: "finance_payment" },
  { label: "财务利润", value: "finance_profit" },
  { label: "财务工资", value: "finance_salary" },
];

export const documentSensitivityLevelOptions: Array<{ label: string; value: DocumentSensitivityLevel }> = [
  { label: "内部", value: "internal" },
  { label: "保密", value: "confidential" },
  { label: "受限", value: "restricted" },
];

export const ragTeamStatusLabels: Record<RagTeamStatus, string> = {
  active: "启用",
  paused: "暂停",
  archived: "归档",
};

export const ragTeamStatusColors: Record<RagTeamStatus, string> = {
  active: "green",
  paused: "gold",
  archived: "default",
};

export const ragTeamStatusOptions: Array<{ label: string; value: RagTeamStatus }> = [
  { label: "启用", value: "active" },
  { label: "暂停", value: "paused" },
  { label: "归档", value: "archived" },
];

export const ragTeamMemberRoleLabels: Record<RagTeamMemberRole, string> = {
  member: "成员",
  supervisor: "主管",
  auditor: "审计",
};

export const ragTeamMemberRoleOptions: Array<{ label: string; value: RagTeamMemberRole }> = [
  { label: "成员", value: "member" },
  { label: "主管", value: "supervisor" },
  { label: "审计", value: "auditor" },
];

export const ragDocumentAccessModeLabels: Record<RagDocumentAccessMode, string> = {
  open: "开放",
  owner_only: "仅归属人",
  team_only: "仅归属团队",
  explicit_grants: "显式授权",
  owner_and_grants: "归属与授权",
};

export const ragDocumentAccessModeOptions: Array<{ label: string; value: RagDocumentAccessMode }> = [
  { label: "开放", value: "open" },
  { label: "仅归属人", value: "owner_only" },
  { label: "仅归属团队", value: "team_only" },
  { label: "显式授权", value: "explicit_grants" },
  { label: "归属与授权", value: "owner_and_grants" },
];

export const ragGrantSubjectTypeOptions: Array<{ label: string; value: RagGrantSubjectType }> = [
  { label: "用户", value: "user" },
  { label: "团队", value: "team" },
];

export const ragGrantAccessLevelLabels: Record<RagGrantAccessLevel, string> = {
  read: "读取",
  manage: "管理",
};

export const ragGrantAccessLevelOptions: Array<{ label: string; value: RagGrantAccessLevel }> = [
  { label: "读取", value: "read" },
  { label: "管理", value: "manage" },
];

export function DocumentsPanel(props: {
  token: string;
  file: File | null;
  setFile: (value: File | null) => void;
  visibility: Role;
  setVisibility: (value: Role) => void;
  department: string;
  setDepartment: (value: string) => void;
  positionScope: DocumentPositionScope;
  setPositionScope: (value: DocumentPositionScope) => void;
  marketScope: DocumentMarketScope;
  setMarketScope: (value: DocumentMarketScope) => void;
  storeScope: DocumentStoreScope;
  setStoreScope: (value: DocumentStoreScope) => void;
  fieldScope: DocumentFieldScope;
  setFieldScope: (value: DocumentFieldScope) => void;
  sensitivityLevel: DocumentSensitivityLevel;
  setSensitivityLevel: (value: DocumentSensitivityLevel) => void;
  uploadDocument: (uploadAccess?: DocumentUploadAccessPayload) => Promise<void>;
  role: Role;
  users: UserRecord[];
  isUploading: boolean;
}) {
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const disabled = props.role !== "admin" || props.isUploading;
  const [teams, setTeams] = useState<RagTeamItem[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [members, setMembers] = useState<RagTeamMemberItem[]>([]);
  const [teamForm, setTeamForm] = useState<RagTeamFormState>(emptyRagTeamForm());
  const [memberForm, setMemberForm] = useState<RagTeamMemberFormState>({
    userId: "",
    memberRole: "member",
    expiresAt: "",
  });
  const [isLoadingTeams, setIsLoadingTeams] = useState(false);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [savingTeamKey, setSavingTeamKey] = useState("");
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [removingMemberKey, setRemovingMemberKey] = useState("");
  const [uploadAccessForm, setUploadAccessForm] = useState<DocumentAccessFormState>({
    accessMode: "open",
    ownerUserId: "",
    ownerTeamId: "",
  });
  const [uploadGrantForm, setUploadGrantForm] = useState<DocumentGrantFormState>({
    subjectType: "user",
    subjectId: "",
    accessLevel: "read",
    reason: "",
    expiresAt: "",
  });
  const [documents, setDocuments] = useState<DocumentAccessItem[]>([]);
  const [documentSearch, setDocumentSearch] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [documentAccess, setDocumentAccess] = useState<DocumentAccessItem | null>(null);
  const [isDocumentAuthDrawerOpen, setIsDocumentAuthDrawerOpen] = useState(false);
  const [documentAccessForm, setDocumentAccessForm] = useState<DocumentAccessFormState>({
    accessMode: "open",
    ownerUserId: "",
    ownerTeamId: "",
  });
  const [documentGrants, setDocumentGrants] = useState<DocumentGrantItem[]>([]);
  const [documentGrantForm, setDocumentGrantForm] = useState<DocumentGrantFormState>({
    subjectType: "user",
    subjectId: "",
    accessLevel: "read",
    reason: "",
    expiresAt: "",
  });
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isLoadingDocumentAccess, setIsLoadingDocumentAccess] = useState(false);
  const [isSavingDocumentAccess, setIsSavingDocumentAccess] = useState(false);
  const [isCreatingGrant, setIsCreatingGrant] = useState(false);
  const [revokingGrantId, setRevokingGrantId] = useState("");

  useEffect(() => {
    if (!props.token || props.role !== "admin") {
      setTeams([]);
      setMembers([]);
      setDocuments([]);
      setDocumentAccess(null);
      setDocumentGrants([]);
      setIsDocumentAuthDrawerOpen(false);
      return;
    }

    void refreshRagTeams({ silent: true });
    void refreshDocuments({ silent: true });
  }, [props.token, props.role]);

  const uploadFileList: UploadFile[] = props.file
    ? [
        {
          uid: props.file.name,
          name: props.file.name,
          status: "done",
        },
      ]
    : [];

  const userOptions = useMemo(
    () =>
      props.users.map((user) => ({
        label: userLabel(user),
        value: user.id,
      })),
    [props.users],
  );
  const activeTeamOptions = useMemo(
    () =>
      teams
        .filter((team) => team.status === "active")
        .map((team) => ({
          label: `${team.name} / ${team.team_key}`,
          value: team.id,
        })),
    [teams],
  );
  const ownerTeamOptions = useMemo(
    () =>
      teams
        .filter((team) => team.status !== "archived")
        .map((team) => ({
          label: `${team.name} / ${team.team_key}`,
          value: team.id,
        })),
    [teams],
  );
  const grantSubjectOptions = documentGrantForm.subjectType === "team" ? activeTeamOptions : userOptions;

  async function refreshRagTeams(options: { silent?: boolean; preferredTeamId?: string } = {}) {
    if (!props.token) {
      return;
    }

    setIsLoadingTeams(true);
    try {
      const result = await listRagTeams(props.token);
      setTeams(result.items);
      const nextTeam =
        result.items.find((item) => item.id === options.preferredTeamId) ||
        result.items.find((item) => item.id === selectedTeamId) ||
        result.items[0] ||
        null;

      if (nextTeam) {
        setSelectedTeamId(nextTeam.id);
        setTeamForm(teamFormFromItem(nextTeam));
        await refreshRagTeamMembers(nextTeam.id, { silent: true });
      } else {
        setSelectedTeamId("");
        setTeamForm(emptyRagTeamForm());
        setMembers([]);
      }

      if (!options.silent) {
        message.success("RAG 团队已刷新");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "RAG 团队加载失败");
    } finally {
      setIsLoadingTeams(false);
    }
  }

  async function refreshRagTeamMembers(teamId = selectedTeamId, options: { silent?: boolean } = {}) {
    if (!props.token || !teamId) {
      setMembers([]);
      return;
    }

    setIsLoadingMembers(true);
    try {
      const result = await listRagTeamMembers(props.token, teamId);
      setMembers(result.items);
      if (!options.silent) {
        message.success("团队成员已刷新");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "团队成员加载失败");
    } finally {
      setIsLoadingMembers(false);
    }
  }

  function selectTeam(team: RagTeamItem) {
    setSelectedTeamId(team.id);
    setTeamForm(teamFormFromItem(team));
    void refreshRagTeamMembers(team.id);
  }

  function startNewTeam() {
    setSelectedTeamId("");
    setTeamForm(emptyRagTeamForm());
    setMembers([]);
  }

  async function saveTeam() {
    if (!props.token) {
      message.warning("请先登录管理员账号");
      return;
    }
    if (!teamForm.name.trim()) {
      message.warning("团队名称不能为空");
      return;
    }
    if (!selectedTeamId && !teamForm.teamKey.trim()) {
      message.warning("团队 key 不能为空");
      return;
    }

    const basePayload = {
      name: teamForm.name.trim(),
      description: teamForm.description.trim() || null,
      position_scope: teamForm.positionScope === "all" ? null : teamForm.positionScope,
      market_scope: teamForm.marketScope === "all" ? null : (teamForm.marketScope as RagMarketScope),
      store_scope: teamForm.storeScope === "all" ? null : (teamForm.storeScope as RagStoreScope),
      status: teamForm.status,
    };

    setSavingTeamKey(selectedTeamId || "new");
    try {
      const result = selectedTeamId
        ? await updateRagTeam(props.token, selectedTeamId, basePayload)
        : await createRagTeam(props.token, {
            ...basePayload,
            team_key: teamForm.teamKey.trim().toLowerCase(),
          });
      setSelectedTeamId(result.item.id);
      setTeamForm(teamFormFromItem(result.item));
      await refreshRagTeams({ silent: true, preferredTeamId: result.item.id });
      message.success(selectedTeamId ? "RAG 团队已保存" : "RAG 团队已创建");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "RAG 团队保存失败");
    } finally {
      setSavingTeamKey("");
    }
  }

  async function addMember() {
    if (!props.token || !selectedTeamId) {
      message.warning("请选择 RAG 团队");
      return;
    }
    if (!memberForm.userId) {
      message.warning("请选择成员");
      return;
    }

    setIsAddingMember(true);
    try {
      await addRagTeamMember(props.token, selectedTeamId, {
        user_id: memberForm.userId,
        member_role: memberForm.memberRole,
        expires_at: optionalIsoText(memberForm.expiresAt),
      });
      setMemberForm((current) => ({ ...current, userId: "", expiresAt: "" }));
      await Promise.all([
        refreshRagTeamMembers(selectedTeamId, { silent: true }),
        refreshRagTeams({ silent: true, preferredTeamId: selectedTeamId }),
      ]);
      message.success("团队成员已添加");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "团队成员添加失败");
    } finally {
      setIsAddingMember(false);
    }
  }

  function removeMember(item: RagTeamMemberItem) {
    if (!props.token || !selectedTeamId) {
      return;
    }

    Modal.confirm({
      title: "移除团队成员",
      content: `确认移除“${item.display_name || item.username}”？`,
      okText: "移除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        setRemovingMemberKey(item.user_id);
        try {
          await removeRagTeamMember(props.token, selectedTeamId, item.user_id);
          await Promise.all([
            refreshRagTeamMembers(selectedTeamId, { silent: true }),
            refreshRagTeams({ silent: true, preferredTeamId: selectedTeamId }),
          ]);
          message.success("团队成员已移除");
        } catch (error) {
          if (isAuthExpiredError(error)) {
            return;
          }
          message.error(error instanceof Error ? error.message : "团队成员移除失败");
        } finally {
          setRemovingMemberKey("");
        }
      },
    });
  }

  async function uploadDocumentWithAccess() {
    if (uploadAccessForm.accessMode === "owner_only" && !uploadAccessForm.ownerUserId) {
      message.warning("仅归属人模式需要选择 owner 用户");
      return;
    }
    if (uploadAccessForm.accessMode === "team_only" && !uploadAccessForm.ownerTeamId) {
      message.warning("仅归属团队模式需要选择 owner 团队");
      return;
    }

    const uploadGrant = uploadGrantForm.subjectId
      ? {
          grant_subject_type: uploadGrantForm.subjectType,
          grant_subject_id: uploadGrantForm.subjectId,
          grant_access_level: uploadGrantForm.accessLevel,
          grant_reason: uploadGrantForm.reason.trim() || null,
          grant_expires_at: optionalIsoText(uploadGrantForm.expiresAt),
        }
      : {};

    await props.uploadDocument({
      access_mode: uploadAccessForm.accessMode,
      owner_user_id: uploadAccessForm.ownerUserId || null,
      owner_team_id: uploadAccessForm.ownerTeamId || null,
      ...uploadGrant,
    });
    await refreshDocuments({ silent: true });
  }

  async function refreshDocuments(options: { silent?: boolean } = {}) {
    if (!props.token) {
      setDocuments([]);
      return;
    }

    setIsLoadingDocuments(true);
    try {
      const result = await listRagDocuments(props.token, {
        search: documentSearch.trim() || undefined,
        status: "active",
        limit: 50,
      });
      setDocuments(result.items);
      if (!options.silent) {
        message.success("文档列表已刷新");
      }
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档列表加载失败");
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  function selectDocument(item: DocumentAccessItem, options: { openDrawer?: boolean } = {}) {
    setDocumentId(item.id);
    if (options.openDrawer) {
      setIsDocumentAuthDrawerOpen(true);
    }
    void loadDocumentAuthorization(item.id);
  }

  async function loadDocumentAuthorization(targetDocumentId = documentId) {
    const normalizedDocumentId = targetDocumentId.trim();
    if (!props.token) {
      message.warning("请先登录管理员账号");
      return;
    }
    if (!normalizedDocumentId) {
      message.warning("文档 ID 不能为空");
      return;
    }

    setIsLoadingDocumentAccess(true);
    try {
      const [accessResult, grantsResult] = await Promise.all([
        getDocumentAccess(props.token, normalizedDocumentId),
        listDocumentGrants(props.token, normalizedDocumentId),
      ]);
      setDocumentId(normalizedDocumentId);
      setDocumentAccess(accessResult.item);
      setDocuments((current) =>
        current.map((item) => (item.id === accessResult.item.id ? accessResult.item : item)),
      );
      setDocumentAccessForm({
        accessMode: accessResult.item.access_mode,
        ownerUserId: accessResult.item.owner_user_id || "",
        ownerTeamId: accessResult.item.owner_team_id || "",
      });
      setDocumentGrants(grantsResult.items);
      message.success("文档授权已加载");
    } catch (error) {
      setDocumentAccess(null);
      setDocumentGrants([]);
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档授权加载失败");
    } finally {
      setIsLoadingDocumentAccess(false);
    }
  }

  async function saveDocumentAccess() {
    if (!props.token || !documentAccess) {
      message.warning("请先加载文档");
      return;
    }
    if (documentAccessForm.accessMode === "owner_only" && !documentAccessForm.ownerUserId) {
      message.warning("仅归属人模式需要选择 owner 用户");
      return;
    }
    if (documentAccessForm.accessMode === "team_only" && !documentAccessForm.ownerTeamId) {
      message.warning("仅归属团队模式需要选择 owner 团队");
      return;
    }

    setIsSavingDocumentAccess(true);
    try {
      const result = await updateDocumentAccess(props.token, documentAccess.id, {
        access_mode: documentAccessForm.accessMode,
        owner_user_id: documentAccessForm.ownerUserId || null,
        owner_team_id: documentAccessForm.ownerTeamId || null,
      });
      setDocumentAccess(result.item);
      setDocuments((current) => current.map((item) => (item.id === result.item.id ? result.item : item)));
      setDocumentAccessForm({
        accessMode: result.item.access_mode,
        ownerUserId: result.item.owner_user_id || "",
        ownerTeamId: result.item.owner_team_id || "",
      });
      message.success("文档访问模式已保存");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档访问模式保存失败");
    } finally {
      setIsSavingDocumentAccess(false);
    }
  }

  async function createGrant() {
    if (!props.token || !documentAccess) {
      message.warning("请先加载文档");
      return;
    }
    if (!documentGrantForm.subjectId) {
      message.warning("请选择授权对象");
      return;
    }

    setIsCreatingGrant(true);
    try {
      await createDocumentGrant(props.token, documentAccess.id, {
        subject_type: documentGrantForm.subjectType,
        subject_id: documentGrantForm.subjectId,
        access_level: documentGrantForm.accessLevel,
        reason: documentGrantForm.reason.trim() || null,
        expires_at: optionalIsoText(documentGrantForm.expiresAt),
      });
      setDocumentGrantForm((current) => ({
        ...current,
        subjectId: "",
        reason: "",
        expiresAt: "",
      }));
      const result = await listDocumentGrants(props.token, documentAccess.id);
      setDocumentGrants(result.items);
      message.success("文档授权已添加");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档授权添加失败");
    } finally {
      setIsCreatingGrant(false);
    }
  }

  async function revokeGrant(item: DocumentGrantItem) {
    if (!props.token || !documentAccess) {
      return;
    }

    setRevokingGrantId(item.id);
    try {
      await revokeDocumentGrant(props.token, documentAccess.id, item.id);
      const result = await listDocumentGrants(props.token, documentAccess.id);
      setDocumentGrants(result.items);
      message.success("文档授权已撤销");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      message.error(error instanceof Error ? error.message : "文档授权撤销失败");
    } finally {
      setRevokingGrantId("");
    }
  }

  const teamColumns: TableColumnsType<RagTeamItem> = [
    {
      title: "团队",
      dataIndex: "name",
      width: 220,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.name}</Text>
          <Text type="secondary" copyable>
            {item.team_key}
          </Text>
        </Space>
      ),
    },
    {
      title: "范围",
      dataIndex: "position_scope",
      render: (_, item) => renderTeamScopeTags(item),
    },
    {
      title: "成员",
      dataIndex: "member_count",
      width: 80,
      render: (value) => <Tag color="blue">{Number(value || 0)}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (value) => renderRagTeamStatus(String(value) as RagTeamStatus),
    },
    {
      title: "操作",
      key: "actions",
      width: 92,
      render: (_, item) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => selectTeam(item)}>
          编辑
        </Button>
      ),
    },
  ];

  const memberColumns: TableColumnsType<RagTeamMemberItem> = [
    {
      title: "成员",
      dataIndex: "username",
      width: 220,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.display_name || item.username}</Text>
          <Text type="secondary">{item.username}</Text>
        </Space>
      ),
    },
    {
      title: "岗位",
      dataIndex: "position",
      width: 110,
      render: (value) => (value && isPosition(value) ? positionLabel(value) : roleLabel("admin")),
    },
    {
      title: "角色",
      dataIndex: "member_role",
      width: 90,
      render: (value) => (
        <Tag>{ragTeamMemberRoleLabels[String(value) as RagTeamMemberRole] || String(value)}</Tag>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (value) => <StatusTag value={String(value)} />,
    },
    {
      title: "过期时间",
      dataIndex: "expires_at",
      width: 140,
      render: (value) => formatTime(value ? String(value) : null),
    },
    {
      title: "操作",
      key: "actions",
      width: 92,
      render: (_, item) => (
        <Button
          danger
          size="small"
          icon={<DeleteOutlined />}
          disabled={item.status !== "active"}
          loading={removingMemberKey === item.user_id}
          onClick={() => removeMember(item)}
        >
          移除
        </Button>
      ),
    },
  ];

  const documentColumns: TableColumnsType<DocumentAccessItem> = [
    {
      title: "文档",
      dataIndex: "title",
      width: 300,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.title}</Text>
          <Text type="secondary">{item.source || "-"}</Text>
          <Text type="secondary" copyable>
            {item.id}
          </Text>
        </Space>
      ),
    },
    {
      title: "范围",
      key: "scope",
      width: 300,
      render: (_, item) => renderDocumentScopeTags(item),
    },
    {
      title: "访问",
      dataIndex: "access_mode",
      width: 118,
      render: (value) => (
        <Tag color="blue">
          {ragDocumentAccessModeLabels[String(value) as RagDocumentAccessMode] || String(value)}
        </Tag>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (value) => <StatusTag value={String(value)} />,
    },
    {
      title: "更新时间",
      dataIndex: "updated_at",
      width: 142,
      render: (value) => formatTime(value ? String(value) : null),
    },
    {
      title: "操作",
      key: "actions",
      width: 116,
      fixed: "right",
      render: (_, item) => (
        <Button
          size="small"
          icon={<SafetyCertificateOutlined />}
          loading={isLoadingDocumentAccess && documentId === item.id}
          onClick={() => selectDocument(item, { openDrawer: true })}
        >
          授权详情
        </Button>
      ),
    },
  ];

  const grantColumns: TableColumnsType<DocumentGrantItem> = [
    {
      title: "对象",
      dataIndex: "subject_name",
      width: 220,
      render: (_, item) => (
        <Space direction="vertical" size={2}>
          <Text strong>{item.subject_name || item.subject_id}</Text>
          <Text type="secondary">{item.subject_type === "team" ? "团队" : "用户"}</Text>
        </Space>
      ),
    },
    {
      title: "级别",
      dataIndex: "access_level",
      width: 90,
      render: (value) => (
        <Tag color={value === "manage" ? "purple" : "blue"}>
          {ragGrantAccessLevelLabels[String(value) as RagGrantAccessLevel] || String(value)}
        </Tag>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 88,
      render: (value) => <StatusTag value={String(value)} />,
    },
    {
      title: "原因",
      dataIndex: "reason",
      ellipsis: true,
      render: (value) => (value ? String(value) : "-"),
    },
    {
      title: "过期时间",
      dataIndex: "expires_at",
      width: 140,
      render: (value) => formatTime(value ? String(value) : null),
    },
    {
      title: "操作",
      key: "actions",
      width: 92,
      render: (_, item) => (
        <Popconfirm
          title="撤销文档授权"
          description={`确认撤销“${item.subject_name || item.subject_id}”的授权？`}
          okText="撤销"
          okButtonProps={{ danger: true, className: "documentGrantRevokeConfirmButton" }}
          cancelText="取消"
          disabled={item.status !== "active"}
          onConfirm={() => revokeGrant(item)}
        >
          <Button
            danger
            size="small"
            icon={<StopOutlined />}
            disabled={item.status !== "active"}
            loading={revokingGrantId === item.id}
          >
            撤销
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const documentAccessEditor = documentAccess ? (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Space direction="vertical" size={4}>
        <Text strong>{documentAccess.title}</Text>
        <Text type="secondary">{documentAccess.source || "-"}</Text>
        <Text type="secondary" copyable>
          {documentAccess.id}
        </Text>
      </Space>
      {renderDocumentScopeTags(documentAccess)}
      <Form layout="vertical">
        <Form.Item label="访问模式">
          <Select<RagDocumentAccessMode>
            value={documentAccessForm.accessMode}
            onChange={(value) => setDocumentAccessForm((current) => ({ ...current, accessMode: value }))}
            options={ragDocumentAccessModeOptions}
            virtual={false}
          />
        </Form.Item>
        <Form.Item label="owner 用户">
          <Select
            allowClear
            showSearch
            value={documentAccessForm.ownerUserId || undefined}
            onChange={(value) =>
              setDocumentAccessForm((current) => ({ ...current, ownerUserId: value || "" }))
            }
            options={userOptions}
            virtual={false}
            optionFilterProp="label"
          />
        </Form.Item>
        <Form.Item label="owner 团队">
          <Select
            allowClear
            showSearch
            value={documentAccessForm.ownerTeamId || undefined}
            onChange={(value) =>
              setDocumentAccessForm((current) => ({ ...current, ownerTeamId: value || "" }))
            }
            options={ownerTeamOptions}
            virtual={false}
            optionFilterProp="label"
          />
        </Form.Item>
        <Button
          type="primary"
          block
          icon={<SaveOutlined />}
          loading={isSavingDocumentAccess}
          onClick={saveDocumentAccess}
        >
          保存访问模式
        </Button>
      </Form>
    </Space>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档授权数据" />
  );

  const documentGrantEditor = documentAccess ? (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Row gutter={[12, 12]} align="bottom">
        <Col xs={24} md={5}>
          <Form.Item label="对象类型">
            <Select<RagGrantSubjectType>
              value={documentGrantForm.subjectType}
              onChange={(value) =>
                setDocumentGrantForm((current) => ({
                  ...current,
                  subjectType: value,
                  subjectId: "",
                }))
              }
              options={ragGrantSubjectTypeOptions}
              virtual={false}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={7}>
          <Form.Item label="授权对象">
            <Select
              showSearch
              value={documentGrantForm.subjectId || undefined}
              onChange={(value) => setDocumentGrantForm((current) => ({ ...current, subjectId: value }))}
              options={grantSubjectOptions}
              virtual={false}
              optionFilterProp="label"
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={4}>
          <Form.Item label="授权级别">
            <Select<RagGrantAccessLevel>
              value={documentGrantForm.accessLevel}
              onChange={(value) => setDocumentGrantForm((current) => ({ ...current, accessLevel: value }))}
              options={ragGrantAccessLevelOptions}
              virtual={false}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={4}>
          <Form.Item label="过期时间">
            <Input
              value={documentGrantForm.expiresAt}
              onChange={(event) =>
                setDocumentGrantForm((current) => ({ ...current, expiresAt: event.target.value }))
              }
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={4}>
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
            loading={isCreatingGrant}
            onClick={createGrant}
          >
            添加授权
          </Button>
        </Col>
        <Col xs={24}>
          <Form.Item label="授权原因">
            <Input
              value={documentGrantForm.reason}
              onChange={(event) =>
                setDocumentGrantForm((current) => ({ ...current, reason: event.target.value }))
              }
            />
          </Form.Item>
        </Col>
      </Row>
      <Table<DocumentGrantItem>
        rowKey="id"
        size="small"
        columns={grantColumns}
        dataSource={documentGrants}
        loading={isLoadingDocumentAccess}
        pagination={{ pageSize: 6 }}
        scroll={{ x: 860 }}
      />
    </Space>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档授权数据" />
  );

  const documentAuthorizationDrawerContent = documentAccess ? (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <ProCard title="访问模式" bordered className="splitCard">
        {documentAccessEditor}
      </ProCard>
      <ProCard title="显式授权" bordered className="splitCard">
        {documentGrantEditor}
      </ProCard>
    </Space>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档授权数据" />
  );

  const uploadPanel = (
    <Space direction="vertical" className="pageStack">
      <ProCard title="上传知识库" bordered className="splitCard">
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
          <Form.Item label="岗位范围">
            <Select<DocumentPositionScope>
              value={props.positionScope}
              onChange={props.setPositionScope}
              virtual={false}
              options={[
                { label: "不限岗位", value: "all" },
                ...(Object.keys(positionConfigs) as Position[]).map((item) => ({
                  label: `${positionConfigs[item].label}专属`,
                  value: item,
                })),
              ]}
            />
          </Form.Item>
          <Form.Item label="站点范围">
            <Select<DocumentMarketScope>
              value={props.marketScope}
              onChange={props.setMarketScope}
              virtual={false}
              options={documentMarketScopeOptions}
            />
          </Form.Item>
          <Form.Item label="店铺范围">
            <Select<DocumentStoreScope>
              value={props.storeScope}
              onChange={props.setStoreScope}
              virtual={false}
              options={documentStoreScopeOptions}
            />
          </Form.Item>
          <Form.Item label="字段分类">
            <Select<DocumentFieldScope>
              value={props.fieldScope}
              onChange={props.setFieldScope}
              virtual={false}
              options={documentFieldScopeOptions}
            />
          </Form.Item>
          <Form.Item label="敏感级别">
            <Select<DocumentSensitivityLevel>
              value={props.sensitivityLevel}
              onChange={props.setSensitivityLevel}
              virtual={false}
              options={documentSensitivityLevelOptions}
            />
          </Form.Item>
          <Collapse
            ghost
            className="workspaceAdvancedFilters"
            items={[
              {
                key: "access",
                label: "高级访问控制与初始授权",
                children: (
                  <>
                    <Form.Item label="上传访问模式">
                      <Select<RagDocumentAccessMode>
                        value={uploadAccessForm.accessMode}
                        onChange={(value) =>
                          setUploadAccessForm((current) => ({ ...current, accessMode: value }))
                        }
                        virtual={false}
                        options={ragDocumentAccessModeOptions}
                      />
                    </Form.Item>
                    <Form.Item label="上传 owner 用户">
                      <Select
                        allowClear
                        showSearch
                        value={uploadAccessForm.ownerUserId || undefined}
                        onChange={(value) =>
                          setUploadAccessForm((current) => ({ ...current, ownerUserId: value || "" }))
                        }
                        options={userOptions}
                        virtual={false}
                        optionFilterProp="label"
                      />
                    </Form.Item>
                    <Form.Item label="上传 owner 团队">
                      <Select
                        allowClear
                        showSearch
                        value={uploadAccessForm.ownerTeamId || undefined}
                        onChange={(value) =>
                          setUploadAccessForm((current) => ({ ...current, ownerTeamId: value || "" }))
                        }
                        options={ownerTeamOptions}
                        virtual={false}
                        optionFilterProp="label"
                      />
                    </Form.Item>
                    <Form.Item label="初始授权对象类型">
                      <Select<RagGrantSubjectType>
                        value={uploadGrantForm.subjectType}
                        onChange={(value) =>
                          setUploadGrantForm((current) => ({
                            ...current,
                            subjectType: value,
                            subjectId: "",
                          }))
                        }
                        options={ragGrantSubjectTypeOptions}
                        virtual={false}
                      />
                    </Form.Item>
                    <Form.Item label="初始授权对象">
                      <Select
                        allowClear
                        showSearch
                        value={uploadGrantForm.subjectId || undefined}
                        onChange={(value) =>
                          setUploadGrantForm((current) => ({ ...current, subjectId: value || "" }))
                        }
                        options={uploadGrantForm.subjectType === "team" ? activeTeamOptions : userOptions}
                        virtual={false}
                        optionFilterProp="label"
                      />
                    </Form.Item>
                    <Form.Item label="初始授权级别">
                      <Select<RagGrantAccessLevel>
                        value={uploadGrantForm.accessLevel}
                        onChange={(value) =>
                          setUploadGrantForm((current) => ({ ...current, accessLevel: value }))
                        }
                        options={ragGrantAccessLevelOptions}
                        virtual={false}
                      />
                    </Form.Item>
                    <Form.Item label="初始授权过期时间">
                      <Input
                        value={uploadGrantForm.expiresAt}
                        onChange={(event) =>
                          setUploadGrantForm((current) => ({ ...current, expiresAt: event.target.value }))
                        }
                      />
                    </Form.Item>
                    <Form.Item label="初始授权原因">
                      <Input
                        value={uploadGrantForm.reason}
                        onChange={(event) =>
                          setUploadGrantForm((current) => ({ ...current, reason: event.target.value }))
                        }
                      />
                    </Form.Item>
                  </>
                ),
              },
            ]}
          />
          <Button
            type="primary"
            block
            icon={<CloudUploadOutlined />}
            disabled={disabled}
            loading={props.isUploading}
            onClick={uploadDocumentWithAccess}
          >
            上传到后端
          </Button>
        </Form>
      </ProCard>
      <Collapse
        ghost
        items={[
          {
            key: "pipeline",
            label: "查看文档处理流程",
            children: (
              <ProCard title="入库流程" bordered className="splitCard">
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
            ),
          },
        ]}
      />
    </Space>
  );

  const teamsPanel = (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={8} className="splitCardCol">
        <ProCard
          title={selectedTeamId ? "编辑团队" : "创建团队"}
          bordered
          className="splitCard"
          extra={
            <Space>
              <Tooltip title="刷新团队">
                <Button
                  icon={<ReloadOutlined />}
                  loading={isLoadingTeams}
                  onClick={() => refreshRagTeams()}
                />
              </Tooltip>
              <Tooltip title="新建团队">
                <Button icon={<PlusOutlined />} onClick={startNewTeam} />
              </Tooltip>
            </Space>
          }
        >
          <Form layout="vertical">
            <Form.Item label="团队 key">
              <Input
                value={teamForm.teamKey}
                disabled={Boolean(selectedTeamId)}
                onChange={(event) => setTeamForm((current) => ({ ...current, teamKey: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="团队名称">
              <Input
                value={teamForm.name}
                onChange={(event) => setTeamForm((current) => ({ ...current, name: event.target.value }))}
              />
            </Form.Item>
            <Form.Item label="描述">
              <TextArea
                rows={3}
                value={teamForm.description}
                onChange={(event) =>
                  setTeamForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </Form.Item>
            <Form.Item label="岗位范围">
              <Select<DocumentPositionScope>
                value={teamForm.positionScope}
                onChange={(value) => setTeamForm((current) => ({ ...current, positionScope: value }))}
                virtual={false}
                options={[
                  { label: "不限岗位", value: "all" },
                  ...(Object.keys(positionConfigs) as Position[]).map((item) => ({
                    label: `${positionConfigs[item].label}专属`,
                    value: item,
                  })),
                ]}
              />
            </Form.Item>
            <Form.Item label="站点范围">
              <Select<DocumentMarketScope>
                value={teamForm.marketScope}
                onChange={(value) => setTeamForm((current) => ({ ...current, marketScope: value }))}
                virtual={false}
                options={documentMarketScopeOptions}
              />
            </Form.Item>
            <Form.Item label="店铺范围">
              <Select<DocumentStoreScope>
                value={teamForm.storeScope}
                onChange={(value) => setTeamForm((current) => ({ ...current, storeScope: value }))}
                virtual={false}
                options={documentStoreScopeOptions}
              />
            </Form.Item>
            <Form.Item label="状态">
              <Select<RagTeamStatus>
                value={teamForm.status}
                onChange={(value) => setTeamForm((current) => ({ ...current, status: value }))}
                virtual={false}
                options={ragTeamStatusOptions}
              />
            </Form.Item>
            <Button
              type="primary"
              block
              icon={<SaveOutlined />}
              loading={savingTeamKey === (selectedTeamId || "new")}
              onClick={saveTeam}
            >
              {selectedTeamId ? "保存团队" : "创建团队"}
            </Button>
          </Form>
        </ProCard>
      </Col>
      <Col xs={24} xl={16} className="splitCardCol">
        <ProCard title="团队列表" bordered className="splitCard">
          <Table<RagTeamItem>
            rowKey="id"
            size="small"
            columns={teamColumns}
            dataSource={teams}
            loading={isLoadingTeams}
            pagination={{ pageSize: 6 }}
            scroll={{ x: 760 }}
          />
        </ProCard>
      </Col>
      <Col xs={24} className="splitCardCol">
        <ProCard
          title={
            selectedTeamId
              ? `团队成员：${teams.find((item) => item.id === selectedTeamId)?.name || ""}`
              : "团队成员"
          }
          bordered
          className="splitCard"
          extra={
            <Tooltip title="刷新成员">
              <Button
                icon={<ReloadOutlined />}
                disabled={!selectedTeamId}
                loading={isLoadingMembers}
                onClick={() => refreshRagTeamMembers()}
              />
            </Tooltip>
          }
        >
          <Row gutter={[12, 12]} align="bottom">
            <Col xs={24} md={8}>
              <Form.Item label="成员">
                <Select
                  showSearch
                  value={memberForm.userId || undefined}
                  onChange={(value) => setMemberForm((current) => ({ ...current, userId: value }))}
                  options={userOptions}
                  virtual={false}
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={5}>
              <Form.Item label="成员角色">
                <Select<RagTeamMemberRole>
                  value={memberForm.memberRole}
                  onChange={(value) => setMemberForm((current) => ({ ...current, memberRole: value }))}
                  options={ragTeamMemberRoleOptions}
                  virtual={false}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={7}>
              <Form.Item label="过期时间">
                <Input
                  value={memberForm.expiresAt}
                  onChange={(event) =>
                    setMemberForm((current) => ({ ...current, expiresAt: event.target.value }))
                  }
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={4}>
              <Button
                type="primary"
                block
                icon={<UserAddOutlined />}
                disabled={!selectedTeamId}
                loading={isAddingMember}
                onClick={addMember}
              >
                添加成员
              </Button>
            </Col>
          </Row>
          <Table<RagTeamMemberItem>
            rowKey="id"
            size="small"
            columns={memberColumns}
            dataSource={members}
            loading={isLoadingMembers}
            pagination={{ pageSize: 6 }}
            scroll={{ x: 820 }}
          />
        </ProCard>
      </Col>
    </Row>
  );

  const documentAccessPanel = (
    <ProCard title="按文档 ID 管理授权" subTitle="也可以在文档列表中点击授权详情" bordered>
      <div className="workspaceFilterBar">
        <Input
          aria-label="文档 ID"
          placeholder="输入文档 ID"
          value={documentId}
          onChange={(event) => setDocumentId(event.target.value)}
          onPressEnter={() => {
            setIsDocumentAuthDrawerOpen(true);
            void loadDocumentAuthorization();
          }}
        />
        <Button
          type="primary"
          loading={isLoadingDocumentAccess}
          onClick={() => {
            setIsDocumentAuthDrawerOpen(true);
            void loadDocumentAuthorization();
          }}
        >
          加载文档
        </Button>
      </div>
    </ProCard>
  );

  return (
    <>
      <WorkspaceTabs
        storageKey="knowledge_tab"
        items={[
          {
            key: "documents",
            label: "文档列表",
            children: (
              <ProCard
                title="文档列表"
                bordered
                className="splitCard"
                extra={
                  <Space>
                    <Button
                      type="primary"
                      icon={<CloudUploadOutlined />}
                      onClick={() => setIsUploadOpen(true)}
                    >
                      上传文档
                    </Button>
                    <Tooltip title="刷新文档">
                      <Button
                        icon={<ReloadOutlined />}
                        loading={isLoadingDocuments}
                        onClick={() => refreshDocuments()}
                      />
                    </Tooltip>
                  </Space>
                }
              >
                <Form layout="vertical">
                  <Row gutter={[12, 12]} align="bottom">
                    <Col xs={24} md={16}>
                      <Form.Item label="搜索文档">
                        <Input
                          value={documentSearch}
                          placeholder="标题、来源或文档 ID"
                          onChange={(event) => setDocumentSearch(event.target.value)}
                          onPressEnter={() => refreshDocuments()}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={8}>
                      <Button
                        type="primary"
                        block
                        icon={<SearchOutlined />}
                        loading={isLoadingDocuments}
                        onClick={() => refreshDocuments()}
                      >
                        搜索
                      </Button>
                    </Col>
                  </Row>
                </Form>
                <Table<DocumentAccessItem>
                  rowKey="id"
                  size="small"
                  columns={documentColumns}
                  dataSource={documents}
                  loading={isLoadingDocuments}
                  locale={{
                    emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可选文档" />,
                  }}
                  pagination={{ pageSize: 8, showSizeChanger: false }}
                  scroll={{ x: 1034 }}
                />
              </ProCard>
            ),
          },
          { key: "teams", label: "团队管理", children: teamsPanel },
          { key: "authorization", label: "文档授权", children: documentAccessPanel },
        ]}
      />
      <Drawer
        title="上传知识库"
        open={isUploadOpen}
        width="min(760px, 100vw)"
        onClose={() => setIsUploadOpen(false)}
        rootClassName="workspaceUploadDrawer"
      >
        <div className="workspaceLayout">{uploadPanel}</div>
      </Drawer>
      <Drawer
        title="文档授权详情"
        open={isDocumentAuthDrawerOpen}
        rootClassName="documentAuthorizationDrawer"
        width="min(760px, 100vw)"
        onClose={() => setIsDocumentAuthDrawerOpen(false)}
      >
        {isLoadingDocumentAccess && !documentAccess ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="正在加载文档授权" />
        ) : (
          documentAuthorizationDrawerContent
        )}
      </Drawer>
    </>
  );
}

export function emptyRagTeamForm(): RagTeamFormState {
  return {
    teamKey: "",
    name: "",
    description: "",
    positionScope: "all",
    marketScope: "all",
    storeScope: "all",
    status: "active",
  };
}

export function teamFormFromItem(item: RagTeamItem): RagTeamFormState {
  return {
    teamKey: item.team_key,
    name: item.name,
    description: item.description || "",
    positionScope: item.position_scope || "all",
    marketScope: item.market_scope || "all",
    storeScope: item.store_scope || "all",
    status: item.status,
  };
}

export function optionalIsoText(value: string) {
  const normalized = value.trim();
  return normalized || null;
}

export function userLabel(user: UserRecord) {
  const name = user.displayName || user.username;
  const scope = user.position ? positionLabel(user.position) : roleLabel(user.role);
  return `${name} / ${scope} / ${user.username}`;
}

export function labelFromOptions<T extends string>(
  options: Array<{ label: string; value: T }>,
  value: T,
) {
  return options.find((item) => item.value === value)?.label || value;
}

export function renderRagTeamStatus(value: RagTeamStatus) {
  return <Tag color={ragTeamStatusColors[value] || "default"}>{ragTeamStatusLabels[value] || value}</Tag>;
}

export function renderTeamScopeTags(item: RagTeamItem) {
  return (
    <Space size={[4, 4]} wrap>
      <Tag>{item.position_scope ? `${positionLabel(item.position_scope)}专属` : "不限岗位"}</Tag>
      <Tag>{labelFromOptions(documentMarketScopeOptions, item.market_scope || "all")}</Tag>
      <Tag>{labelFromOptions(documentStoreScopeOptions, item.store_scope || "all")}</Tag>
    </Space>
  );
}

export function renderDocumentScopeTags(item: DocumentAccessItem) {
  return (
    <Space size={[4, 4]} wrap>
      <Tag>{item.visibility === "employee" ? "员工可见" : "管理员可见"}</Tag>
      <Tag>{item.position_scope ? `${positionLabel(item.position_scope)}专属` : "不限岗位"}</Tag>
      <Tag>{labelFromOptions(documentMarketScopeOptions, item.market_scope || "all")}</Tag>
      <Tag>{labelFromOptions(documentStoreScopeOptions, item.store_scope || "all")}</Tag>
      <Tag>{labelFromOptions(documentFieldScopeOptions, (item.field_scope || "all") as DocumentFieldScope)}</Tag>
      <Tag color={item.sensitivity_level === "restricted" ? "red" : "blue"}>
        {labelFromOptions(documentSensitivityLevelOptions, (item.sensitivity_level || "internal") as DocumentSensitivityLevel)}
      </Tag>
    </Space>
  );
}
