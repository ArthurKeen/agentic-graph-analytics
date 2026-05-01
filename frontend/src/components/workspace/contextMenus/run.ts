import type { ContextMenuItem } from "./types";

interface BuildRunContextMenuArgs {
  onViewPipeline: () => void;
  onCopyRunId: () => void;
  onRetryRun: () => void;
  onDeleteRun: () => void;
}

export function buildRunContextMenu({
  onViewPipeline,
  onCopyRunId,
  onRetryRun,
  onDeleteRun
}: BuildRunContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "view-pipeline",
      label: "View Pipeline & Metrics",
      icon: "⚡",
      onSelect: onViewPipeline
    },
    {
      id: "copy-run-id",
      label: "Copy Run ID",
      icon: "📋",
      onSelect: onCopyRunId
    },
    {
      id: "retry-run",
      label: "Retry",
      icon: "🔄",
      onSelect: onRetryRun
    },
    {
      id: "delete-run",
      label: "Delete Run",
      icon: "🗑️",
      danger: true,
      onSelect: onDeleteRun
    }
  ];
}
