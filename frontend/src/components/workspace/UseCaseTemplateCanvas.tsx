"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  AnalysisCatalogView,
  AnalysisTemplate,
  CreateAnalysisTemplateInput,
  CreateUseCaseInput,
  UseCase,
  UseCaseStatus
} from "@/lib/product-api/types";

interface UseCaseTemplateCanvasProps {
  onBrowse: () => Promise<AnalysisCatalogView>;
  onCreateUseCase: (input: CreateUseCaseInput) => Promise<UseCase>;
  onSetUseCaseStatus: (
    useCaseId: string,
    status: UseCaseStatus,
    reviewNote?: string
  ) => Promise<UseCase>;
  onSetUseCasePriority: (useCaseId: string, priority: string) => Promise<UseCase>;
  onCreateTemplate: (input: CreateAnalysisTemplateInput) => Promise<AnalysisTemplate>;
  onUpdateTemplate: (
    analysisTemplateId: string,
    patch: { parameters?: Record<string, unknown> }
  ) => Promise<AnalysisTemplate>;
  onApproveTemplate: (analysisTemplateId: string) => Promise<AnalysisTemplate>;
  onGetTemplateVersions: (analysisTemplateId: string) => Promise<AnalysisTemplate[]>;
  onImportTemplates: (
    templates: Array<Record<string, unknown>>
  ) => Promise<AnalysisTemplate[]>;
}

const USE_CASE_TYPES = [
  "centrality",
  "community",
  "pathfinding",
  "pattern",
  "anomaly",
  "recommendation",
  "similarity"
];
const PRIORITIES = ["critical", "high", "medium", "low"];

