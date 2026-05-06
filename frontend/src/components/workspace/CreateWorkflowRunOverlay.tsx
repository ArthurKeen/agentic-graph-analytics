"use client";

import { useState } from "react";
import type { CreateWorkflowRunInput } from "@/lib/product-api/types";

interface CreateWorkflowRunOverlayProps {
  isCreating: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: CreateWorkflowRunInput) => Promise<void>;
}

const TRADITIONAL_DEFAULT_STEPS = [
  "Requirements Review",
  "Schema Discovery",
  "Agent Analysis",
  "Dynamic Report"
].join("\n");

// FR-31a Phase 1 (PRD v0.4 decision 1): the backend ignores user-typed
// step labels for agentic runs and seeds the canonical six-step layout
// instead. The overlay mirrors that contract by showing the canonical
// labels read-only when "Agentic" is selected, so the visualizer the
// user sees during the run lines up with what they see in this preview.
//
// The strings are duplicated (rather than imported from a Python file)
// because the frontend can't import from the backend; keeping the list
// centralized in this constant means a backend change to AGENTIC_STEP_LAYOUT
// only requires editing this constant in lockstep.
const CANONICAL_AGENTIC_STEP_LABELS: ReadonlyArray<string> = [
  "Schema Analysis",
  "Requirements Extraction",
  "Use Case Generation",
  "Template Generation",
  "Execution",
  "Reporting"
];

export function CreateWorkflowRunOverlay({
  isCreating,
  errorMessage,
  onCancel,
  onSubmit
}: CreateWorkflowRunOverlayProps) {
  const [workflowMode, setWorkflowMode] = useState("agentic");
  const [stepText, setStepText] = useState(TRADITIONAL_DEFAULT_STEPS);

  const isAgentic =
    workflowMode === "agentic" || workflowMode === "parallel_agentic";
  const traditionalStepLabels = stepText
    .split("\n")
    .map((step) => step.trim())
    .filter(Boolean);
  // In agentic mode we still pass step labels for resilience, but the
  // backend will discard them and seed the canonical six. Sending the
  // canonical labels here keeps the request body honest and means
  // intermediate proxies / network logs see the labels that will end
  // up persisted, not the user's stale free-form text.
  const stepLabels = isAgentic
    ? Array.from(CANONICAL_AGENTIC_STEP_LABELS)
    : traditionalStepLabels;

  const submitDisabled =
    isCreating || (!isAgentic && traditionalStepLabels.length === 0);

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Create workflow run">
        <h3>Create Workflow Run</h3>
        <p className="muted">
          Create a queued, visualizable run. Agentic mode uses a fixed
          six-step pipeline run by the agent supervisor. Traditional mode
          accepts free-form step labels, one per line.
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

        {isAgentic ? (
          <div
            className="agentic-step-preview"
            role="group"
            aria-label="Agentic canonical steps"
          >
            <p className="muted">
              The agent supervisor runs these six phases in order. Step
              labels are not user-configurable in agentic mode.
            </p>
            <ol className="agentic-step-list">
              {CANONICAL_AGENTIC_STEP_LABELS.map((label) => (
                <li key={label}>{label}</li>
              ))}
            </ol>
          </div>
        ) : (
          <label>
            Steps
            <textarea
              value={stepText}
              disabled={isCreating}
              onChange={(event) => setStepText(event.target.value)}
            />
          </label>
        )}

        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        <div className="confirmation-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={submitDisabled}
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
