"use client";

import { useState, type FormEvent } from "react";
import type { StartRequirementsCopilotInput, WorkspaceAsset } from "@/lib/product-api/types";

interface StartRequirementsCopilotOverlayProps {
  graphProfile: WorkspaceAsset;
  isStarting: boolean;
  errorMessage: string | null;
  /** When set, the new interview is pre-populated from this prior version,
   * the new approval will be `priorVersion + 1`, and the prior version will
   * be flipped to SUPERSEDED on approve. The overlay also surfaces a
   * confirmation banner so the user knows v1 won't be lost in place. */
  basedOnVersion?: { requirementVersionId: string; version: number } | null;
  /** Pre-fill the Domain field. Caller supplies the best-known value:
   * prior version's metadata.domain when reopening, else a workspace-derived
   * fallback (e.g. derived from customer_name / tags). The user can still
   * edit it before submitting. */
  defaultDomain?: string;
  onCancel: () => void;
  onSubmit: (input: StartRequirementsCopilotInput) => Promise<void>;
}

export function StartRequirementsCopilotOverlay({
  graphProfile,
  isStarting,
  errorMessage,
  basedOnVersion = null,
  defaultDomain = "",
  onCancel,
  onSubmit
}: StartRequirementsCopilotOverlayProps) {
  const [form, setForm] = useState<StartRequirementsCopilotInput>({
    domain: defaultDomain,
    createdBy: "workspace-ui",
    basedOnVersionId: basedOnVersion?.requirementVersionId
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
            <h2>
              {basedOnVersion
                ? `Reopen Requirements Copilot (v${basedOnVersion.version} → v${basedOnVersion.version + 1})`
                : "Start Requirements Copilot"}
            </h2>
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

        {basedOnVersion ? (
          <p className="warning-text">
            Your existing Requirements v{basedOnVersion.version} answers will be
            pre-filled into this interview. On approve, a new
            Requirements v{basedOnVersion.version + 1} is created and
            v{basedOnVersion.version} is automatically marked
            <strong> superseded</strong> (kept for history; it is not deleted).
          </p>
        ) : (
          <p className="muted">
            Start a schema-aware interview for {graphProfile.label}. The copilot will use
            discovered collections and graph metadata to generate starter questions.
          </p>
        )}

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
