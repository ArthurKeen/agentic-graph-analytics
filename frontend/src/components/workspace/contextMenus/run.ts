import type { ContextMenuItem } from "./types";

interface BuildRunContextMenuArgs {
  onViewPipeline: () => void;
  onCopyRunId: () => void;
  onStartRun: () => void;
  onRetryRun: () => void;
  onDeleteRun: () => void;
}

export function buildRunContextMenu({
  onViewPipeline,
  onCopyRunId,
  onStartRun,
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
      id: "start-run",
      label: "Start Run",
      icon: "▶",
      onSelect: onStartRun
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
