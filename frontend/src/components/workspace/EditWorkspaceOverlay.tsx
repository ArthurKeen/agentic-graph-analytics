"use client";

import { useState } from "react";

import type { UpdateWorkspaceInput, WorkspaceSummary } from "@/lib/product-api/types";

interface EditWorkspaceOverlayProps {
  workspace: WorkspaceSummary;
  isSaving: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: UpdateWorkspaceInput) => Promise<void>;
}

export function EditWorkspaceOverlay({
  workspace,
  isSaving,
  errorMessage,
  onCancel,
  onSubmit
}: EditWorkspaceOverlayProps) {
  // Initialize from the loaded workspace so the overlay shows current
  // values; the user only needs to edit the fields they care about. We
  // diff before submit to avoid sending no-op updates that would still
  // round-trip the network.
  const [customerName, setCustomerName] = useState(workspace.customerName);
  const [projectName, setProjectName] = useState(workspace.projectName);
  const [environment, setEnvironment] = useState(workspace.environment);
  const [description, setDescription] = useState(workspace.description);
  const [tags, setTags] = useState(workspace.tags.join(", "));

  const trimmedCustomer = customerName.trim();
  const trimmedProject = projectName.trim();
  const trimmedEnvironment = environment.trim();

  const buildPatch = (): UpdateWorkspaceInput => {
    const patch: UpdateWorkspaceInput = { actor: "workspace-ui" };
    if (trimmedCustomer !== workspace.customerName) patch.customerName = trimmedCustomer;
    if (trimmedProject !== workspace.projectName) patch.projectName = trimmedProject;
    if (trimmedEnvironment !== workspace.environment) patch.environment = trimmedEnvironment;
    if (description.trim() !== workspace.description) patch.description = description.trim();
    const nextTags = tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (nextTags.join("|") !== workspace.tags.join("|")) patch.tags = nextTags;
    return patch;
  };

  const isDirty = (() => {
    const patch = buildPatch();
    // The actor key is always set; treat as no-op when no other field
    // differs.
    return Object.keys(patch).filter((key) => key !== "actor").length > 0;
  })();

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Edit workspace">
        <h3>Edit Workspace</h3>
        <p className="muted">
          Update the workspace metadata. Lifecycle changes (archive) use a separate
          action so audit history stays clean.
        </p>
        <label>
          Customer name
          <input
            value={customerName}
            disabled={isSaving}
            onChange={(event) => setCustomerName(event.target.value)}
          />
        </label>
        <label>
          Project name
          <input
            value={projectName}
            disabled={isSaving}
            onChange={(event) => setProjectName(event.target.value)}
          />
        </label>
        <label>
          Environment
          <input
            value={environment}
            disabled={isSaving}
            onChange={(event) => setEnvironment(event.target.value)}
          />
        </label>
        <label>
          Description
          <textarea
            value={description}
            disabled={isSaving}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label>
          Tags
          <input
            value={tags}
            disabled={isSaving}
            placeholder="comma, separated, tags"
            onChange={(event) => setTags(event.target.value)}
          />
        </label>
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        <div className="confirmation-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={
              isSaving ||
              !isDirty ||
              !trimmedCustomer ||
              !trimmedProject ||
              !trimmedEnvironment
            }
            onClick={() => void onSubmit(buildPatch())}
          >
            {isSaving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </section>
    </div>
  );
}