export function UseCaseTemplateCanvas({
  onBrowse,
  onCreateUseCase,
  onSetUseCaseStatus,
  onSetUseCasePriority,
  onCreateTemplate,
  onUpdateTemplate,
  onApproveTemplate,
  onGetTemplateVersions,
  onImportTemplates
}: UseCaseTemplateCanvasProps) {
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [templates, setTemplates] = useState<AnalysisTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [newUseCase, setNewUseCase] = useState<CreateUseCaseInput>({
    title: "",
    description: "",
    useCaseType: "pattern",
    priority: "medium"
  });
  const [newTemplate, setNewTemplate] = useState<CreateAnalysisTemplateInput>({
    name: "",
    algorithm: ""
  });
  const [paramDrafts, setParamDrafts] = useState<Record<string, string>>({});
  const [versionsFor, setVersionsFor] = useState<{
    id: string;
    versions: AnalysisTemplate[];
  } | null>(null);

  const refresh = useCallback(async () => {
    const view = await onBrowse();
    setUseCases(view.useCases);
    setTemplates(view.templates);
  }, [onBrowse]);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    refresh()
      .catch((error) => {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : "Failed to load use cases"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  /** Every mutation refreshes from the server rather than patching local
   * state: FR-25 means an edit can *create a different row* (a new version),
   * so optimistic local patching would show the wrong record. */
  const run = async (action: () => Promise<unknown>, successMessage: string) => {
    setErrorMessage(null);
    setMessage(null);
    try {
      await action();
      await refresh();
      setMessage(successMessage);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Action failed");
    }
  };

  const templatesByUseCase = useMemo(() => {
    const map: Record<string, AnalysisTemplate[]> = {};
    for (const template of templates) {
      const key = template.useCaseId ?? "";
      (map[key] ??= []).push(template);
    }
    return map;
  }, [templates]);

  if (isLoading) {
    return (
      <section className="canvas-surface" aria-label="Use Cases and Templates">
        <h3>Use Cases &amp; Templates</h3>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  return (
    <section className="canvas-surface" aria-label="Use Cases and Templates">
      <h3>Use Cases &amp; Templates</h3>
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      {message ? <p className="success-text">{message}</p> : null}

      <section className="connection-profile-card">
        <h4>New Use Case</h4>
        <div className="catalog-filters">
          <label>
            Title
            <input
              type="text"
              value={newUseCase.title}
              placeholder="Find fraud rings"
              onChange={(event) =>
                setNewUseCase({ ...newUseCase, title: event.target.value })
              }
            />
          </label>
          <label>
            Type
            <select
              value={newUseCase.useCaseType}
              onChange={(event) =>
                setNewUseCase({ ...newUseCase, useCaseType: event.target.value })
              }
            >
              {USE_CASE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Priority
            <select
              value={newUseCase.priority}
              onChange={(event) =>
                setNewUseCase({ ...newUseCase, priority: event.target.value })
              }
            >
              {PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="primary-button"
            disabled={!newUseCase.title.trim()}
            onClick={() =>
              void run(
                () => onCreateUseCase(newUseCase),
                `Created use case "${newUseCase.title}".`
              ).then(() =>
                setNewUseCase({
                  title: "",
                  description: "",
                  useCaseType: "pattern",
                  priority: "medium"
                })
              )
            }
          >
            Add Use Case
          </button>
        </div>
      </section>

      <section className="connection-profile-card">
        <h4>Use Cases ({useCases.length})</h4>
        {useCases.length === 0 ? (
          <p className="muted">No use cases yet.</p>
        ) : (
          <div className="catalog-table-scroll">
            <table className="catalog-table">
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Type</th>
                  <th scope="col">Priority</th>
                  <th scope="col">Status</th>
                  <th scope="col">Origin</th>
                  <th scope="col">Review</th>
                </tr>
              </thead>
              <tbody>
                {useCases.map((useCase) => (
                  <tr key={useCase.useCaseId}>
                    <td>
                      <strong>{useCase.title}</strong>
                      {useCase.description ? (
                        <>
                          <br />
                          <span className="muted">{useCase.description}</span>
                        </>
                      ) : null}
                      {templatesByUseCase[useCase.useCaseId]?.length ? (
                        <>
                          <br />
                          <span className="muted">
                            {templatesByUseCase[useCase.useCaseId].length} template(s)
                          </span>
                        </>
                      ) : null}
                    </td>
                    <td>{useCase.useCaseType}</td>
                    <td>
                      <select
                        aria-label={`Priority for ${useCase.title}`}
                        value={useCase.priority}
                        // Archived rows are terminal server-side; disabling
                        // here avoids offering an action that must 409.
                        disabled={useCase.status === "archived"}
                        onChange={(event) =>
                          void run(
                            () =>
                              onSetUseCasePriority(
                                useCase.useCaseId,
                                event.target.value
                              ),
                            `Priority updated to ${event.target.value}.`
                          )
                        }
                      >
                        {PRIORITIES.map((priority) => (
                          <option key={priority} value={priority}>
                            {priority}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td data-status={useCase.status}>{useCase.status}</td>
                    <td>{useCase.origin}</td>
                    <td>
                      {useCase.status === "archived" ? (
                        <span className="muted">archived (terminal)</span>
                      ) : (
                        <div className="catalog-row-actions">
                          {useCase.status !== "approved" ? (
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={() =>
                                void run(
                                  () =>
                                    onSetUseCaseStatus(useCase.useCaseId, "approved"),
                                  `Approved "${useCase.title}".`
                                )
                              }
                            >
                              Approve
                            </button>
                          ) : null}
                          {useCase.status !== "rejected" ? (
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={() =>
                                void run(
                                  () =>
                                    onSetUseCaseStatus(useCase.useCaseId, "rejected"),
                                  `Rejected "${useCase.title}".`
                                )
                              }
                            >
                              Reject
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() =>
                              void run(
                                () => onSetUseCaseStatus(useCase.useCaseId, "archived"),
                                `Archived "${useCase.title}".`
                              )
                            }
                          >
                            Archive
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="connection-profile-card">
        <h4>Analysis Templates ({templates.length})</h4>
        <div className="catalog-filters">
          <label>
            Name
            <input
              type="text"
              value={newTemplate.name}
              placeholder="PageRank on Person"
              onChange={(event) =>
                setNewTemplate({ ...newTemplate, name: event.target.value })
              }
            />
          </label>
          <label>
            Algorithm
            <input
              type="text"
              value={newTemplate.algorithm}
              placeholder="pagerank"
              onChange={(event) =>
                setNewTemplate({ ...newTemplate, algorithm: event.target.value })
              }
            />
          </label>
          <button
            type="button"
            className="primary-button"
            disabled={!newTemplate.name.trim() || !newTemplate.algorithm.trim()}
            onClick={() =>
              void run(
                () => onCreateTemplate(newTemplate),
                `Created template "${newTemplate.name}".`
              ).then(() => setNewTemplate({ name: "", algorithm: "" }))
            }
          >
            Add Template
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = "application/json,.json";
              input.onchange = async () => {
                const file = input.files?.[0];
                if (!file) return;
                try {
                  const parsed = JSON.parse(await file.text());
                  const list = Array.isArray(parsed)
                    ? parsed
                    : (parsed.templates as Array<Record<string, unknown>>) ?? [];
                  await run(
                    () => onImportTemplates(list),
                    `Imported ${list.length} template(s) as drafts.`
                  );
                } catch (error) {
                  setErrorMessage(
                    error instanceof Error ? error.message : "Failed to read file"
                  );
                }
              };
              input.click();
            }}
          >
            Import Dictionary
          </button>
        </div>

        {templates.length === 0 ? (
          <p className="muted">No templates yet.</p>
        ) : (
          <div className="catalog-table-scroll">
            <table className="catalog-table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Algorithm</th>
                  <th scope="col">Version</th>
                  <th scope="col">Status</th>
                  <th scope="col">Parameters</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((template) => {
                  const draftKey = template.analysisTemplateId;
                  const draftValue =
                    paramDrafts[draftKey] ??
                    JSON.stringify(template.parameters, null, 0);
                  return (
                    <tr key={template.analysisTemplateId}>
                      <td>
                        <strong>{template.name}</strong>
                        {template.description ? (
                          <>
                            <br />
                            <span className="muted">{template.description}</span>
                          </>
                        ) : null}
                      </td>
                      <td>{template.algorithm}</td>
                      <td>v{template.version}</td>
                      <td data-status={template.status}>{template.status}</td>
                      <td>
                        <textarea
                          aria-label={`Parameters for ${template.name}`}
                          className="template-params"
                          rows={2}
                          value={draftValue}
                          onChange={(event) =>
                            setParamDrafts({
                              ...paramDrafts,
                              [draftKey]: event.target.value
                            })
                          }
                        />
                      </td>
                      <td>
                        <div className="catalog-row-actions">
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() => {
                              let parsed: Record<string, unknown>;
                              try {
                                parsed = JSON.parse(draftValue || "{}");
                              } catch {
                                setErrorMessage("Parameters must be valid JSON.");
                                return;
                              }
                              void run(
                                () =>
                                  onUpdateTemplate(template.analysisTemplateId, {
                                    parameters: parsed
                                  }),
                                template.status === "approved"
                                  ? // FR-25: editing an approved template
                                    // creates the next version rather than
                                    // mutating the executed configuration.
                                    `Saved as v${template.version + 1} (approved templates are immutable).`
                                  : "Parameters saved."
                              ).then(() => {
                                const next = { ...paramDrafts };
                                delete next[draftKey];
                                setParamDrafts(next);
                              });
                            }}
                          >
                            Save Params
                          </button>
                          {template.status === "draft" ? (
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={() =>
                                void run(
                                  () =>
                                    onApproveTemplate(template.analysisTemplateId),
                                  `Approved "${template.name}" v${template.version}.`
                                )
                              }
                            >
                              Approve
                            </button>
                          ) : null}
                          <button
                            type="button"
                            className="secondary-button"
                            onClick={() =>
                              void onGetTemplateVersions(template.analysisTemplateId)
                                .then((versions) =>
                                  setVersionsFor({
                                    id: template.analysisTemplateId,
                                    versions
                                  })
                                )
                                .catch((error) =>
                                  setErrorMessage(
                                    error instanceof Error
                                      ? error.message
                                      : "Failed to load versions"
                                  )
                                )
                            }
                          >
                            History
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {versionsFor ? (
          <section className="connection-profile-card">
            <h4>Version History</h4>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setVersionsFor(null)}
            >
              Close history
            </button>
            <ul className="copilot-question-list">
              {versionsFor.versions.map((version) => (
                <li key={version.analysisTemplateId}>
                  <strong>v{version.version}</strong> — {version.status}
                  {version.approvedBy ? ` · approved by ${version.approvedBy}` : ""}
                  <br />
                  <span className="muted">
                    {JSON.stringify(version.parameters)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </section>
    </section>
  );
}
