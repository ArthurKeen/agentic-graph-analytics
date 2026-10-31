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
      icon: "copy",
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
      icon: "retry",
      onSelect: onRetryRun
    },
    {
      id: "delete-run",
      label: "Delete Run",
      icon: "delete",
      danger: true,
      onSelect: onDeleteRun
    }
  ];
}
