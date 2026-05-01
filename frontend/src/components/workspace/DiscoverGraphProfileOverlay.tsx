"use client";

import { useState, type FormEvent } from "react";
import type { DiscoverGraphProfileInput, WorkspaceAsset } from "@/lib/product-api/types";

interface DiscoverGraphProfileOverlayProps {
  connectionProfile: WorkspaceAsset;
  isDiscovering: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: DiscoverGraphProfileInput) => Promise<void>;
}

export function DiscoverGraphProfileOverlay({
  connectionProfile,
  isDiscovering,
  errorMessage,
  onCancel,
  onSubmit
}: DiscoverGraphProfileOverlayProps) {
  const [form, setForm] = useState<DiscoverGraphProfileInput>({
    graphName: "",
    sampleSize: 100,
    maxSamplesPerCollection: 3,
    verifySystem: true
  });

  const updateField = <K extends keyof DiscoverGraphProfileInput>(
    key: K,
    value: DiscoverGraphProfileInput[K]
  ) => setForm((current) => ({ ...current, [key]: value }));

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(form);
  }

  return (
    <div className="confirmation-backdrop" role="presentation" onClick={onCancel}>
      <form
        className="connection-profile-overlay"
        aria-label="Discover graph profile"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <header>
          <div>
            <p className="muted">Connection Profile</p>
            <h2>Discover Graph Profile</h2>
          </div>
          <button
            className="secondary-button"
            type="button"
            disabled={isDiscovering}
            onClick={onCancel}
          >
            Close
          </button>
        </header>

        <p className="muted">
          Discover schema metadata from {connectionProfile.label}. Leave graph name blank to use
          the backend-selected graph.
        </p>

        <label>
          Graph Name
          <input
            placeholder="Optional graph name"
            value={form.graphName}
            onChange={(event) => updateField("graphName", event.target.value)}
          />
        </label>
        <label>
          Sample Size
          <input
            min={1}
            type="number"
            value={form.sampleSize}
            onChange={(event) => updateField("sampleSize", Number(event.target.value))}
          />
        </label>
        <label>
          Max Samples Per Collection
          <input
            min={1}
            type="number"
            value={form.maxSamplesPerCollection}
            onChange={(event) =>
              updateField("maxSamplesPerCollection", Number(event.target.value))
            }
          />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.verifySystem}
            onChange={(event) => updateField("verifySystem", event.target.checked)}
          />
          Verify system database access first
        </label>

        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

        <div className="confirmation-actions">
          <button
            className="secondary-button"
            type="button"
            disabled={isDiscovering}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button className="primary-button" type="submit" disabled={isDiscovering}>
            {isDiscovering ? "Discovering..." : "Discover Graph"}
          </button>
        </div>
      </form>
    </div>
  );
}
