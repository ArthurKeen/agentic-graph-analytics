import type { ContextMenuItem } from "./types";

interface BuildCanvasContextMenuArgs {
  onCreateWorkspace: () => void;
  /** When provided, surfaces an "Edit Workspace" item. Hidden in demo mode
   * or when no workspace is loaded so we don't expose dead actions. */
  onEditWorkspace?: () => void;
  /** When provided, surfaces an "Archive Workspace" item. Hidden when the
   * workspace is already archived. */
  onArchiveWorkspace?: () => void;
  onCreateConnectionProfile: () => void;
  onCreateWorkflowRun: () => void;
  onExportWorkspace: () => void;
  onImportWorkspace: () => void;
  /** FR-13: when provided, surfaces an "Upload Document" item. Omitted
   * when no workspace is loaded so we don't expose a dead action. */
  onUploadDocument?: () => void;
  onFitAll: () => void;
  onCenterView: () => void;
  onViewAsOperational: () => void;
  onShowHelp: () => void;
}

export function buildCanvasContextMenu({
  onCreateWorkspace,
  onEditWorkspace,
  onArchiveWorkspace,
  onCreateConnectionProfile,
  onCreateWorkflowRun,
  onExportWorkspace,
  onImportWorkspace,
  onUploadDocument,
  onFitAll,
  onCenterView,
  onViewAsOperational,
  onShowHelp
}: BuildCanvasContextMenuArgs): ContextMenuItem[] {
  const items: ContextMenuItem[] = [
    {
      id: "create-workspace",
      label: "Create Workspace",
      icon: "+",
      onSelect: onCreateWorkspace
    }
  ];

  if (onEditWorkspace) {
    items.push({
      id: "edit-workspace",
      label: "Edit Workspace",
      icon: "E",
      onSelect: onEditWorkspace
    });
  }
  if (onArchiveWorkspace) {
    items.push({
      id: "archive-workspace",
      label: "Archive Workspace",
      icon: "A",
      onSelect: onArchiveWorkspace
    });
  }

  items.push(
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
    }
  );

  if (onUploadDocument) {
    items.push({
      id: "upload-document",
      label: "Upload Document",
      icon: "📄",
      onSelect: onUploadDocument
    });
  }

  items.push(
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
  );

  return items;
}
