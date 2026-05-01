"use client";

import { useEffect, useMemo, useState } from "react";
import { createProductAPIClient, workspaceAssetsFromOverview } from "@/lib/product-api/client";
import { demoAssets, demoDag } from "@/lib/product-api/demoData";
import type {
  ProductAPIClient,
  WorkflowDAGView,
  WorkspaceAsset,
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
  overview: WorkspaceOverview | null;
  status: "demo" | "loading" | "ready" | "error";
  errorMessage?: string;
}

export function useWorkspaceData({
  initialWorkspaceId,
  initialRunId,
  client
}: UseWorkspaceDataArgs): WorkspaceDataState {
  const apiClient = useMemo(() => client ?? createProductAPIClient(), [client]);
  const [state, setState] = useState<WorkspaceDataState>({
    assets: demoAssets,
    dagByRunId: { [demoDag.runId]: demoDag },
    overview: null,
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
        const overview = await apiClient.getWorkspaceOverview(workspaceId);
        const assets = workspaceAssetsFromOverview(overview);
        const firstRunId =
          initialRunId ??
          assets.find((asset) => asset.kind === "run")?.id;
        const dag = firstRunId ? await apiClient.getWorkflowDAG(firstRunId) : null;

        if (cancelled) {
          return;
        }

        setState({
          assets: assets.length > 0 ? assets : demoAssets,
          dagByRunId: dag ? { [dag.runId]: dag } : { [demoDag.runId]: demoDag },
          overview,
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

  return state;
}
