import type { ContextMenuItem } from "./types";

interface BuildCanvasContextMenuArgs {
  onFitAll: () => void;
  onCenterView: () => void;
  onViewAsOperational: () => void;
}

export function buildCanvasContextMenu({
  onFitAll,
  onCenterView,
  onViewAsOperational
}: BuildCanvasContextMenuArgs): ContextMenuItem[] {
  return [
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
    }
  ];
}
