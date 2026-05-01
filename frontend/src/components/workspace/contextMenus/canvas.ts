import type { ContextMenuItem } from "./types";

interface BuildCanvasContextMenuArgs {
  onCreateWorkspace: () => void;
  onCreateConnectionProfile: () => void;
  onCreateWorkflowRun: () => void;
  onExportWorkspace: () => void;
  onImportWorkspace: () => void;
  onFitAll: () => void;
  onCenterView: () => void;
  onViewAsOperational: () => void;
  onShowHelp: () => void;
}

export function buildCanvasContextMenu({
  onCreateWorkspace,
  onCreateConnectionProfile,
  onCreateWorkflowRun,
  onExportWorkspace,
  onImportWorkspace,
  onFitAll,
  onCenterView,
  onViewAsOperational,
  onShowHelp
}: BuildCanvasContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "create-workspace",
      label: "Create Workspace",
      icon: "+",
      onSelect: onCreateWorkspace
    },
    {
      id: "create-connection-profile",
      label: "Create Connection Profile",
      icon: "+",
      onSelect: onCreateConnectionProfile
    },
    {
      id: "create-workflow-run",
      label: "Create Workflow Run",
      icon: "+",
      onSelect: onCreateWorkflowRun
    },
    {
      id: "export-workspace",
      label: "Export Workspace Bundle",
      icon: "JSON",
      onSelect: onExportWorkspace
    },
    {
      id: "import-workspace",
      label: "Import Workspace Bundle",
      icon: "JSON",
      onSelect: onImportWorkspace
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
