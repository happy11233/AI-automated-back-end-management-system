import { useEffect, useRef } from "react";
import type { Position } from "../api";
import type { Role, View } from "../workspace/types";
import { canUseApprovalCenter, canUseCustomerServiceInbox } from "../workspace/shared";
import {
  canUseBusinessActionLoop,
  canUsePlatformExecutionTasks,
  isAiWorkflowView,
  isAutomationView,
  isErpView,
} from "../workspace/appHelpers";

type Loader = () => Promise<unknown>;

export type WorkspaceLoaders = Record<
  | "sidebarThreads" | "chat" | "threads" | "dashboard" | "settings"
  | "desktopDownloads" | "files" | "approvals" | "refunds" | "audit"
  | "runs" | "analytics" | "evaluation" | "monitoring" | "workflows"
  | "automation" | "flows" | "drafts" | "businessLoop" | "executionTasks"
  | "notifications" | "feedback" | "customerInbox" | "connectors"
  | "mcpTools" | "executors" | "users" | "erp",
  Loader
>;

// The map is evaluated only on navigation or identity changes. Filters remain
// controlled by each page's explicit refresh action.
export function useWorkspaceLoading({ token, role, position, view, loaders }: {
  token: string;
  role: Role;
  position: Position | null;
  view: View;
  loaders: WorkspaceLoaders;
}) {
  const latest = useRef({ loaders, view });
  latest.current = { loaders, view };

  useEffect(() => {
    if (!token) return;
    if (latest.current.view !== "chat" && latest.current.view !== "threads") {
      void latest.current.loaders.sidebarThreads();
    }
  }, [token, role, position]);

  useEffect(() => {
    if (!token) return;
    const load = latest.current.loaders;
    const common: Partial<Record<View, Loader>> = {
      dashboard: load.dashboard,
      chat: load.chat,
      threads: load.threads,
      user_settings: load.settings,
      desktop_downloads: load.desktopDownloads,
      file_downloads: load.files,
      notifications: load.notifications,
      feedback_improvement: load.feedback,
      feedback_center: load.feedback,
      platform_draft_review: load.drafts,
    };
    const admin: Partial<Record<View, Loader>> = {
      run_records: load.runs,
      effect_analytics: load.analytics,
      evaluation_center: load.evaluation,
      monitoring_center: load.monitoring,
      automation_flows: load.flows,
      connectors: load.connectors,
      mcp_tools: load.mcpTools,
      platform_action_executors: load.executors,
      users: load.users,
      documents: load.users,
      refunds: load.refunds,
      audit: load.audit,
    };
    const loader = common[view] || (role === "admin" ? admin[view] : undefined);
    if (loader) void loader();
    else if (view === "approvals" && canUseApprovalCenter(role, position)) void load.approvals();
    else if (view === "customer_service_inbox" && canUseCustomerServiceInbox(role, position)) void load.customerInbox();
    else if (view === "business_action_loop" && canUseBusinessActionLoop(role, position)) void load.businessLoop();
    else if (view === "platform_execution_tasks" && canUsePlatformExecutionTasks(role, position)) void load.executionTasks();
    else if (isAiWorkflowView(view) || view === "ai_apps") void load.workflows();
    else if (isErpView(view)) void load.erp();
    else if (isAutomationView(view)) void load.automation();
  }, [token, role, position, view]);
}
