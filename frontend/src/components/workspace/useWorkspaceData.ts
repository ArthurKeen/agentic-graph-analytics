"use client";

import { useEffect, useMemo, useState } from "react";
import { createProductAPIClient, workspaceAssetsFromOverview } from "@/lib/product-api/client";
import {
  demoAssets,
  demoConnectionProfile,
  demoDag,
  demoGraphProfile,
  demoReport,
  demoSourceDocument
} from "@/lib/product-api/demoData";
import type {
  ConnectionProfileSummary,
  ConnectionVerificationResult,
  CreateConnectionProfileInput,
  DiscoverGraphProfileInput,
  GraphDiscoveryResult,
  GraphProfileSummary,
  ProductAPIClient,
  ReportBundle,
  SourceDocumentSummary,
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
  connectionProfileById: Record<string, ConnectionProfileSummary>;
  graphProfileById: Record<string, GraphProfileSummary>;
  documentById: Record<string, SourceDocumentSummary>;
  dagByRunId: Record<string, WorkflowDAGView>;
  reportById: Record<string, ReportBundle>;
  overview: WorkspaceOverview | null;
  health: WorkspaceHealth | null;
  status: "demo" | "loading" | "ready" | "error";
  errorMessage?: string;
}

interface WorkspaceDataResult extends WorkspaceDataState {
  publishReport: (reportId: string, actor?: string) => Promise<ReportBundle>;
  createConnectionProfile: (
    input: CreateConnectionProfileInput
  ) => Promise<ConnectionProfileSummary>;
  verifyConnectionProfile: (connectionProfileId: string) => Promise<ConnectionVerificationResult>;
  discoverGraphProfile: (
    connectionProfileId: string,
    input: DiscoverGraphProfileInput
  ) => Promise<GraphDiscoveryResult>;
}

