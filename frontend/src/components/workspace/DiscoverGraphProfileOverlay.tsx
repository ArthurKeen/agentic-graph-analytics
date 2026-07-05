"use client";

import { useEffect, useState, type FormEvent } from "react";
import type {
  ConnectionGraphSummary,
  ConnectionGraphsResult,
  DiscoverGraphProfileInput,
  WorkspaceAsset
} from "@/lib/product-api/types";

interface DiscoverGraphProfileOverlayProps {
  connectionProfile: WorkspaceAsset;
  isDiscovering: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: DiscoverGraphProfileInput) => Promise<void>;
  onLoadGraphs?: (
    connectionProfileId: string
  ) => Promise<ConnectionGraphsResult>;
}

const CUSTOM_GRAPH_VALUE = "__custom__";

export function DiscoverGraphProfileOverlay({
  connectionProfile,
  isDiscovering,
  errorMessage,
  onCancel,
  onSubmit,
  onLoadGraphs
}: DiscoverGraphProfileOverlayProps) {
  const [form, setForm] = useState<DiscoverGraphProfileInput>({
    graphName: "",
    sampleSize: 100,
    maxSamplesPerCollection: 3,
    verifySystem: true
  });
  const [graphs, setGraphs] = useState<ConnectionGraphSummary[] | null>(null);
  const [isLoadingGraphs, setIsLoadingGraphs] = useState(false);
  const [graphsError, setGraphsError] = useState<string | null>(null);
  const [graphSelection, setGraphSelection] = useState<string>("");

  useEffect(() => {
    if (!onLoadGraphs) {
      return;
    }
    let cancelled = false;
    setIsLoadingGraphs(true);
    setGraphsError(null);
    onLoadGraphs(connectionProfile.id)
      .then((result) => {
        if (cancelled) {
          return;
        }
        const visible = result.graphs.filter((graph) => !graph.isSystem);
        setGraphs(visible);
        if (visible.length > 0) {
          const first = visible[0];
          setGraphSelection(first.name);
          setForm((current) => ({ ...current, graphName: first.name }));
        }
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setGraphsError(
          error instanceof Error ? error.message : "Failed to enumerate graphs"
        );
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingGraphs(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [connectionProfile.id, onLoadGraphs]);

  const updateField = <K extends keyof DiscoverGraphProfileInput>(
    key: K,
    value: DiscoverGraphProfileInput[K]
  ) => setForm((current) => ({ ...current, [key]: value }));

  function handleGraphSelectionChange(value: string) {
    setGraphSelection(value);
    if (value === CUSTOM_GRAPH_VALUE || value === "") {
      updateField("graphName", "");
    } else {
      updateField("graphName", value);
    }
  }

  const selectedGraph =
    graphs?.find((graph) => graph.name === graphSelection) ?? null;
  const isCustomSelection = graphSelection === CUSTOM_GRAPH_VALUE;
  const showDropdown = Boolean(onLoadGraphs);
  const hasGraphs = (graphs?.length ?? 0) > 0;

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
          Discover schema metadata from {connectionProfile.label}. Pick the named graph
          to scope analysis to its vertex and edge collections.
        </p>

        {showDropdown ? (
          <label>
            Named Graph
            {isLoadingGraphs ? (
              <span className="muted">Loading graphs...</span>
            ) : graphsError ? (
              <span className="error-text">{graphsError}</span>
            ) : hasGraphs ? (
              <select
                value={graphSelection}
                onChange={(event) => handleGraphSelectionChange(event.target.value)}
              >
                {graphs?.map((graph) => (
                  <option key={graph.name} value={graph.name}>
                    {graph.name}
                    {graph.vertexCount !== null && graph.vertexCount !== undefined
                      ? ` — ${graph.vertexCount.toLocaleString()} vertices`
                      : ""}
                    {graph.edgeCount !== null && graph.edgeCount !== undefined
                      ? `, ${graph.edgeCount.toLocaleString()} edges`
                      : ""}
                  </option>
                ))}
                <option value={CUSTOM_GRAPH_VALUE}>Custom (enter manually)</option>
              </select>
            ) : (
              <span className="muted">
                No named graphs found in this database. Enter one manually below.
              </span>
            )}
          </label>
        ) : null}

        {graphs && graphs.length > 1 ? (
          <p className="muted" role="note">
            This database contains {graphs.length} named graphs. The graph profile will
            be scoped to <strong>{form.graphName || graphSelection || "(none)"}</strong>{" "}
            only.
          </p>
        ) : null}

        {selectedGraph ? (
          <p className="muted">
            <strong>{selectedGraph.name}</strong> — {selectedGraph.vertexCollections.length}{" "}
            vertex / {selectedGraph.edgeCollections.length} edge collections.
          </p>
        ) : null}

        {(!showDropdown || isCustomSelection || (!hasGraphs && !isLoadingGraphs)) ? (
          <label>
            Graph Name
            <input
              placeholder="Optional graph name"
              value={form.graphName}
              onChange={(event) => updateField("graphName", event.target.value)}
            />
          </label>
        ) : null}
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
