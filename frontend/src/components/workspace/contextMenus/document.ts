import type { ContextMenuItem } from "./types";

interface BuildDocumentContextMenuArgs {
  onOpenInCanvas: () => void;
  onViewInfo: () => void;
  onCopyId: () => void;
}

export function buildDocumentContextMenu({
  onOpenInCanvas,
  onViewInfo,
  onCopyId
}: BuildDocumentContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "open-in-canvas",
      label: "Open in Canvas",
      onSelect: onOpenInCanvas
    },
    {
      id: "view-info",
      label: "View Info",
      onSelect: onViewInfo
    },
    {
      id: "copy-id",
      label: "Copy ID",
      onSelect: onCopyId
    }
  ];
}
