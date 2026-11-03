import type { ContextMenuItem } from "./types";

interface BuildConnectionProfileContextMenuArgs {
  onOpenInCanvas: () => void;
  onVerifyConnection: () => void;
  onDiscoverGraph: () => void;
  onViewInfo: () => void;
  onCopyId: () => void;
  onDelete: () => void;
}

export function buildConnectionProfileContextMenu({
  onOpenInCanvas,
  onVerifyConnection,
  onDiscoverGraph,
  onViewInfo,
  onCopyId,
  onDelete
}: BuildConnectionProfileContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "open-in-canvas",
      label: "Open in Canvas",
      onSelect: onOpenInCanvas
    },
    {
      id: "verify-connection",
      label: "Verify Connection",
      onSelect: onVerifyConnection
    },
    {
      id: "discover-graph",
      label: "Discover Graph Profile",
      onSelect: onDiscoverGraph
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
    },
    {
      id: "delete-connection-profile",
      danger: true,
      label: "Delete Connection Profile",
      onSelect: onDelete
    }
  ];
}
