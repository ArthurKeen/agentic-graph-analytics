import type { ContextMenuItem } from "./types";

interface BuildGraphProfileContextMenuArgs {
  onOpenInCanvas: () => void;
  onStartRequirementsCopilot: () => void;
  onViewInfo: () => void;
  onCopyId: () => void;
  onDelete: () => void;
}

export function buildGraphProfileContextMenu({
  onOpenInCanvas,
  onStartRequirementsCopilot,
  onViewInfo,
  onCopyId,
  onDelete
}: BuildGraphProfileContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "open-in-canvas",
      label: "Open in Canvas",
      icon: "G",
      onSelect: onOpenInCanvas
    },
    {
      id: "start-requirements-copilot",
      label: "Start Requirements Copilot",
      icon: "R",
      onSelect: onStartRequirementsCopilot
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
    },
    {
      id: "delete-graph-profile",
      label: "Delete Graph Profile",
      icon: "X",
      onSelect: onDelete
    }
  ];
}
