"use client";

import type { WorkspaceAsset } from "@/lib/product-api/types";

interface PublishReportConfirmationOverlayProps {
  report: WorkspaceAsset;
  onCancel: () => void;
  onConfirm: () => void;
}

export function PublishReportConfirmationOverlay({
  report,
  onCancel,
  onConfirm
}: PublishReportConfirmationOverlayProps) {
  return (
    <div className="confirmation-backdrop" role="presentation">
      <section
        className="confirmation-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="publish-report-title"
      >
        <h2 id="publish-report-title">Publish Report</h2>
        <p>
          Publish <strong>{report.label}</strong> as the current report snapshot?
          Published reports become reviewable artifacts for the workspace.
        </p>
        <dl className="detail-list">
          <div>
            <dt>Report ID</dt>
            <dd>{report.id}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{report.description ?? "No description available."}</dd>
          </div>
        </dl>
        <div className="confirmation-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="primary-button" onClick={onConfirm}>
            Publish Report
          </button>
        </div>
      </section>
    </div>
  );
}
