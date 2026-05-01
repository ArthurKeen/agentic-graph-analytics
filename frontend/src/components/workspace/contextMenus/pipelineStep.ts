import type { ContextMenuItem } from "./types";

interface BuildPipelineStepContextMenuArgs {
  onViewStepDetails: () => void;
  onCopyError: () => void;
  onViewRunResults: () => void;
  onRetryRun: () => void;
}

export function buildPipelineStepContextMenu({
  onViewStepDetails,
  onCopyError,
  onViewRunResults,
  onRetryRun
}: BuildPipelineStepContextMenuArgs): ContextMenuItem[] {
  return [
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
    },
    {
      id: "retry-run",
      label: "Retry Run",
      icon: "🔄",
      onSelect: onRetryRun
    }
  ];
}
