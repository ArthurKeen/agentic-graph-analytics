"use client";

import { useEffect, useMemo, useState } from "react";
import { createProductAPIClient, workspaceAssetsFromOverview } from "@/lib/product-api/client";
import { demoAssets, demoDag, demoReport } from "@/lib/product-api/demoData";
import type {
  ProductAPIClient,
  ReportBundle,
  WorkflowDAGView,
  WorkspaceAsset,
  WorkspaceHealth,
  WorkspaceOverview
} from "@/lib/product-api/types";

interface UseWorkspaceDataArgs {
  initialWorkspaceId?: string;
  initialRunId?: string;
  client?: ProductAPIClient;
}

interface WorkspaceDataState {
  assets: WorkspaceAsset[];
  dagByRunId: Record<string, WorkflowDAGView>;
  reportById: Record<string, ReportBundle>;
  overview: WorkspaceOverview | null;
  health: WorkspaceHealth | null;
  status: "demo" | "loading" | "ready" | "error";
  errorMessage?: string;
}

interface WorkspaceDataResult extends WorkspaceDataState {
  publishReport: (reportId: string, actor?: string) => Promise<ReportBundle>;
}

export function useWorkspaceData({
  initialWorkspaceId,
  initialRunId,
  client
}: UseWorkspaceDataArgs): WorkspaceDataResult {
  const apiClient = useMemo(() => client ?? createProductAPIClient(), [client]);
  const [state, setState] = useState<WorkspaceDataState>({
    assets: demoAssets,
    dagByRunId: { [demoDag.runId]: demoDag },
    reportById: { [demoReport.manifest.reportId]: demoReport },
    overview: null,
    health: null,
    status: "demo"
  });

  useEffect(() => {
    if (!initialWorkspaceId) {
      return;
    }

    const workspaceId = initialWorkspaceId;
    let cancelled = false;
    setState((current) => ({ ...current, status: "loading", errorMessage: undefined }));

    async function loadWorkspace() {
      try {
        const [overview, health] = await Promise.all([
          apiClient.getWorkspaceOverview(workspaceId),
          apiClient.getWorkspaceHealth(workspaceId)
        ]);
        const assets = workspaceAssetsFromOverview(overview);
        const firstRunId =
          initialRunId ??
          assets.find((asset) => asset.kind === "run")?.id;
        const dag = firstRunId ? await apiClient.getWorkflowDAG(firstRunId) : null;
        const reportBundles = await Promise.all(
          assets
            .filter((asset) => asset.kind === "report")
            .map((asset) => apiClient.getReportBundle(asset.id))
        );
        const reportById = Object.fromEntries(
          reportBundles.map((report) => [report.manifest.reportId, report])
        );

        if (cancelled) {
          return;
        }

        setState({
          assets: assets.length > 0 ? assets : demoAssets,
          dagByRunId: dag ? { [dag.runId]: dag } : { [demoDag.runId]: demoDag },
          reportById:
            Object.keys(reportById).length > 0
              ? reportById
              : { [demoReport.manifest.reportId]: demoReport },
          overview,
          health,
          status: "ready"
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setState((current) => ({
          ...current,
          status: "error",
          errorMessage: error instanceof Error ? error.message : "Failed to load workspace"
        }));
      }
    }

    void loadWorkspace();

    return () => {
      cancelled = true;
    };
  }, [apiClient, initialRunId, initialWorkspaceId]);

  const publishReport = async (
    reportId: string,
    actor = "workspace-ui"
  ): Promise<ReportBundle> => {
    if (!initialWorkspaceId) {
      const report = state.reportById[reportId] ?? statefulDemoPublish(reportId);
      const publishedReport = {
        ...report,
        manifest: {
          ...report.manifest,
          status: "published"
        }
      };
      setState((current) => ({
        ...current,
        reportById: {
          ...current.reportById,
          [reportId]: publishedReport
        }
      }));
      return publishedReport;
    }

    const publishedReport = await apiClient.publishReport(reportId, actor);
    setState((current) => ({
      ...current,
      reportById: {
        ...current.reportById,
        [reportId]: publishedReport
      }
    }));
    return publishedReport;
  };

  return {
    ...state,
    publishReport
  };
}

function statefulDemoPublish(reportId: string): ReportBundle {
  return {
    ...demoReport,
    manifest: {
      ...demoReport.manifest,
      reportId,
      status: "published"
    }
  };
}
