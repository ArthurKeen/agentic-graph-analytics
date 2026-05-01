import type { ContextMenuItem } from "./types";

interface BuildGraphProfileContextMenuArgs {
  onOpenInCanvas: () => void;
  onViewInfo: () => void;
  onCopyId: () => void;
}

export function buildGraphProfileContextMenu({
  onOpenInCanvas,
  onViewInfo,
  onCopyId
}: BuildGraphProfileContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "open-in-canvas",
      label: "Open in Canvas",
      icon: "G",
      onSelect: onOpenInCanvas
    },
    {
      id: "view-info",
      label: "View Info",
      icon: "i",
      onSelect: onViewInfo
    },
    {
      id: "copy-id",
      label: "Copy ID",
      icon: "#",
      onSelect: onCopyId
    }
  ];
}
