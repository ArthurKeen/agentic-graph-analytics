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
      icon: "report",
      onSelect: onViewReport
    },
    {
      id: "copy-report-id",
      label: "Copy Report ID",
      icon: "copy",
      onSelect: onCopyReportId
    },
    {
      id: "publish-report",
      label: "Publish",
      icon: "publish",
      onSelect: onPublishReport
    }
  ];
}
