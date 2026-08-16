"use client";

import { useEffect, useMemo, useState } from "react";
import type {
  AnalysisCatalogView,
  AnalysisExecution,
  AnalysisExecutionComparison,
  AnalysisExecutionFilters,
  AnalysisLineage
} from "@/lib/product-api/types";

interface AnalysisCatalogCanvasProps {
  /** FR-45 */
  onBrowse: () => Promise<AnalysisCatalogView>;
  /** FR-46 */
  onSearch: (filters: AnalysisExecutionFilters) => Promise<AnalysisExecution[]>;
  /** FR-48 */
  onCompare: (ids: string[]) => Promise<AnalysisExecutionComparison>;
  /** FR-47 */
  onLineage: (id: string) => Promise<AnalysisLineage>;
}

const EMPTY_FILTERS: AnalysisExecutionFilters = {};

export function AnalysisCatalogCanvas({
  onBrowse,
  onSearch,
  onCompare,
  onLineage
}: AnalysisCatalogCanvasProps) {
  const [catalog, setCatalog] = useState<AnalysisCatalogView | null>(null);
  const [executions, setExecutions] = useState<AnalysisExecution[]>([]);
  const [filters, setFilters] = useState<AnalysisExecutionFilters>(EMPTY_FILTERS);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<AnalysisExecutionComparison | null>(null);
  const [lineage, setLineage] = useState<AnalysisLineage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    onBrowse()
      .then((view) => {
        if (cancelled) return;
        setCatalog(view);
        setExecutions(view.executions);
        setErrorMessage(null);
      })
      .catch((error) => {
        if (cancelled) return;
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to load the analysis catalog"
        );
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [onBrowse]);

  // Filter option values come from the catalog rather than a hard-coded list,
  // so they always reflect what this workspace actually ran.
  const algorithms = useMemo(
    () => Array.from(new Set((catalog?.executions ?? []).map((e) => e.algorithm))).sort(),
    [catalog]
  );
  const statuses = useMemo(
    () => Array.from(new Set((catalog?.executions ?? []).map((e) => e.status))).sort(),
    [catalog]
  );

  const applyFilters = (next: AnalysisExecutionFilters) => {
    setFilters(next);
    setErrorMessage(null);
    onSearch(next)
      .then(setExecutions)
      .catch((error) =>
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to search executions"
        )
      );
  };

  const toggleSelected = (id: string) => {
    setComparison(null);
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    );
  };

  const runComparison = () => {
    setErrorMessage(null);
    onCompare(selectedIds)
      .then(setComparison)
      .catch((error) =>
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to compare executions"
        )
      );
  };

  const showLineage = (id: string) => {
    setErrorMessage(null);
    onLineage(id)
      .then(setLineage)
      .catch((error) =>
        setErrorMessage(
          error instanceof Error ? error.message : "Failed to load lineage"
        )
      );
  };

  const epochNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const epoch of catalog?.epochs ?? []) {
      map[epoch.analysisEpochId] = epoch.name;
    }
    return map;
  }, [catalog]);

  if (isLoading) {
    return (
      <section className="canvas-surface" aria-label="Analysis Catalog">
        <h3>Analysis Catalog</h3>
        <p className="muted">Loading analyses…</p>
      </section>
    );
  }

  const hasAnyExecutions = (catalog?.executions.length ?? 0) > 0;

  return (
    <section className="canvas-surface" aria-label="Analysis Catalog">
      <h3>Analysis Catalog</h3>
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      {!hasAnyExecutions ? (
        <p className="muted">
          No analyses have been recorded yet. Completed workflow runs are added here
          automatically.
        </p>
      ) : (
        <>
          <section className="connection-profile-card">
            <h4>Epochs ({catalog?.epochs.length ?? 0})</h4>
            {catalog && catalog.epochs.length > 0 ? (
              <ul className="copilot-question-list">
                {catalog.epochs.map((epoch) => (
                  <li key={epoch.analysisEpochId}>
                    <strong>{epoch.name}</strong> — {epoch.status} ·{" "}
                    {epoch.analysisCount} analysis
                    {epoch.analysisCount === 1 ? "" : "es"}
                    {epoch.description ? ` · ${epoch.description}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No epochs defined.</p>
            )}
          </section>

          <section className="connection-profile-card">
            <h4>Executions</h4>
            <div className="catalog-filters">
              <label>
                Algorithm
                <select
                  value={filters.algorithm ?? ""}
                  onChange={(event) =>
                    applyFilters({
                      ...filters,
                      algorithm: event.target.value || undefined
                    })
                  }
                >
                  <option value="">All</option>
                  {algorithms.map((algorithm) => (
                    <option key={algorithm} value={algorithm}>
                      {algorithm}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Status
                <select
                  value={filters.status ?? ""}
                  onChange={(event) =>
                    applyFilters({ ...filters, status: event.target.value || undefined })
                  }
                >
                  <option value="">All</option>
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Epoch
                <select
                  value={filters.epochId ?? ""}
                  onChange={(event) =>
                    applyFilters({ ...filters, epochId: event.target.value || undefined })
                  }
                >
                  <option value="">All</option>
                  {(catalog?.epochs ?? []).map((epoch) => (
                    <option key={epoch.analysisEpochId} value={epoch.analysisEpochId}>
                      {epoch.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Started after
                <input
                  type="date"
                  value={(filters.startedAfter ?? "").slice(0, 10)}
                  onChange={(event) =>
                    applyFilters({
                      ...filters,
                      // The API compares ISO timestamps, so widen a bare date
                      // to the start of that day.
                      startedAfter: event.target.value
                        ? `${event.target.value}T00:00:00+00:00`
                        : undefined
                    })
                  }
                />
              </label>
              <button
                type="button"
                className="secondary-button"
                onClick={() => applyFilters(EMPTY_FILTERS)}
              >
                Clear filters
              </button>
            </div>

            {executions.length === 0 ? (
              <p className="muted">No executions match these filters.</p>
            ) : (
              <div className="catalog-table-scroll">
                <table className="catalog-table">
                  <thead>
                    <tr>
                      <th scope="col">Compare</th>
                      <th scope="col">Algorithm</th>
                      <th scope="col">Status</th>
                      <th scope="col">Epoch</th>
                      <th scope="col">Results</th>
                      <th scope="col">Started</th>
                      <th scope="col">Lineage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {executions.map((execution) => (
                      <tr key={execution.analysisExecutionId}>
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Select ${execution.algorithm} for comparison`}
                            checked={selectedIds.includes(execution.analysisExecutionId)}
                            onChange={() =>
                              toggleSelected(execution.analysisExecutionId)
                            }
                          />
                        </td>
                        <td>
                          <strong>{execution.algorithm}</strong>
                          {execution.templateName ? (
                            <>
                              <br />
                              <span className="muted">{execution.templateName}</span>
                            </>
                          ) : null}
                        </td>
                        <td data-status={execution.status}>
                          {execution.status}
                          {execution.errorMessage ? (
                            <>
                              <br />
                              <span className="muted">{execution.errorMessage}</span>
                            </>
                          ) : null}
                        </td>
                        <td>
                          {execution.epochId
                            ? epochNameById[execution.epochId] ?? execution.epochId
                            : "—"}
                        </td>
                        <td>{execution.resultCount.toLocaleString()}</td>
                        <td>{execution.startedAt ?? "—"}</td>
                        <td>
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => showLineage(execution.analysisExecutionId)}
                          >
                            Trace
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="confirmation-actions">
              <button
                type="button"
                className="primary-button"
                // Comparison is relative to the first selection, so it needs
                // at least two executions to say anything.
                disabled={selectedIds.length < 2}
                onClick={runComparison}
              >
                Compare selected ({selectedIds.length})
              </button>
            </div>
          </section>

          {comparison ? (
            <section className="connection-profile-card">
              <h4>Comparison</h4>
              <p className="muted">
                Deltas are relative to the first selected execution (
                {comparison.baselineExecutionId}).
              </p>
              <div className="catalog-table-scroll">
                <table className="catalog-table">
                  <thead>
                    <tr>
                      <th scope="col">Execution</th>
                      <th scope="col">Δ Results</th>
                      <th scope="col">Δ Performance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.deltas.map((delta) => {
                      const execution = comparison.executions.find(
                        (item) =>
                          item.analysisExecutionId === delta.analysisExecutionId
                      );
                      const isBaseline =
                        delta.analysisExecutionId === comparison.baselineExecutionId;
                      return (
                        <tr key={delta.analysisExecutionId}>
                          <td>
                            {execution?.algorithm ?? delta.analysisExecutionId}
                            {isBaseline ? (
                              <span className="muted"> (baseline)</span>
                            ) : null}
                          </td>
                          <td>{formatDelta(delta.resultCount)}</td>
                          <td>
                            {Object.keys(delta.performanceMetrics).length === 0
                              ? "—"
                              : Object.entries(delta.performanceMetrics)
                                  .map(([key, value]) => `${key}: ${formatDelta(value)}`)
                                  .join(", ")}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {lineage ? (
            <section className="connection-profile-card">
              <h4>Lineage</h4>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setLineage(null)}
              >
                Close lineage
              </button>
              <ol className="copilot-question-list">
                <li>
                  <strong>Reports:</strong>{" "}
                  {lineage.reports.length > 0
                    ? `${lineage.reports.length} linked`
                    : "None linked"}
                </li>
                <li>
                  <strong>Execution:</strong>{" "}
                  {lineage.execution
                    ? `${lineage.execution.algorithm} (${lineage.execution.status})`
                    : "—"}
                </li>
                <li>
                  <strong>Template:</strong> {lineage.templateId ?? "—"}
                </li>
                <li>
                  <strong>Use case:</strong> {lineage.useCaseId ?? "—"}
                </li>
                <li>
                  <strong>Requirement version:</strong>{" "}
                  {lineage.requirementVersionId ?? "—"}
                </li>
              </ol>
              <p className="muted">
                Template and use case are IDs until their product entities ship
                (FR-19..FR-26).
              </p>
            </section>
          ) : null}
        </>
      )}
    </section>
  );
}

function formatDelta(value: number): string {
  if (value === 0) return "0";
  return value > 0 ? `+${value.toLocaleString()}` : value.toLocaleString();
}
