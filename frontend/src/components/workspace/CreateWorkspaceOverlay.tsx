"use client";

import { useState } from "react";
import type { CreateWorkspaceInput } from "@/lib/product-api/types";

interface CreateWorkspaceOverlayProps {
  isCreating: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: CreateWorkspaceInput) => Promise<void>;
}

export function CreateWorkspaceOverlay({
  isCreating,
  errorMessage,
  onCancel,
  onSubmit
}: CreateWorkspaceOverlayProps) {
  const [customerName, setCustomerName] = useState("");
  const [projectName, setProjectName] = useState("");
  const [environment, setEnvironment] = useState("dev");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Create workspace">
        <h3>Create Workspace</h3>
        <p className="muted">
          Create product metadata for a customer graph. Connection profiles, graph profiles,
          requirements, runs, and reports will attach to this workspace.
        </p>
        <label>
          Customer name
          <input
            value={customerName}
            disabled={isCreating}
            onChange={(event) => setCustomerName(event.target.value)}
          />
        </label>
        <label>
          Project name
          <input
            value={projectName}
            disabled={isCreating}
            onChange={(event) => setProjectName(event.target.value)}
          />
        </label>
        <label>
          Environment
          <input
            value={environment}
            disabled={isCreating}
            onChange={(event) => setEnvironment(event.target.value)}
          />
        </label>
        <label>
          Description
          <textarea
            value={description}
            disabled={isCreating}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label>
          Tags
          <input
            value={tags}
            disabled={isCreating}
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
              isCreating ||
              !customerName.trim() ||
              !projectName.trim() ||
              !environment.trim()
            }
            onClick={() =>
              void onSubmit({
                customerName,
                projectName,
                environment,
                description,
                tags: tags
                  .split(",")
                  .map((tag) => tag.trim())
                  .filter(Boolean),
                actor: "workspace-ui"
              })
            }
          >
            {isCreating ? "Creating..." : "Create Workspace"}
          </button>
        </div>
      </section>
    </div>
  );
}
