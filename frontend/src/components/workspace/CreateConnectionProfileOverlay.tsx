"use client";

import { useState, type FormEvent } from "react";
import type {
  CreateConnectionProfileInput,
  ListClusterDatabasesInput
} from "@/lib/product-api/types";

interface CreateConnectionProfileOverlayProps {
  isCreating: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: CreateConnectionProfileInput) => Promise<void>;
  /** Two-step connect, part 1: enumerate databases on the cluster from the
   * supplied credentials so the user can pick one instead of typing it. */
  onListDatabases: (
    input: ListClusterDatabasesInput
  ) => Promise<{ endpoint: string; databases: string[] }>;
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
  onSubmit,
  onListDatabases
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
  const [databases, setDatabases] = useState<string[]>([]);
  const [isFinding, setIsFinding] = useState(false);
  const [findError, setFindError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const updateField = <K extends keyof CreateConnectionProfileInput>(
    key: K,
    value: CreateConnectionProfileInput[K]
  ) => setForm((current) => ({ ...current, [key]: value }));

  // Changing any credential invalidates a prior database search so the user
  // can't save a database picked against different credentials.
  const updateCredField = <K extends keyof CreateConnectionProfileInput>(
    key: K,
    value: CreateConnectionProfileInput[K]
  ) => {
    setForm((current) => ({
      ...current,
      [key]: value,
      // Changing credentials invalidates a prior database pick.
      ...(hasSearched ? { database: "" } : {})
    }));
    if (hasSearched) {
      setHasSearched(false);
      setDatabases([]);
    }
  };

  const canSearch =
    !isFinding &&
    form.endpoint.trim().length > 0 &&
    form.username.trim().length > 0 &&
    (form.passwordSecretEnvVar ?? "").trim().length > 0;

  async function handleFindDatabases() {
    setFindError(null);
    setIsFinding(true);
    try {
      const result = await onListDatabases({
        endpoint: form.endpoint.trim(),
        username: form.username.trim(),
        passwordSecretEnvVar: (form.passwordSecretEnvVar ?? "").trim(),
        verifySsl: form.verifySsl
      });
      setDatabases(result.databases);
      setHasSearched(true);
      // Auto-select the first database so the form is immediately submittable.
      if (result.databases.length > 0) {
        updateField("database", result.databases[0]);
      } else {
        updateField("database", "");
      }
    } catch (error) {
      setFindError(
        error instanceof Error ? error.message : "Failed to list databases"
      );
      setDatabases([]);
      setHasSearched(true);
    } finally {
      setIsFinding(false);
    }
  }

  const submitDisabled =
    isCreating || form.name.trim().length === 0 || form.database.trim().length === 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitDisabled) {
      return;
    }
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
            <p className="muted">Workspace Setup · Step 1: Cluster credentials</p>
            <h2>Connect to a Cluster</h2>
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
          Enter cluster credentials and click <strong>Find databases</strong> to
          list what&apos;s available, then pick a database. The password is
          referenced by environment-variable name — never entered in plaintext.
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
            onChange={(event) => updateCredField("endpoint", event.target.value)}
          />
        </label>
        <label>
          Username
          <input
            required
            value={form.username}
            onChange={(event) => updateCredField("username", event.target.value)}
          />
        </label>
        <label>
          Password Environment Variable
          <input
            placeholder="ARANGO_PASSWORD"
            value={form.passwordSecretEnvVar}
            onChange={(event) =>
              updateCredField("passwordSecretEnvVar", event.target.value)
            }
          />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.verifySsl}
            onChange={(event) => updateCredField("verifySsl", event.target.checked)}
          />
          Verify SSL
        </label>

        <div className="confirmation-actions" style={{ justifyContent: "flex-start" }}>
          <button
            className="secondary-button"
            type="button"
            disabled={!canSearch}
            title={canSearch ? "List databases on this cluster" : "Enter endpoint, username, and password env var first"}
            onClick={handleFindDatabases}
          >
            {isFinding ? "Finding..." : "Find databases"}
          </button>
        </div>
        {findError ? <p className="error-text">{findError}</p> : null}

        {/* Step 2: pick a database from the discovered list. */}
        {hasSearched ? (
          databases.length > 0 ? (
            <label>
              Database (Step 2)
              <select
                value={form.database}
                onChange={(event) => updateField("database", event.target.value)}
              >
                {databases.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <p className="muted">
              No databases visible to these credentials. Check the endpoint and
              that the account can list databases (root / <code>_system</code>).
            </p>
          )
        ) : null}

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
          <button
            className="primary-button"
            type="submit"
            disabled={submitDisabled}
            title={
              form.database.trim().length === 0
                ? "Find and select a database first"
                : "Save connection profile"
            }
          >
            {isCreating ? "Creating..." : "Create Profile"}
          </button>
        </div>
      </form>
    </div>
  );
}
