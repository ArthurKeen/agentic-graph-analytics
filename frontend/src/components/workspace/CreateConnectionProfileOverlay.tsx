"use client";

import { useState, type FormEvent } from "react";
import type { CreateConnectionProfileInput } from "@/lib/product-api/types";

interface CreateConnectionProfileOverlayProps {
  isCreating: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: CreateConnectionProfileInput) => Promise<void>;
}

const deploymentModes = [
  { value: "local", label: "Local" },
  { value: "self_managed", label: "Self Managed" },
  { value: "arangograph", label: "ArangoGraph" },
  { value: "amp", label: "AMP" }
];

export function CreateConnectionProfileOverlay({
  isCreating,
  errorMessage,
  onCancel,
  onSubmit
}: CreateConnectionProfileOverlayProps) {
  const [form, setForm] = useState<CreateConnectionProfileInput>({
    name: "",
    deploymentMode: "local",
    endpoint: "http://localhost:8529",
    database: "",
    username: "",
    verifySsl: true,
    passwordSecretEnvVar: ""
  });

  const updateField = <K extends keyof CreateConnectionProfileInput>(
    key: K,
    value: CreateConnectionProfileInput[K]
  ) => setForm((current) => ({ ...current, [key]: value }));

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(form);
  }

  return (
    <div className="confirmation-backdrop" role="presentation" onClick={onCancel}>
      <form
        className="connection-profile-overlay"
        aria-label="Create connection profile"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <header>
          <div>
            <p className="muted">Workspace Setup</p>
            <h2>Create Connection Profile</h2>
          </div>
          <button
            className="secondary-button"
            type="button"
            disabled={isCreating}
            onClick={onCancel}
          >
            Close
          </button>
        </header>

        <p className="muted">
          Store connection metadata plus a password secret reference. Do not enter plaintext
          passwords here.
        </p>

        <label>
          Name
          <input
            required
            value={form.name}
            onChange={(event) => updateField("name", event.target.value)}
          />
        </label>
        <label>
          Deployment Mode
          <select
            value={form.deploymentMode}
            onChange={(event) => updateField("deploymentMode", event.target.value)}
          >
            {deploymentModes.map((mode) => (
              <option key={mode.value} value={mode.value}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Endpoint
          <input
            required
            value={form.endpoint}
            onChange={(event) => updateField("endpoint", event.target.value)}
          />
        </label>
        <label>
          Database
          <input
            required
            value={form.database}
            onChange={(event) => updateField("database", event.target.value)}
          />
        </label>
        <label>
          Username
          <input
            required
            value={form.username}
            onChange={(event) => updateField("username", event.target.value)}
          />
        </label>
        <label>
          Password Environment Variable
          <input
            placeholder="ARANGO_PASSWORD"
            value={form.passwordSecretEnvVar}
            onChange={(event) => updateField("passwordSecretEnvVar", event.target.value)}
          />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.verifySsl}
            onChange={(event) => updateField("verifySsl", event.target.checked)}
          />
          Verify SSL
        </label>

        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

        <div className="confirmation-actions">
          <button
            className="secondary-button"
            type="button"
            disabled={isCreating}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button className="primary-button" type="submit" disabled={isCreating}>
            {isCreating ? "Creating..." : "Create Profile"}
          </button>
        </div>
      </form>
    </div>
  );
}
