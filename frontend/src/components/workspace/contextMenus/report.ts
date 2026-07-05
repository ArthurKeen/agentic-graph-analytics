import type { ContextMenuItem } from "./types";

interface BuildReportContextMenuArgs {
  onViewReport: () => void;
  onCopyReportId: () => void;
  onPublishReport: () => void;
}

export function buildReportContextMenu({
  onViewReport,
  onCopyReportId,
  onPublishReport
}: BuildReportContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "view-report",
      label: "View Report",
      icon: "📊",
      onSelect: onViewReport
    },
    {
      id: "copy-report-id",
      label: "Copy Report ID",
      icon: "📋",
      onSelect: onCopyReportId
    },
    {
      id: "publish-report",
      label: "Publish",
      icon: "🚀",
      onSelect: onPublishReport
    }
  ];
}
