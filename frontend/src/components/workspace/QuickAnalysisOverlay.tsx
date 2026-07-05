"use client";

import { useMemo, useState, type CSSProperties, type FormEvent } from "react";
import type {
  ConnectionProfileSummary,
  GraphProfileSummary,
  QuickAnalysisInput
} from "@/lib/product-api/types";

interface QuickAnalysisOverlayProps {
  graphProfiles: GraphProfileSummary[];
  connectionProfiles: ConnectionProfileSummary[];
  defaultGraphProfileId?: string | null;
  /** True when the workspace is showing demo data (no live Product API
   * workspace). Runs in this mode are simulated, not executed. */
  isDemo: boolean;
  isRunning: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: QuickAnalysisInput) => Promise<void>;
}

const EXAMPLE_PROMPT =
  "Which organizations are most central in the competitive network?";

const textareaStyle: CSSProperties = {
  width: "100%",
  minHeight: 110,
  resize: "vertical",
  border: "1px solid var(--aga-border)",
  borderRadius: 10,
  background: "var(--aga-bg)",
  color: "var(--aga-text)",
  padding: "10px 12px",
  font: "inherit"
};

/**
 * FR-73 Quick Analysis: a single natural-language prompt against a graph
 * profile runs the agentic pipeline once and produces a report — no manual
 * requirement / use-case / template approval. The run is created and started
 * in one call; the shell then opens its run DAG.
 *
 * Uses the `connection-profile-overlay` form layout (grid + stacked labels)
 * rather than `confirmation-overlay`, whose inline labels crowded the inputs.
 */
export function QuickAnalysisOverlay({
  graphProfiles,
  connectionProfiles,
  defaultGraphProfileId,
  isDemo,
  isRunning,
  errorMessage,
  onCancel,
  onSubmit
}: QuickAnalysisOverlayProps) {
  const initialGraphProfileId = useMemo(() => {
    if (
      defaultGraphProfileId &&
      graphProfiles.some((profile) => profile.graphProfileId === defaultGraphProfileId)
    ) {
      return defaultGraphProfileId;
    }
    return graphProfiles[0]?.graphProfileId ?? "";
  }, [defaultGraphProfileId, graphProfiles]);

  const [graphProfileId, setGraphProfileId] = useState(initialGraphProfileId);
  const [prompt, setPrompt] = useState("");
  const [workflowMode, setWorkflowMode] = useState("agentic");

  const selectedProfile = useMemo(
    () => graphProfiles.find((profile) => profile.graphProfileId === graphProfileId) ?? null,
    [graphProfiles, graphProfileId]
  );
  const selectedConnection = useMemo(
    () =>
      selectedProfile
        ? connectionProfiles.find(
            (connection) =>
              connection.connectionProfileId === selectedProfile.connectionProfileId
          ) ?? null
        : null,
    [connectionProfiles, selectedProfile]
  );

  const trimmedPrompt = prompt.trim();
  const hasGraph = Boolean(graphProfileId);
  const hasPrompt = trimmedPrompt.length > 0;
  const submitDisabled = isRunning || !hasGraph || !hasPrompt;

  const disabledReason = !hasGraph
    ? "Select a graph profile to run."
    : !hasPrompt
      ? "Enter a prompt to run."
      : null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitDisabled) {
      return;
    }
    await onSubmit({ graphProfileId, prompt: trimmedPrompt, workflowMode });
  }

  return (
    <div className="confirmation-backdrop" role="presentation" onClick={onCancel}>
      <form
        className="connection-profile-overlay"
        aria-label="Quick analysis"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <header>
          <div>
            <p className="muted">Run an analysis</p>
            <h2>Quick Analysis</h2>
          </div>
          <button
            className="secondary-button"
            type="button"
            disabled={isRunning}
            onClick={onCancel}
          >
            Close
          </button>
        </header>

        <p className="muted">
          Describe what you want to learn in plain English and pick a graph. The
          agent pipeline runs end to end and produces a report — no manual
          requirements, use cases, or templates to approve.
        </p>

        {isDemo ? (
          <p className="error-text" role="alert">
            Demo mode — no live database is connected, so this runs a simulated
            workflow (no real analysis). To run for real, create a workspace and
            connection profile, then discover a graph profile.
          </p>
        ) : null}

        <label>
          Graph profile
          <select
            value={graphProfileId}
            disabled={isRunning || graphProfiles.length === 0}
            onChange={(event) => setGraphProfileId(event.target.value)}
          >
            {graphProfiles.length === 0 ? (
              <option value="">No graph profiles in this workspace</option>
            ) : null}
            {graphProfiles.map((profile) => (
              <option key={profile.graphProfileId} value={profile.graphProfileId}>
                {profile.graphName === "default"
                  ? `${profile.graphName} (all collections)`
                  : profile.graphName}
              </option>
            ))}
          </select>
        </label>

        {selectedProfile ? (
          <p className="muted" aria-live="polite" style={{ margin: 0 }}>
            Runs against graph <strong>{selectedProfile.graphName}</strong> ·{" "}
            {selectedProfile.vertexCollections.length} vertex /{" "}
            {selectedProfile.edgeCollections.length} edge collections
            {selectedConnection ? (
              <>
                {" · database "}
                <code>{selectedConnection.database}</code>
              </>
            ) : null}
          </p>
        ) : null}

        <label>
          Prompt
          <textarea
            value={prompt}
            placeholder={`e.g. ${EXAMPLE_PROMPT}`}
            disabled={isRunning}
            rows={4}
            style={textareaStyle}
            onChange={(event) => setPrompt(event.target.value)}
          />
        </label>

        <label>
          Workflow mode
          <select
            value={workflowMode}
            disabled={isRunning}
            onChange={(event) => setWorkflowMode(event.target.value)}
          >
            <option value="agentic">Agentic</option>
            <option value="parallel_agentic">Parallel Agentic</option>
          </select>
        </label>

        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        {disabledReason ? <p className="muted" style={{ margin: 0 }}>{disabledReason}</p> : null}

        <div className="confirmation-actions">
          <button
            className="secondary-button"
            type="button"
            disabled={isRunning}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            className="primary-button"
            type="submit"
            disabled={submitDisabled}
            title={disabledReason ?? "Run the analysis"}
          >
            {isRunning ? "Starting..." : "Run analysis"}
          </button>
        </div>
      </form>
    </div>
  );
}
