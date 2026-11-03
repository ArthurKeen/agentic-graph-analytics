import { describe, expect, it, vi } from "vitest";
import { buildWorkspaceActions } from "../contextMenus/canvas";

/** FR-1 and FR-13 under NFR-23.
 *
 * Edit, Archive, Export, Import and Upload Document were reachable only by
 * right-clicking empty canvas. The sidebar renders buildWorkspaceActions as
 * two menus, "New" for the create group and "Workspace" for the workspace
 * group, so an action in neither group has no visible path and the
 * requirement is back to where it started.
 */

/** The groups AssetExplorer actually renders. Keep in step with the filters
 * in AssetExplorer: anything outside this set is invisible. */
const RENDERED_GROUPS = new Set(["create", "workspace"]);

function allHandlers() {
  return {
    onCreateWorkspace: vi.fn(),
    onEditWorkspace: vi.fn(),
    onArchiveWorkspace: vi.fn(),
    onCreateConnectionProfile: vi.fn(),
    onCreateWorkflowRun: vi.fn(),
    onExportWorkspace: vi.fn(),
    onImportWorkspace: vi.fn(),
    onUploadDocument: vi.fn()
  };
}

describe("workspace actions", () => {
  it("gives every workspace-level action a visible menu", () => {
    const items = buildWorkspaceActions(allHandlers());

    expect(items.length).toBeGreaterThan(0);
    for (const item of items) {
      expect(
        RENDERED_GROUPS.has(item.group ?? ""),
        `${item.id} is in group ${item.group}, which the sidebar does not render`
      ).toBe(true);
    }
  });

  it.each([
    ["upload-document", "FR-13"],
    ["edit-workspace", "FR-1"],
    ["archive-workspace", "FR-1"],
    ["export-workspace", "FR-1"],
    ["import-workspace", "FR-1"],
    ["create-workspace", "FR-1"]
  ])("%s has a visible path (%s)", (id) => {
    const visible = buildWorkspaceActions(allHandlers()).filter((item) =>
      RENDERED_GROUPS.has(item.group ?? "")
    );

    expect(visible.map((item) => item.id)).toContain(id);
  });

  it("still omits the actions the shell has no handler for", () => {
    // Hiding a dead entry is the reason these are conditional. A visible
    // menu makes that more important, not less: a disabled-looking button
    // for a workspace that does not exist is worse than no button.
    const { onEditWorkspace, onArchiveWorkspace, onUploadDocument, ...rest } =
      allHandlers();
    const ids = buildWorkspaceActions(rest).map((item) => item.id);

    expect(ids).not.toContain("edit-workspace");
    expect(ids).not.toContain("archive-workspace");
    expect(ids).not.toContain("upload-document");
    expect(ids).toContain("create-workspace");
  });

  it("routes a clicked action to its handler", () => {
    const handlers = allHandlers();
    const items = buildWorkspaceActions(handlers);

    items.find((item) => item.id === "upload-document")?.onSelect();

    expect(handlers.onUploadDocument).toHaveBeenCalledOnce();
  });

  it("flags archiving as destructive", () => {
    const items = buildWorkspaceActions(allHandlers());

    expect(items.find((item) => item.id === "archive-workspace")?.danger).toBe(
      true
    );
  });
});
