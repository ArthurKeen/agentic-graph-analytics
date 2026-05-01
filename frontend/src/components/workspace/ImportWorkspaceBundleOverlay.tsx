"use client";

import { useState } from "react";
import type { WorkspaceBundle } from "@/lib/product-api/types";

interface ImportWorkspaceBundleOverlayProps {
  isImporting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (bundle: WorkspaceBundle) => Promise<void>;
}

export function ImportWorkspaceBundleOverlay({
  isImporting,
  errorMessage,
  onCancel,
  onSubmit
}: ImportWorkspaceBundleOverlayProps) {
  const [bundle, setBundle] = useState<WorkspaceBundle | null>(null);
  const [fileErrorMessage, setFileErrorMessage] = useState<string | null>(null);

  async function readBundle(file: File) {
    setFileErrorMessage(null);
    try {
      const parsed = normalizeWorkspaceBundle(JSON.parse(await file.text()));
      if (!parsed.schemaVersion || !parsed.workspace) {
        throw new Error("Selected file is not an agentic graph analytics workspace bundle.");
      }
      setBundle(parsed);
    } catch (error) {
      setBundle(null);
      setFileErrorMessage(
        error instanceof Error ? error.message : "Failed to parse workspace bundle"
      );
    }
  }

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Import workspace bundle">
        <h3>Import Workspace Bundle</h3>
        <p className="muted">
          Select an exported workspace metadata bundle. Secret references are imported as
          references; secret values are not expected in the bundle.
        </p>
        <input
          type="file"
          accept="application/json,.json"
          disabled={isImporting}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void readBundle(file);
            }
          }}
        />
        {bundle ? (
          <p className="success-text">
            Ready to import {String(bundle.workspace.workspace_id ?? bundle.workspace._key)}.
          </p>
        ) : null}
        {fileErrorMessage ? <p className="error-text">{fileErrorMessage}</p> : null}
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        <div className="confirmation-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="primary-button"
            type="button"
            disabled={!bundle || isImporting}
            onClick={() => (bundle ? void onSubmit(bundle) : undefined)}
          >
            {isImporting ? "Importing..." : "Import Bundle"}
          </button>
        </div>
      </section>
    </div>
  );
}

function normalizeWorkspaceBundle(value: unknown): WorkspaceBundle {
  const raw = value as Record<string, unknown>;
  return {
    schemaVersion: String(raw.schemaVersion ?? raw.schema_version ?? ""),
    workspace: asRecord(raw.workspace),
    connectionProfiles: asRecordArray(raw.connectionProfiles ?? raw.connection_profiles),
    graphProfiles: asRecordArray(raw.graphProfiles ?? raw.graph_profiles),
    sourceDocuments: asRecordArray(raw.sourceDocuments ?? raw.source_documents),
    requirementInterviews: asRecordArray(
      raw.requirementInterviews ?? raw.requirement_interviews
    ),
    requirementVersions: asRecordArray(raw.requirementVersions ?? raw.requirement_versions),
    workflowRuns: asRecordArray(raw.workflowRuns ?? raw.workflow_runs),
    reports: asRecordArray(raw.reports),
    auditEvents: asRecordArray(raw.auditEvents ?? raw.audit_events)
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? { ...(value as object) } : {};
}

function asRecordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.map(asRecord) : [];
}
