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
      onSelect: onOpenInCanvas
    },
    {
      id: "start-requirements-copilot",
      label: "Start Requirements Copilot",
      onSelect: onStartRequirementsCopilot
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
      id: "delete-graph-profile",
      danger: true,
      label: "Delete Graph Profile",
      onSelect: onDelete
    }
  ];
}
