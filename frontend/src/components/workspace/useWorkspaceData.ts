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
  ConnectionGraphsResult,
  ConnectionProfileSummary,
  ConnectionVerificationResult,
  CreateConnectionProfileInput,
  CreateWorkspaceInput,
  CreateWorkflowRunInput,
  CreateWorkflowRunResult,
  DiscoverGraphProfileInput,
  GraphDiscoveryResult,
  GraphProfileSummary,
  ProductAPIClient,
  RequirementInterview,
  RequirementVersion,
  RequirementsDraftResult,
  ReportBundle,
  SourceDocumentSummary,
  StartRequirementsCopilotInput,
  WorkflowDAGView,
  WorkflowRecoveryActions,
  WorkflowRunSummary,
  WorkflowStepStatus,
  WorkflowStepUpdateResult,
  WorkspaceAsset,
  WorkspaceBundle,
  WorkspaceHealth,
  WorkspaceImportResult,
  WorkspaceOverview,
  WorkspaceSummary
} from "@/lib/product-api/types";

let demoRequirementInterview: RequirementInterview | null = null;

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
  recoveryActionsByRunId: Record<string, WorkflowRecoveryActions>;
  reportById: Record<string, ReportBundle>;
  overview: WorkspaceOverview | null;
  health: WorkspaceHealth | null;
  status: "demo" | "loading" | "ready" | "error";
  errorMessage?: string;
}

