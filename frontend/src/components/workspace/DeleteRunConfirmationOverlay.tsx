"use client";

import type { WorkspaceAsset } from "@/lib/product-api/types";

interface DeleteRunConfirmationOverlayProps {
  run: WorkspaceAsset;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteRunConfirmationOverlay({
  run,
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
          Delete <strong>{run.label}</strong> from this workspace view? This is an
          irreversible run action in the product UI and must be confirmed here.
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
        <div className="confirmation-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="danger-button" onClick={onConfirm}>
            Delete Run
          </button>
        </div>
      </section>
    </div>
  );
}
