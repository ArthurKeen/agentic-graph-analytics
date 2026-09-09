"use client";

import type { WorkspaceAsset } from "@/lib/product-api/types";

interface DeleteRunConfirmationOverlayProps {
  run: WorkspaceAsset;
  isDeleting: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteRunConfirmationOverlay({
  run,
  isDeleting,
  errorMessage,
  onCancel,
  onConfirm
}: DeleteRunConfirmationOverlayProps) {
  return (
    <div className="confirmation-backdrop" role="presentation">
      <section
        className="confirmation-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-run-title"
      >
        <h2 id="delete-run-title">Delete Run</h2>
        <p>
          Permanently delete <strong>{run.label}</strong>? This removes the run
          and the reports and executions it produced. It cannot be undone.
        </p>
        <p className="muted">
          Reports and executions exist because of this run, so they go with it.
          If any of its reports has been published, the delete is refused —
          published reports are never removed.
        </p>
        <dl className="detail-list">
          <div>
            <dt>Run ID</dt>
            <dd>{run.id}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{run.description ?? "No description available."}</dd>
          </div>
        </dl>
        {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
        <div className="confirmation-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={isDeleting}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={isDeleting}
            onClick={onConfirm}
          >
            {isDeleting ? "Deleting..." : "Delete Run"}
          </button>
        </div>
      </section>
    </div>
  );
}
