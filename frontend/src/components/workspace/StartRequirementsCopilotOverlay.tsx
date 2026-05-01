"use client";

import { useState, type FormEvent } from "react";
import type { StartRequirementsCopilotInput, WorkspaceAsset } from "@/lib/product-api/types";

interface StartRequirementsCopilotOverlayProps {
  graphProfile: WorkspaceAsset;
  isStarting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: StartRequirementsCopilotInput) => Promise<void>;
}

export function StartRequirementsCopilotOverlay({
  graphProfile,
  isStarting,
  errorMessage,
  onCancel,
  onSubmit
}: StartRequirementsCopilotOverlayProps) {
  const [form, setForm] = useState<StartRequirementsCopilotInput>({
    domain: "",
    createdBy: "workspace-ui"
  });

  const updateField = <K extends keyof StartRequirementsCopilotInput>(
    key: K,
    value: StartRequirementsCopilotInput[K]
  ) => setForm((current) => ({ ...current, [key]: value }));

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(form);
  }

  return (
    <div className="confirmation-backdrop" role="presentation" onClick={onCancel}>
      <form
        className="connection-profile-overlay"
        aria-label="Start Requirements Copilot"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <header>
          <div>
            <p className="muted">Graph Profile</p>
            <h2>Start Requirements Copilot</h2>
          </div>
          <button
            className="secondary-button"
            type="button"
            disabled={isStarting}
            onClick={onCancel}
          >
            Close
          </button>
        </header>

        <p className="muted">
          Start a schema-aware interview for {graphProfile.label}. The copilot will use
          discovered collections and graph metadata to generate starter questions.
        </p>

        <label>
          Domain
          <input
            placeholder="Clinical trials, AdTech, OSINT..."
            value={form.domain}
            onChange={(event) => updateField("domain", event.target.value)}
          />
        </label>
        <label>
          Created By
          <input
            value={form.createdBy}
            onChange={(event) => updateField("createdBy", event.target.value)}
          />
        </label>

        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

        <div className="confirmation-actions">
          <button
            className="secondary-button"
            type="button"
            disabled={isStarting}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button className="primary-button" type="submit" disabled={isStarting}>
            {isStarting ? "Starting..." : "Start Session"}
          </button>
        </div>
      </form>
    </div>
  );
}