interface WorkspaceDataResult extends WorkspaceDataState {
  createWorkspace: (input: CreateWorkspaceInput) => Promise<WorkspaceSummary>;
  publishReport: (reportId: string, actor?: string) => Promise<ReportBundle>;
  createConnectionProfile: (
    input: CreateConnectionProfileInput
  ) => Promise<ConnectionProfileSummary>;
  verifyConnectionProfile: (connectionProfileId: string) => Promise<ConnectionVerificationResult>;
  listConnectionProfileGraphs: (
    connectionProfileId: string
  ) => Promise<ConnectionGraphsResult>;
  discoverGraphProfile: (
    connectionProfileId: string,
    input: DiscoverGraphProfileInput
  ) => Promise<GraphDiscoveryResult>;
  startRequirementsCopilot: (
    graphProfileId: string,
    input: StartRequirementsCopilotInput
  ) => Promise<RequirementInterview>;
  answerRequirementsCopilotQuestion: (
    requirementInterviewId: string,
    questionId: string,
    answer: string,
    actor?: string
  ) => Promise<RequirementInterview>;
  generateRequirementsCopilotDraft: (
    requirementInterviewId: string
  ) => Promise<RequirementsDraftResult>;
  approveRequirementsCopilotDraft: (
    requirementInterviewId: string,
    version: number,
    approvedBy?: string
  ) => Promise<RequirementVersion>;
  exportWorkspaceBundle: () => Promise<WorkspaceBundle>;
  importWorkspaceBundle: (bundle: WorkspaceBundle) => Promise<WorkspaceImportResult>;
  createWorkflowRun: (input: CreateWorkflowRunInput) => Promise<CreateWorkflowRunResult>;
  startWorkflowRun: (runId: string) => Promise<WorkflowRunSummary>;
  updateWorkflowStep: (
    runId: string,
    stepId: string,
    status: WorkflowStepStatus
  ) => Promise<WorkflowStepUpdateResult>;
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
    recoveryActionsByRunId: { [demoDag.runId]: demoRecoveryActions(demoDag) },
    reportById: { [demoReport.manifest.reportId]: demoReport },
    overview: null,
    health: null,
    status: "demo"
  });

  useEffect(() => {
    let cancelled = false;
    setState((current) => ({ ...current, status: "loading", errorMessage: undefined }));

    async function resolveWorkspaceId(): Promise<string | null> {
      if (initialWorkspaceId) {
        return initialWorkspaceId;
      }
      try {
        const workspaces = await apiClient.listWorkspaces();
        if (workspaces.length === 0) {
          return null;
        }
        return workspaces[0].workspaceId;
      } catch {
        return null;
      }
    }

    async function loadWorkspace() {
      const workspaceId = await resolveWorkspaceId();
      if (cancelled) {
        return;
      }
      if (!workspaceId) {
        // No real workspaces in the Product API yet — fall back to the canned
        // demo data the initial state was seeded with.
        setState((current) => ({ ...current, status: "demo", errorMessage: undefined }));
        return;
      }

      try {
        const [overview, health] = await Promise.all([
          apiClient.getWorkspaceOverview(workspaceId),
          apiClient.getWorkspaceHealth(workspaceId)
        ]);
        const assets = workspaceAssetsFromOverview(overview);
        const firstRunId =
          initialRunId ??
          assets.find((asset) => asset.kind === "run")?.id;
        const [dag, recoveryActions] = firstRunId
          ? await Promise.all([
              apiClient.getWorkflowDAG(firstRunId),
              apiClient.getWorkflowRecoveryActions(firstRunId)
            ])
          : [null, null];
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
          recoveryActionsByRunId:
            firstRunId && recoveryActions
              ? { [firstRunId]: recoveryActions }
              : { [demoDag.runId]: demoRecoveryActions(demoDag) },
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

  const createWorkspace = async (input: CreateWorkspaceInput): Promise<WorkspaceSummary> => {
    const workspace =
      initialWorkspaceId || state.status !== "demo"
        ? await apiClient.createWorkspace(input)
        : statefulDemoCreateWorkspace(input);
    setState((current) => ({
      ...current,
      overview: {
        workspace: {
          workspace_id: workspace.workspaceId,
          customer_name: workspace.customerName,
          project_name: workspace.projectName,
          environment: workspace.environment
        },
        counts: {},
        latestConnectionProfiles: [],
        latestGraphProfiles: [],
        latestSourceDocuments: [],
        latestWorkflowRuns: [],
        latestReports: [],
        latestAuditEvents: [
          {
            action: "create_workspace",
            entity_id: workspace.workspaceId,
            actor: input.actor ?? "workspace-ui"
          }
        ]
      },
      health: {
        workspaceId: workspace.workspaceId,
        status: "needs_attention",
        counts: {},
        issues: [
          {
            severity: "warning",
            code: "missing_connection_profile",
            message: "Workspace has no connection profiles.",
            entityIds: []
          }
        ]
      },
      status: current.status === "demo" ? "demo" : "ready",
      errorMessage: undefined
    }));
    return workspace;
  };

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

  const listConnectionProfileGraphs = async (
    connectionProfileId: string
  ): Promise<ConnectionGraphsResult> => {
    if (initialWorkspaceId || state.status !== "demo") {
      return apiClient.listConnectionProfileGraphs(connectionProfileId);
    }
    return statefulDemoListConnectionProfileGraphs(connectionProfileId);
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

  const startRequirementsCopilot = async (
    graphProfileId: string,
    input: StartRequirementsCopilotInput
  ): Promise<RequirementInterview> => {
    return initialWorkspaceId
      ? apiClient.startRequirementsCopilot(graphProfileId, input)
      : statefulDemoStartRequirementsCopilot(graphProfileId, input);
  };

  const answerRequirementsCopilotQuestion = async (
    requirementInterviewId: string,
    questionId: string,
    answer: string,
    actor = "workspace-ui"
  ): Promise<RequirementInterview> => {
    return initialWorkspaceId
      ? apiClient.answerRequirementsCopilotQuestion(
          requirementInterviewId,
          questionId,
          answer,
          actor
        )
      : statefulDemoAnswerRequirementsCopilotQuestion(
          requirementInterviewId,
          questionId,
          answer,
          actor
        );
  };

  const generateRequirementsCopilotDraft = async (
    requirementInterviewId: string
  ): Promise<RequirementsDraftResult> => {
    return initialWorkspaceId
      ? apiClient.generateRequirementsCopilotDraft(requirementInterviewId)
      : statefulDemoGenerateRequirementsCopilotDraft(requirementInterviewId);
  };

  const approveRequirementsCopilotDraft = async (
    requirementInterviewId: string,
    version: number,
    approvedBy = "workspace-ui"
  ): Promise<RequirementVersion> => {
    return initialWorkspaceId
      ? apiClient.approveRequirementsCopilotDraft(requirementInterviewId, version, approvedBy)
      : statefulDemoApproveRequirementsCopilotDraft(requirementInterviewId, version, approvedBy);
  };

  const exportWorkspaceBundle = async (): Promise<WorkspaceBundle> => {
    return initialWorkspaceId
      ? apiClient.exportWorkspaceBundle(initialWorkspaceId)
      : statefulDemoExportWorkspaceBundle(state);
  };

  const importWorkspaceBundle = async (
    bundle: WorkspaceBundle
  ): Promise<WorkspaceImportResult> => {
    return initialWorkspaceId
      ? apiClient.importWorkspaceBundle(bundle)
      : statefulDemoImportWorkspaceBundle(bundle);
  };

  const createWorkflowRun = async (
    input: CreateWorkflowRunInput
  ): Promise<CreateWorkflowRunResult> => {
    const workspaceId =
      initialWorkspaceId ?? state.overview?.workspace.workspace_id ?? demoDag.workspaceId;
    const result = initialWorkspaceId
      ? await apiClient.createWorkflowRun(workspaceId, input)
      : statefulDemoCreateWorkflowRun(workspaceId, input);
    const asset: WorkspaceAsset = {
      id: result.workflowRun.runId,
      kind: "run",
      label: `Run ${result.workflowRun.runId}`,
      description: `${result.workflowRun.workflowMode} workflow (${result.workflowRun.status})`
    };

    setState((current) => ({
      ...current,
      assets: [asset, ...current.assets.filter((item) => item.id !== asset.id)],
      dagByRunId: {
        ...current.dagByRunId,
        [result.workflowRun.runId]: result.dagView
      },
      recoveryActionsByRunId: {
        ...current.recoveryActionsByRunId,
        [result.workflowRun.runId]: demoRecoveryActions(result.dagView)
      }
    }));

    return result;
  };

  const startWorkflowRun = async (runId: string): Promise<WorkflowRunSummary> => {
    const workflowRun = initialWorkspaceId
      ? await apiClient.startWorkflowRun(runId)
      : statefulDemoStartWorkflowRun(runId);

    setState((current) => ({
      ...current,
      assets: current.assets.map((asset) =>
        asset.id === runId
          ? {
              ...asset,
              description: `${workflowRun.workflowMode} workflow (${workflowRun.status})`
            }
          : asset
      ),
      dagByRunId: current.dagByRunId[runId]
        ? {
            ...current.dagByRunId,
            [runId]: {
              ...current.dagByRunId[runId],
              status: workflowRun.status
            }
          }
        : current.dagByRunId
    }));

    return workflowRun;
  };

  const updateWorkflowStep = async (
    runId: string,
    stepId: string,
    status: WorkflowStepStatus
  ): Promise<WorkflowStepUpdateResult> => {
    const result = initialWorkspaceId
      ? await apiClient.updateWorkflowStep(runId, stepId, status)
      : statefulDemoUpdateWorkflowStep(runId, stepId, status);

    setState((current) => ({
      ...current,
      assets: current.assets.map((asset) =>
        asset.id === runId
          ? {
              ...asset,
              description: `${result.workflowRun.workflowMode} workflow (${result.workflowRun.status})`
            }
          : asset
      ),
      dagByRunId: {
        ...current.dagByRunId,
        [runId]: result.dagView
      },
      recoveryActionsByRunId: {
        ...current.recoveryActionsByRunId,
        [runId]: demoRecoveryActions(result.dagView)
      }
    }));

    return result;
  };

  return {
    ...state,
    createWorkspace,
    publishReport,
    createConnectionProfile,
    verifyConnectionProfile,
    listConnectionProfileGraphs,
    discoverGraphProfile,
    startRequirementsCopilot,
    answerRequirementsCopilotQuestion,
    generateRequirementsCopilotDraft,
    approveRequirementsCopilotDraft,
    exportWorkspaceBundle,
    importWorkspaceBundle,
    createWorkflowRun,
    startWorkflowRun,
    updateWorkflowStep
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

function statefulDemoCreateWorkspace(input: CreateWorkspaceInput): WorkspaceSummary {
  return {
    workspaceId: `workspace-${Date.now()}`,
    customerName: input.customerName.trim(),
    projectName: input.projectName.trim(),
    environment: input.environment.trim(),
    description: input.description?.trim() ?? "",
    status: "active",
    tags: input.tags ?? []
  };
}

function demoRecoveryActions(dag: WorkflowDAGView): WorkflowRecoveryActions {
  return Object.fromEntries(
    dag.nodes.map((node) => [
      node.id,
      node.status === "failed"
        ? ["retry", "open_logs"]
        : node.status === "paused"
          ? ["resume", "cancel", "open_logs"]
          : []
    ])
  );
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

function statefulDemoListConnectionProfileGraphs(
  connectionProfileId: string
): ConnectionGraphsResult {
  return {
    connectionProfileId,
    workspaceId: "workspace-demo",
    database: demoConnectionProfile.database,
    graphs: [
      {
        name: demoGraphProfile.graphName,
        isSystem: false,
        vertexCollections: demoGraphProfile.vertexCollections,
        edgeCollections: demoGraphProfile.edgeCollections,
        orphanCollections: [],
        edgeDefinitions: demoGraphProfile.edgeDefinitions,
        vertexCount: demoGraphProfile.counts?.total_documents ?? null,
        edgeCount: demoGraphProfile.counts?.total_edges ?? null
      }
    ]
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

function statefulDemoStartRequirementsCopilot(
  graphProfileId: string,
  input: StartRequirementsCopilotInput
): RequirementInterview {
  const graphProfile = demoGraphProfile.graphProfileId === graphProfileId
    ? demoGraphProfile
    : { ...demoGraphProfile, graphProfileId };
  demoRequirementInterview = {
    requirementInterviewId: `requirement-interview-${Date.now()}`,
    workspaceId: graphProfile.workspaceId,
    graphProfileId,
    status: "draft",
    domain: input.domain?.trim() || null,
    questions: [
      {
        id: "business_goal",
        text: `What business decision should ${graphProfile.graphName} support?`,
        provenance: "user_provided"
      },
      {
        id: "analytics_questions",
        text: "What graph analytics questions should the system answer?",
        provenance: "user_provided"
      },
      {
        id: "audience",
        text: "Who will consume the report and what level of detail do they need?",
        provenance: "user_provided"
      },
      {
        id: "constraints",
        text: "What runtime, cost, freshness, sensitivity, or evidence constraints apply?",
        provenance: "user_provided"
      }
    ],
    answers: [],
    schemaObservations: {
      graph_name: graphProfile.graphName,
      vertex_collections: graphProfile.vertexCollections,
      edge_collections: graphProfile.edgeCollections,
      counts: graphProfile.counts
    },
    inferences: [],
    assumptions: [],
    draftBrd: null,
    provenanceLabels: []
  };
  return demoRequirementInterview;
}

function statefulDemoAnswerRequirementsCopilotQuestion(
  requirementInterviewId: string,
  questionId: string,
  answer: string,
  actor: string
): RequirementInterview {
  const interview =
    demoRequirementInterview?.requirementInterviewId === requirementInterviewId
      ? demoRequirementInterview
      : statefulDemoStartRequirementsCopilot(demoGraphProfile.graphProfileId, {});
  const answers = [
    ...interview.answers.filter((existing) => existing.question_id !== questionId),
    {
      question_id: questionId,
      answer,
      actor,
      answered_at: new Date().toISOString()
    }
  ];
  demoRequirementInterview = {
    ...interview,
    requirementInterviewId,
    answers
  };
  return demoRequirementInterview;
}

function statefulDemoGenerateRequirementsCopilotDraft(
  requirementInterviewId: string
): RequirementsDraftResult {
  const currentInterview =
    demoRequirementInterview?.requirementInterviewId === requirementInterviewId
      ? demoRequirementInterview
      : statefulDemoStartRequirementsCopilot(demoGraphProfile.graphProfileId, {});
  const requirementInterview = {
    ...currentInterview,
    requirementInterviewId,
    status: "ready_for_review",
    draftBrd:
      "# Business Requirements Draft\n\nThis draft was generated from demo schema observations and saved interview answers."
  };
  demoRequirementInterview = requirementInterview;
  return {
    requirementInterview,
    draftBrd: requirementInterview.draftBrd ?? "",
    provenanceLabels: [
      { path: "observed_schema.graph_name", label: "observed_from_schema" },
      { path: "answers", label: "user_provided" }
    ]
  };
}

function statefulDemoApproveRequirementsCopilotDraft(
  requirementInterviewId: string,
  version: number,
  approvedBy: string
): RequirementVersion {
  const currentInterview =
    demoRequirementInterview?.requirementInterviewId === requirementInterviewId
      ? demoRequirementInterview
      : statefulDemoStartRequirementsCopilot(demoGraphProfile.graphProfileId, {});
  demoRequirementInterview = {
    ...currentInterview,
    status: "approved"
  };
  return {
    requirementVersionId: `requirement-version-${Date.now()}`,
    workspaceId: currentInterview.workspaceId,
    version,
    status: "approved",
    requirementInterviewId,
    summary: "Requirements Copilot approved draft",
    objectives: [],
    requirements: [],
    constraints: [],
    approvedAt: new Date().toISOString(),
    metadata: {
      approved_by: approvedBy,
      source: "requirements_copilot"
    }
  };
}

function statefulDemoExportWorkspaceBundle(state: WorkspaceDataState): WorkspaceBundle {
  return {
    schemaVersion: "demo",
    workspace: {
      workspace_id: state.overview?.workspace.workspace_id ?? "workspace-demo",
      customer_name: state.overview?.workspace.customer_name ?? "Demo Customer",
      project_name: state.overview?.workspace.project_name ?? "Graph Analytics",
      environment: state.overview?.workspace.environment ?? "demo"
    },
    connectionProfiles: toRecordArray(Object.values(state.connectionProfileById)),
    graphProfiles: toRecordArray(Object.values(state.graphProfileById)),
    sourceDocuments: toRecordArray(Object.values(state.documentById)),
    requirementInterviews: demoRequirementInterview ? toRecordArray([demoRequirementInterview]) : [],
    requirementVersions: [],
    workflowRuns: toRecordArray(Object.values(state.dagByRunId)),
    reports: toRecordArray(Object.values(state.reportById)),
    auditEvents: []
  };
}

function toRecordArray<T>(items: T[]): Array<Record<string, unknown>> {
  return items.map((item) => ({ ...(item as object) }));
}

function statefulDemoImportWorkspaceBundle(bundle: WorkspaceBundle): WorkspaceImportResult {
  return {
    workspaceId: String(bundle.workspace.workspace_id ?? bundle.workspace._key ?? "workspace-demo"),
    counts: {
      connection_profiles: bundle.connectionProfiles.length,
      graph_profiles: bundle.graphProfiles.length,
      source_documents: bundle.sourceDocuments.length,
      requirement_versions: bundle.requirementVersions.length,
      workflow_runs: bundle.workflowRuns.length,
      reports: bundle.reports.length
    }
  };
}

function statefulDemoCreateWorkflowRun(
  workspaceId: string,
  input: CreateWorkflowRunInput
): CreateWorkflowRunResult {
  const runId = `run-${Date.now()}`;
  const nodes = input.stepLabels.map((label, index) => ({
    id: slugifyStepId(label, index),
    label,
    status: "pending" as const,
    artifactCount: 0,
    warningCount: 0,
    errorCount: 0
  }));
  const dagView = {
    runId,
    workspaceId,
    status: "queued",
    workflowMode: input.workflowMode,
    nodes,
    edges: nodes.slice(1).map((node, index) => ({
      id: `${nodes[index].id}-${node.id}`,
      from: nodes[index].id,
      to: node.id
    })),
    warnings: [],
    errors: []
  };
  return {
    workflowRun: {
      runId,
      workspaceId,
      workflowMode: input.workflowMode,
      status: "queued"
    },
    dagView
  };
}

function slugifyStepId(label: string, index: number): string {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug || `step-${index + 1}`;
}

function statefulDemoStartWorkflowRun(runId: string): WorkflowRunSummary {
  return {
    runId,
    workspaceId: demoDag.workspaceId,
    workflowMode: demoDag.workflowMode,
    status: "running",
    startedAt: new Date().toISOString(),
    completedAt: null
  };
}

function statefulDemoUpdateWorkflowStep(
  runId: string,
  stepId: string,
  status: WorkflowStepStatus
): WorkflowStepUpdateResult {
  const currentDag = demoDag.runId === runId ? demoDag : { ...demoDag, runId };
  const dagView = {
    ...currentDag,
    status: status === "running" ? "running" : currentDag.status,
    nodes: currentDag.nodes.map((node) =>
      node.id === stepId
        ? {
            ...node,
            status
          }
        : node
    )
  };
  return {
    workflowRun: {
      runId,
      workspaceId: currentDag.workspaceId,
      workflowMode: currentDag.workflowMode,
      status: dagView.status
    },
    dagView
  };
}
