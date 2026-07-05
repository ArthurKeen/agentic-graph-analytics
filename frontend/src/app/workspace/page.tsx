import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

interface WorkspacePageProps {
  searchParams?: {
    workspaceId?: string;
    runId?: string;
    /** Deep-link target for the Requirements canvas. When present, the
     * version dropdown opens on this id (read-only history mode if it isn't
     * the active version). */
    requirementVersion?: string;
  };
}

export default function WorkspacePage({ searchParams }: WorkspacePageProps) {
  return (
    <WorkspaceShell
      initialWorkspaceId={searchParams?.workspaceId}
      initialRunId={searchParams?.runId}
      initialRequirementVersionId={searchParams?.requirementVersion}
    />
  );
}
