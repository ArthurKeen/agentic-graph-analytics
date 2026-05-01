import { WorkspaceShell } from "@/components/workspace/WorkspaceShell";

interface WorkspacePageProps {
  searchParams?: {
    workspaceId?: string;
    runId?: string;
  };
}

export default function WorkspacePage({ searchParams }: WorkspacePageProps) {
  return (
    <WorkspaceShell
      initialWorkspaceId={searchParams?.workspaceId}
      initialRunId={searchParams?.runId}
    />
  );
}
