import type { ContextMenuItem } from "./types";

interface BuildPipelineStepContextMenuArgs {
  onViewStepDetails: () => void;
  onCopyError: () => void;
  onViewRunResults: () => void;
  onRetryRun: () => void;
  /**
   * FR-31a Phase 1: per-step retry is unsupported on agentic runs because
   * the canonical pipeline executes start-to-finish and there is no
   * checkpoint to resume from yet (FR-31c+). Suppress the entry rather
   * than render a click-to-no-op so the user isn't misled. Traditional
   * runs continue to expose retry as before.
   */
  isAgenticRun?: boolean;
  /**
   * FR-30: a paused step is *resumed*, not retried — same backend
   * transition (PAUSED -> RUNNING, no retry_count bump), but calling it
   * "Retry" misrepresents what happens and is the reason FR-30 read as
   * unimplemented. The backend already advertises "resume" for paused
   * steps via supported_workflow_recovery_actions.
   */
  stepStatus?: string;
}

export function buildPipelineStepContextMenu({
  onViewStepDetails,
  onCopyError,
  onViewRunResults,
  onRetryRun,
  isAgenticRun = false,
  stepStatus
}: BuildPipelineStepContextMenuArgs): ContextMenuItem[] {
  const items: ContextMenuItem[] = [
    {
      id: "view-step-details",
      label: "View Step Details",
      icon: "🔍",
      onSelect: onViewStepDetails
    },
    {
      id: "copy-error",
      label: "Copy Error",
      icon: "📋",
      onSelect: onCopyError
    },
    {
      id: "view-run-results",
      label: "View Run Results",
      icon: "📊",
      onSelect: onViewRunResults
    }
  ];
  if (!isAgenticRun) {
    const isPaused = stepStatus === "paused";
    items.push({
      id: isPaused ? "resume-run" : "retry-run",
      label: isPaused ? "Resume Run" : "Retry Run",
      icon: isPaused ? "▶️" : "🔄",
      onSelect: onRetryRun
    });
  }
  return items;
}
