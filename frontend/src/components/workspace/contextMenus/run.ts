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
      onSelect: onViewPipeline
    },
    {
      id: "copy-run-id",
      label: "Copy Run ID",
      onSelect: onCopyRunId
    },
    {
      id: "start-run",
      label: "Start Run",
      onSelect: onStartRun
    },
    {
      id: "retry-run",
      label: "Retry",
      onSelect: onRetryRun
    },
    {
      id: "delete-run",
      label: "Delete Run",
      danger: true,
      onSelect: onDeleteRun
    }
  ];
}
