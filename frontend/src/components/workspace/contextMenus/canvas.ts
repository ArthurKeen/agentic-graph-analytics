import type { ContextMenuItem } from "./types";

interface BuildCanvasContextMenuArgs {
  onCreateConnectionProfile: () => void;
  onFitAll: () => void;
  onCenterView: () => void;
  onViewAsOperational: () => void;
  onShowHelp: () => void;
}

export function buildCanvasContextMenu({
  onCreateConnectionProfile,
  onFitAll,
  onCenterView,
  onViewAsOperational,
  onShowHelp
}: BuildCanvasContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "create-connection-profile",
      label: "Create Connection Profile",
      icon: "+",
      onSelect: onCreateConnectionProfile
    },
    {
      id: "view-operational",
      label: "View As Operational DAG",
      icon: "👁",
      onSelect: onViewAsOperational
    },
    {
      id: "fit-all",
      label: "Fit All",
      icon: "⬜",
      onSelect: onFitAll
    },
    {
      id: "center-view",
      label: "Center View",
      icon: "🎯",
      onSelect: onCenterView
    },
    {
      id: "show-help",
      label: "Show Workspace Help",
      icon: "?",
      onSelect: onShowHelp
    }
  ];
}
