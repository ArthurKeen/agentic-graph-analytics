"use client";

import { FloatingDetailPanel } from "./FloatingDetailPanel";

interface WorkspaceHelpOverlayProps {
  onClose: () => void;
}

export function WorkspaceHelpOverlay({ onClose }: WorkspaceHelpOverlayProps) {
  return (
    <FloatingDetailPanel
      title="Workspace Help"
      placement="viewportTopRight"
      stackIndex={1}
      onClose={onClose}
    >
      <div className="help-content">
        <p>
          The workspace keeps you on one stage. Select objects to inspect them;
          right-click objects or the canvas to act.
        </p>
        <dl className="detail-list">
          <div>
            <dt>Left-click</dt>
            <dd>Selects an asset or pipeline step and opens read-only details.</dd>
          </div>
          <div>
            <dt>Right-click</dt>
            <dd>Opens actions for the specific asset, step, or canvas.</dd>
          </div>
          <div>
            <dt>Canvas actions</dt>
            <dd>
              Use canvas actions to create workflow runs, switch back to the
              operational DAG, or export/import workspace metadata bundles.
            </dd>
          </div>
          <div>
            <dt>Esc</dt>
            <dd>Closes open help and detail overlays.</dd>
          </div>
          <div>
            <dt>Deep links</dt>
            <dd>
              Use <code>/workspace?workspaceId=...&amp;runId=...</code> to open a
              workspace object without leaving the workspace route.
            </dd>
          </div>
        </dl>
      </div>
    </FloatingDetailPanel>
  );
}
