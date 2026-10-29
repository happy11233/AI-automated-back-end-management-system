import type { AiWorkflowItem, Position } from "../api";
import type {
  View,
  FinanceAutomationTool,
  AiWorkflowFilterState,
  Role,
  ChatRoute,
  ChatMessage,
} from "./types";
import { workflowIdViewMap } from "./shared";
import { automationTaskViewMap } from "./shared";

export const automationTaskIdViewMap: Record<string, View> = {
  operations: "automation_operations",
  "operations:listing": "automation_operations_listing",
  "operations:title": "automation_operations_title",
  "operations:bullets": "automation_operations_bullets",
  "operations:keywords": "automation_operations_keywords",
  "operations:promo_copy": "automation_operations_promo_copy",
  "operations:competitor_analysis": "automation_operations_competitor_analysis",
  customer_service: "automation_customer_service",
  "customer_service:smart_reply": "automation_customer_service_smart_reply",
  "customer_service:auto_reply": "automation_customer_service_auto_reply",
  "customer_service:refund_script": "automation_customer_service_refund_script",
  "customer_service:multilingual_translation": "automation_customer_service_multilingual_translation",
  finance: "automation_finance",
  "finance:report_analysis": "automation_finance_report_analysis",
  "finance:salary_summary": "automation_finance_salary_summary",
  "finance:excel_transform": "automation_finance_excel_transform",
};

export const automationFinanceToolViewMap: Partial<Record<View, FinanceAutomationTool>> = {
  automation_finance_report_analysis: "report_analysis",
  automation_finance_salary_summary: "salary_export",
  automation_finance_excel_transform: "excel_upload",
  automation_finance_excel_upload: "excel_upload",
  automation_finance_reconciliation: "reconciliation",
};

export function filterAiWorkflows(items: AiWorkflowItem[], filters: AiWorkflowFilterState) {
  return items.filter((item) => {
    if (filters.position !== "all" && item.position !== filters.position) {
      return false;
    }

    if (filters.category && item.category !== filters.category) {
      return false;
    }

    return true;
  });
}

export function groupAiWorkflows(items: AiWorkflowItem[]) {
  const groups = new Map<string, { key: string; label: string; items: AiWorkflowItem[] }>();

  items.forEach((item) => {
    const key = `${item.position}-${item.category}`;
    const label = `${item.position_label} / ${item.category}`;
    const group = groups.get(key) || { key, label, items: [] };
    group.items.push(item);
    groups.set(key, group);
  });

  return Array.from(groups.values());
}

export function workflowEntryView(value: string): View {
  if (value === "customer_service_inbox") {
    return "customer_service_inbox";
  }

  if (value === "automation_customer_service") {
    return "automation_customer_service";
  }

  if (value === "automation_finance") {
    return "automation_finance";
  }

  if (value === "automation_operations") {
    return "automation_operations";
  }

  return "ai_workflows";
}

export function workflowEntryViewForWorkflow(workflow: AiWorkflowItem): View {
  return workflowIdViewMap[workflow.id] || "ai_workflows";
}

export function workflowAutomationLevelLabel(value: string) {
  const labels: Record<string, string> = {
    draft_auto: "草稿自动化",
    assist_auto: "辅助自动化",
    tool_auto: "工具自动化",
    case_loop_auto: "闭环自动化",
  };

  return labels[value] ?? value;
}

export function automationTaskIdFromView(view: View) {
  return automationTaskViewMap[view] || null;
}

export function automationFinanceToolFromView(view: View): FinanceAutomationTool | null {
  return automationFinanceToolViewMap[view] || null;
}

export function automationPositionFromView(
  view: View,
  role: Role,
  position: Position | null,
): Position | null {
  if (role !== "admin") {
    return position;
  }

  if (view === "automation_customer_service" || view.startsWith("automation_customer_service_")) {
    return "customer_service";
  }

  if (view === "automation_finance" || view.startsWith("automation_finance_")) {
    return "finance";
  }

  return "operations";
}

export function routeColor(route: ChatRoute) {
  const colors: Record<ChatRoute, string> = {
    refund_workflow: "gold",
    order_agent: "blue",
    knowledge_rag: "green",
    finance_compound_report_generation: "magenta",
    finance_salary_export: "purple",
    enterprise_wechat_file_send: "cyan",
  };

  return colors[route];
}

export function roleColor(role: ChatMessage["role"]) {
  const colors: Record<ChatMessage["role"], string> = {
    user: "blue",
    assistant: "green",
    system: "gold",
    tool: "purple",
  };

  return colors[role];
}
