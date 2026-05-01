import type { ContextMenuItem } from "./types";

interface BuildConnectionProfileContextMenuArgs {
  onOpenInCanvas: () => void;
  onVerifyConnection: () => void;
  onDiscoverGraph: () => void;
  onViewInfo: () => void;
  onCopyId: () => void;
}

export function buildConnectionProfileContextMenu({
  onOpenInCanvas,
  onVerifyConnection,
  onDiscoverGraph,
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
      id: "discover-graph",
      label: "Discover Graph Profile",
      icon: "G",
      onSelect: onDiscoverGraph
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
