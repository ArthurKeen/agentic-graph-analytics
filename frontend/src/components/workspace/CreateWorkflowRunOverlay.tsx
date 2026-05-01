"use client";

import { useState } from "react";
import type { CreateWorkflowRunInput } from "@/lib/product-api/types";

interface CreateWorkflowRunOverlayProps {
  isCreating: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: CreateWorkflowRunInput) => Promise<void>;
}

const DEFAULT_STEPS = [
  "Requirements Review",
  "Schema Discovery",
  "Agent Analysis",
  "Dynamic Report"
].join("\n");

export function CreateWorkflowRunOverlay({
  isCreating,
  errorMessage,
  onCancel,
  onSubmit
}: CreateWorkflowRunOverlayProps) {
  const [workflowMode, setWorkflowMode] = useState("agentic");
  const [stepText, setStepText] = useState(DEFAULT_STEPS);
  const stepLabels = stepText
    .split("\n")
    .map((step) => step.trim())
    .filter(Boolean);

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Create workflow run">
        <h3>Create Workflow Run</h3>
        <p className="muted">
          Create a queued, visualizable run. Enter one step label per line; the first version
          creates a sequential DAG.
        </p>
        <label>
          Workflow mode
          <select
            value={workflowMode}
            disabled={isCreating}
            onChange={(event) => setWorkflowMode(event.target.value)}
          >
            <option value="traditional">Traditional</option>
            <option value="agentic">Agentic</option>
            <option value="parallel_agentic">Parallel Agentic</option>
          </select>
        </label>
        <label>
          Steps
          <textarea
            value={stepText}
            disabled={isCreating}
            onChange={(event) => setStepText(event.target.value)}
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
            disabled={isCreating || stepLabels.length === 0}
            onClick={() =>
              void onSubmit({
                workflowMode,
                stepLabels
              })
            }
          >
            {isCreating ? "Creating..." : "Create Run"}
          </button>
        </div>
      </section>
    </div>
  );
}
