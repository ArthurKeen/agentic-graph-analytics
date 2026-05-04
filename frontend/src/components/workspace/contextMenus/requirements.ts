import type { ContextMenuItem } from "./types";

interface BuildRequirementsContextMenuArgs {
  onOpenInCanvas: () => void;
  /** Reopen the Requirements Copilot pre-populated from the workspace's
   * currently active version. Always available on the consolidated
   * "Requirements" asset row; the canvas-side affordance for viewing
   * historical (SUPERSEDED) versions lives inside the version selector
   * dropdown, not in this menu. */
  onReopenCopilot: () => void;
  onViewInfo: () => void;
  /** Copies the consolidated asset id (`requirements:<workspaceId>`). To copy
   * a specific version's id (e.g. for an audit link), users select that
   * version in the canvas dropdown and copy from there — keeping the menu
   * shallow. */
  onCopyId: () => void;
}

export function buildRequirementsContextMenu({
  onOpenInCanvas,
  onReopenCopilot,
  onViewInfo,
  onCopyId
}: BuildRequirementsContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "open-in-canvas",
      label: "Open in Canvas",
      icon: "R",
      onSelect: onOpenInCanvas
    },
    {
      id: "reopen-requirements-copilot",
      label: "Reopen Requirements Copilot",
      icon: "C",
      onSelect: onReopenCopilot
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
