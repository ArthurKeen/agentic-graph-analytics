import type { ContextMenuItem } from "./types";

interface BuildWorkspaceActionsArgs {
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
}

interface BuildCanvasViewMenuArgs {
  onFitAll: () => void;
  onCenterView: () => void;
  onViewAsOperational: () => void;
  onShowHelp: () => void;
}

type BuildCanvasContextMenuArgs = BuildWorkspaceActionsArgs &
  BuildCanvasViewMenuArgs;

/** Actions that belong to the workspace, not to the canvas you right-clicked.
 *
 * Split out so the sidebar can render them as visible New and Workspace
 * menus (NFR-23). Creating a workspace, uploading a document and archiving
 * are capabilities requirements grant; they were reachable only by
 * right-clicking empty canvas, which is the one gesture a new user never
 * tries. The canvas menu still carries them as an accelerator.
 */
export function buildWorkspaceActions({
  onCreateWorkspace,
  onEditWorkspace,
  onArchiveWorkspace,
  onCreateConnectionProfile,
  onCreateWorkflowRun,
  onExportWorkspace,
  onImportWorkspace,
  onUploadDocument
}: BuildWorkspaceActionsArgs): ContextMenuItem[] {
  const items: ContextMenuItem[] = [
    {
      id: "create-workspace",
      label: "Create Workspace",
      icon: "new",
      group: "create",
      onSelect: onCreateWorkspace
    },
    {
      id: "create-connection-profile",
      label: "Create Connection Profile",
      icon: "new",
      group: "create",
      onSelect: onCreateConnectionProfile
    },
    {
      id: "create-workflow-run",
      label: "Create Workflow Run",
      icon: "new",
      group: "create",
      onSelect: onCreateWorkflowRun
    }
  ];

  if (onUploadDocument) {
    items.push({
      id: "upload-document",
      label: "Upload Document",
      icon: "doc",
      group: "create",
      onSelect: onUploadDocument
    });
  }

  items.push({
    id: "import-workspace",
    label: "Import Workspace Bundle",
    icon: "import",
    group: "create",
    onSelect: onImportWorkspace
  });

  if (onEditWorkspace) {
    items.push({
      id: "edit-workspace",
      label: "Edit Workspace",
      icon: "edit",
      group: "workspace",
      onSelect: onEditWorkspace
    });
  }

  items.push({
    id: "export-workspace",
    label: "Export Workspace Bundle",
    icon: "export",
    group: "workspace",
    onSelect: onExportWorkspace
  });

  if (onArchiveWorkspace) {
    items.push({
      id: "archive-workspace",
      label: "Archive Workspace",
      icon: "archive",
      group: "workspace",
      danger: true,
      onSelect: onArchiveWorkspace
    });
  }

  return items;
}

/** Panning, zooming and help. These stay on the canvas: they act on the
 * view you right-clicked, so there is nowhere else they belong. */
export function buildCanvasViewMenu({
  onFitAll,
  onCenterView,
  onViewAsOperational,
  onShowHelp
}: BuildCanvasViewMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "view-operational",
      label: "View As Operational DAG",
      icon: "view",
      group: "view",
      onSelect: onViewAsOperational
    },
    {
      id: "fit-all",
      label: "Fit All",
      icon: "fit",
      group: "view",
      onSelect: onFitAll
    },
    {
      id: "center-view",
      label: "Center View",
      icon: "center",
      group: "view",
      onSelect: onCenterView
    },
    {
      id: "show-help",
      label: "Show Workspace Help",
      icon: "help",
      group: "help",
      onSelect: onShowHelp
    }
  ];
}

export function buildCanvasContextMenu(
  args: BuildCanvasContextMenuArgs
): ContextMenuItem[] {
  return [...buildWorkspaceActions(args), ...buildCanvasViewMenu(args)];
}
