import { hasAdminAccess } from "../workspace/appHelpers";
import { useState } from "react";
import { message } from "antd";
import {
  getEffectAnalytics,
  getEvaluationCenter,
  getMonitoringCenter,
  isAuthExpiredError,
  listRunRecords,
  getRunRecordDetail,
  runRagEvaluation,
  type EffectAnalyticsResponse,
  type EvaluationCenterResponse,
  type MonitoringCenterResponse,
  type RunRecordDetailResponse,
  type RunRecordFilters,
  type RunRecordItem,
} from "../api";
import type { RunRecordFilterState, EffectAnalyticsFilterState, MonitoringCenterFilterState } from "../workspace/types";
import type { Role } from "../workspace/types";

export function useExecutionInsights({ token, role, setStatusMessage }: { token: string; role: Role; setStatusMessage: (value: string) => void }) {
  const [runRecords, setRunRecords] = useState<RunRecordItem[]>([]);

  const [runRecordFilters, setRunRecordFilters] = useState<RunRecordFilterState>({
    status: "all",
    runType: "",
    appId: "",
    position: "all",
    resourceType: "",
    resourceId: "",
    flowKey: "",
  });

  const [runRecordDetail, setRunRecordDetail] = useState<RunRecordDetailResponse | null>(null);

  const [isRunRecordDetailOpen, setIsRunRecordDetailOpen] = useState(false);

  const [isRunRecordDetailLoading, setIsRunRecordDetailLoading] = useState(false);

  const [isRunRecordsLoading, setIsRunRecordsLoading] = useState(false);

  const [effectAnalytics, setEffectAnalytics] = useState<EffectAnalyticsResponse | null>(null);

  const [effectAnalyticsFilters, setEffectAnalyticsFilters] = useState<EffectAnalyticsFilterState>({
    dateRange: "30d",
    position: "all",
  });

  const [isEffectAnalyticsLoading, setIsEffectAnalyticsLoading] = useState(false);

  const [evaluationCenter, setEvaluationCenter] = useState<EvaluationCenterResponse | null>(null);

  const [isEvaluationCenterLoading, setIsEvaluationCenterLoading] = useState(false);

  const [runningEvaluationId, setRunningEvaluationId] = useState("");

  const [monitoringCenter, setMonitoringCenter] = useState<MonitoringCenterResponse | null>(null);

  const [monitoringCenterFilters, setMonitoringCenterFilters] = useState<MonitoringCenterFilterState>({
    dateRange: "30d",
  });

  const [isMonitoringCenterLoading, setIsMonitoringCenterLoading] = useState(false);

  function runRecordFilterPayload(filters = runRecordFilters): RunRecordFilters {
    return {
      status: filters.status === "all" ? undefined : filters.status,
      run_type: filters.runType.trim() || undefined,
      app_id: filters.appId.trim() || undefined,
      position: filters.position,
      resource_type: filters.resourceType.trim() || undefined,
      resource_id: filters.resourceId.trim() || undefined,
      flow_key: filters.flowKey.trim() || undefined,
      limit: 80,
    };
  }

  async function refreshRunRecords(activeToken = token, filters = runRecordFilters) {
    if (!activeToken || !hasAdminAccess(role, activeToken)) {
      setRunRecords([]);
      setIsRunRecordsLoading(false);
      return;
    }

    setIsRunRecordsLoading(true);

    try {
      const result = await listRunRecords(activeToken, runRecordFilterPayload(filters));
      setRunRecords(result.items);
      setStatusMessage("运行记录已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "运行记录加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsRunRecordsLoading(false);
    }
  }

  async function openRunRecordDetail(runId: string) {
    if (!token || !hasAdminAccess(role, token)) {
      const text = token ? "只有管理员可以查看运行记录详情" : "请先登录";
      setStatusMessage(text);
      message.warning(text);
      return;
    }

    setIsRunRecordDetailOpen(true);
    setIsRunRecordDetailLoading(true);
    setRunRecordDetail(null);

    try {
      setRunRecordDetail(await getRunRecordDetail(token, runId));
      setStatusMessage("运行记录详情已加载");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "运行记录详情加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsRunRecordDetailLoading(false);
    }
  }

  function effectAnalyticsPayload(filters = effectAnalyticsFilters) {
    return {
      date_range: filters.dateRange,
      position: filters.position,
    };
  }

  async function refreshEffectAnalytics(activeToken = token, filters = effectAnalyticsFilters) {
    if (!activeToken || !hasAdminAccess(role, activeToken)) {
      setEffectAnalytics(null);
      setIsEffectAnalyticsLoading(false);
      return;
    }

    setIsEffectAnalyticsLoading(true);

    try {
      const result = await getEffectAnalytics(activeToken, effectAnalyticsPayload(filters));
      setEffectAnalytics(result);
      setStatusMessage("效果分析已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "效果分析加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsEffectAnalyticsLoading(false);
    }
  }

  async function refreshEvaluationCenter(activeToken = token) {
    if (!activeToken) {
      return;
    }

    setIsEvaluationCenterLoading(true);

    try {
      const result = await getEvaluationCenter(activeToken);
      setEvaluationCenter(result);
      setStatusMessage("AI 评测中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "AI 评测中心加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsEvaluationCenterLoading(false);
    }
  }

  async function refreshMonitoringCenter(activeToken = token, filters = monitoringCenterFilters) {
    if (!activeToken) {
      return;
    }

    setIsMonitoringCenterLoading(true);

    try {
      const result = await getMonitoringCenter(activeToken, {
        date_range: filters.dateRange,
      });
      setMonitoringCenter(result);
      setStatusMessage("监控中心已刷新");
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "监控中心加载失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setIsMonitoringCenterLoading(false);
    }
  }

  async function runEvaluation(datasetId: string) {
    if (!token) {
      setStatusMessage("请先登录管理员账号");
      message.warning("请先登录管理员账号");
      return;
    }

    setRunningEvaluationId(datasetId);

    try {
      const result = await runRagEvaluation(token, datasetId, 5);
      setStatusMessage(`评测完成：${result.report.dataset_name}`);
      message.success("RAG 评测已完成");
      await refreshEvaluationCenter(token);
    } catch (error) {
      if (isAuthExpiredError(error)) {
        return;
      }
      const text = error instanceof Error ? error.message : "RAG 评测运行失败";
      setStatusMessage(text);
      message.error(text);
    } finally {
      setRunningEvaluationId("");
    }
  }
  function resetExecutionInsights() {
    setRunRecords([]);
    setRunRecordFilters({
      status: "all",
      runType: "",
      appId: "",
      position: "all",
      resourceType: "",
      resourceId: "",
      flowKey: "",
    });
    setRunRecordDetail(null);
    setIsRunRecordDetailOpen(false);
    setIsRunRecordDetailLoading(false);
    setIsRunRecordsLoading(false);
    setEffectAnalytics(null);
    setEffectAnalyticsFilters({
      dateRange: "30d",
      position: "all",
    });
    setIsEffectAnalyticsLoading(false);
    setEvaluationCenter(null);
    setIsEvaluationCenterLoading(false);
    setRunningEvaluationId("");
    setMonitoringCenter(null);
    setMonitoringCenterFilters({
      dateRange: "30d",
    });
    setIsMonitoringCenterLoading(false);
  }

  return {
    runRecords,
    runRecordFilters,
    setRunRecordFilters,
    runRecordDetail,
    isRunRecordDetailOpen,
    setIsRunRecordDetailOpen,
    isRunRecordDetailLoading,
    isRunRecordsLoading,
    effectAnalytics,
    effectAnalyticsFilters,
    setEffectAnalyticsFilters,
    isEffectAnalyticsLoading,
    evaluationCenter,
    isEvaluationCenterLoading,
    runningEvaluationId,
    monitoringCenter,
    monitoringCenterFilters,
    setMonitoringCenterFilters,
    isMonitoringCenterLoading,
    refreshRunRecords,
    openRunRecordDetail,
    refreshEffectAnalytics,
    refreshEvaluationCenter,
    refreshMonitoringCenter,
    runEvaluation,
    resetExecutionInsights,
  };
}