export function useWorkspaceData({
  initialWorkspaceId,
  initialRunId,
  client
}: UseWorkspaceDataArgs): WorkspaceDataResult {
  const apiClient = useMemo(() => client ?? createProductAPIClient(), [client]);
  const [state, setState] = useState<WorkspaceDataState>({
    assets: demoAssets,
    connectionProfileById: {
      [demoConnectionProfile.connectionProfileId]: demoConnectionProfile
    },
    graphProfileById: { [demoGraphProfile.graphProfileId]: demoGraphProfile },
    documentById: { [demoSourceDocument.documentId]: demoSourceDocument },
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
          connectionProfileById:
            overview.latestConnectionProfiles.length > 0
              ? Object.fromEntries(
                  overview.latestConnectionProfiles.map((profile) => [
                    profile.connectionProfileId,
                    profile
                  ])
                )
              : {
                  [demoConnectionProfile.connectionProfileId]: demoConnectionProfile
                },
          graphProfileById:
            overview.latestGraphProfiles.length > 0
              ? Object.fromEntries(
                  overview.latestGraphProfiles.map((profile) => [
                    profile.graphProfileId,
                    profile
                  ])
                )
              : { [demoGraphProfile.graphProfileId]: demoGraphProfile },
          documentById:
            overview.latestSourceDocuments.length > 0
              ? Object.fromEntries(
                  overview.latestSourceDocuments.map((document) => [
                    document.documentId,
                    document
                  ])
                )
              : { [demoSourceDocument.documentId]: demoSourceDocument },
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

  const createConnectionProfile = async (
    input: CreateConnectionProfileInput
  ): Promise<ConnectionProfileSummary> => {
    const profile = initialWorkspaceId
      ? await apiClient.createConnectionProfile(initialWorkspaceId, input)
      : statefulDemoCreateConnectionProfile(input);
    const asset: WorkspaceAsset = {
      id: profile.connectionProfileId,
      kind: "connection-profile",
      label: profile.name,
      description: `${profile.deploymentMode} connection (${profile.lastVerificationStatus})`
    };

    setState((current) => ({
      ...current,
      assets: [asset, ...current.assets.filter((item) => item.id !== asset.id)],
      connectionProfileById: {
        ...current.connectionProfileById,
        [profile.connectionProfileId]: profile
      }
    }));
    return profile;
  };

  const verifyConnectionProfile = async (
    connectionProfileId: string
  ): Promise<ConnectionVerificationResult> => {
    const verification = initialWorkspaceId
      ? await apiClient.verifyConnectionProfile(connectionProfileId)
      : statefulDemoVerifyConnectionProfile(connectionProfileId);

    setState((current) => {
      const profile = current.connectionProfileById[connectionProfileId];
      if (!profile) {
        return current;
      }

      const updatedProfile = {
        ...profile,
        lastVerificationStatus: verification.status,
        lastVerifiedAt: verification.verifiedAt
      };
      return {
        ...current,
        assets: current.assets.map((asset) =>
          asset.id === connectionProfileId
            ? {
                ...asset,
                description: `${updatedProfile.deploymentMode} connection (${updatedProfile.lastVerificationStatus})`
              }
            : asset
        ),
        connectionProfileById: {
          ...current.connectionProfileById,
          [connectionProfileId]: updatedProfile
        }
      };
    });

    return verification;
  };

  const discoverGraphProfile = async (
    connectionProfileId: string,
    input: DiscoverGraphProfileInput
  ): Promise<GraphDiscoveryResult> => {
    const discovery = initialWorkspaceId
      ? await apiClient.discoverGraphProfile(connectionProfileId, input)
      : statefulDemoDiscoverGraphProfile(connectionProfileId, input);
    const profile = discovery.graphProfile;
    const asset: WorkspaceAsset = {
      id: profile.graphProfileId,
      kind: "graph-profile",
      label: profile.graphName,
      description: `Graph profile (${profile.status})`
    };

    setState((current) => ({
      ...current,
      assets: [asset, ...current.assets.filter((item) => item.id !== asset.id)],
      graphProfileById: {
        ...current.graphProfileById,
        [profile.graphProfileId]: profile
      }
    }));
    return discovery;
  };

  return {
    ...state,
    publishReport,
    createConnectionProfile,
    verifyConnectionProfile,
    discoverGraphProfile
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

function statefulDemoCreateConnectionProfile(
  input: CreateConnectionProfileInput
): ConnectionProfileSummary {
  return {
    connectionProfileId: `connection-${Date.now()}`,
    workspaceId: "workspace-demo",
    name: input.name,
    deploymentMode: input.deploymentMode,
    endpoint: input.endpoint,
    database: input.database,
    username: input.username,
    verifySsl: input.verifySsl,
    secretRefs: input.passwordSecretEnvVar
      ? { password: { kind: "env", ref: input.passwordSecretEnvVar } }
      : {},
    lastVerificationStatus: "unknown",
    lastVerifiedAt: null,
    metadata: { source: "demo" }
  };
}

function statefulDemoVerifyConnectionProfile(
  connectionProfileId: string
): ConnectionVerificationResult {
  return {
    connectionProfileId,
    workspaceId: "workspace-demo",
    status: "success",
    verifiedAt: new Date().toISOString(),
    endpoint: demoConnectionProfile.endpoint,
    database: demoConnectionProfile.database,
    errorMessage: null
  };
}

function statefulDemoDiscoverGraphProfile(
  connectionProfileId: string,
  input: DiscoverGraphProfileInput
): GraphDiscoveryResult {
  const graphProfile = {
    ...demoGraphProfile,
    graphProfileId: `graph-profile-${Date.now()}`,
    connectionProfileId,
    graphName: input.graphName?.trim() || demoGraphProfile.graphName,
    status: "active"
  };
  return {
    graphProfile,
    schemaSummary: {
      database_name: demoConnectionProfile.database,
      graph_names: [graphProfile.graphName],
      sample_size: input.sampleSize
    }
  };
}
