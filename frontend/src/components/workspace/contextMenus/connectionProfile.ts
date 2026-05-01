import type { ContextMenuItem } from "./types";

interface BuildConnectionProfileContextMenuArgs {
  onOpenInCanvas: () => void;
  onVerifyConnection: () => void;
  onViewInfo: () => void;
  onCopyId: () => void;
}

export function buildConnectionProfileContextMenu({
  onOpenInCanvas,
  onVerifyConnection,
  onViewInfo,
  onCopyId
}: BuildConnectionProfileContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "open-in-canvas",
      label: "Open in Canvas",
      icon: "C",
      onSelect: onOpenInCanvas
    },
    {
      id: "verify-connection",
      label: "Verify Connection",
      icon: "V",
      onSelect: onVerifyConnection
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
