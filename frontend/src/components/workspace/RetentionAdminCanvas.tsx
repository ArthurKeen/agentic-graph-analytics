"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  RetentionPolicy,
  RetentionSweepResult,
  SetRetentionPolicyInput
} from "@/lib/product-api/types";

interface RetentionAdminCanvasProps {
  onLoad: () => Promise<RetentionPolicy>;
  onSave: (input: SetRetentionPolicyInput) => Promise<RetentionPolicy>;
  onApply: (dryRun?: boolean) => Promise<RetentionSweepResult>;
}

const WINDOWS: Array<{
  key: keyof SetRetentionPolicyInput;
  label: string;
  hint: string;
}> = [
  {
    key: "draftRetentionDays",
    label: "Drafts",
    hint: "Draft and rejected requirement versions. Approved ones are never removed."
  },
  {
    key: "runRetentionDays",
    label: "Runs",
    hint: "Workflow runs, including ephemeral Quick Analysis runs."
  },
  { key: "documentRetentionDays", label: "Documents", hint: "Uploaded source documents." },
  {
    key: "reportSnapshotRetentionDays",
    label: "Report snapshots",
    hint: "Reports without a published snapshot."
  },
  {
    key: "auditLogRetentionDays",
    label: "Audit logs",
    hint: "Only swept when set explicitly — audit events record every other deletion."
  }
];

const CATEGORY_LABELS: Record<string, string> = {
  drafts: "Drafts",
  runs: "Runs",
  documents: "Documents",
  report_snapshots: "Report snapshots",
  audit_logs: "Audit logs"
};

export function RetentionAdminCanvas({
  onLoad,
  onSave,
  onApply
}: RetentionAdminCanvasProps) {
  const [policy, setPolicy] = useState<RetentionPolicy | null>(null);
  const [draft, setDraft] = useState<SetRetentionPolicyInput>({});
  const [preview, setPreview] = useState<RetentionSweepResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  // Deleting is irreversible, so it needs a second, explicit confirmation
  // rather than being one click away from the preview.
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const load = useCallback(async () => {
    const loaded = await onLoad();
    setPolicy(loaded);
    setDraft({
      enabled: loaded.enabled,
      draftRetentionDays: loaded.draftRetentionDays,
      runRetentionDays: loaded.runRetentionDays,
      documentRetentionDays: loaded.documentRetentionDays,
      reportSnapshotRetentionDays: loaded.reportSnapshotRetentionDays,
      auditLogRetentionDays: loaded.auditLogRetentionDays
    });
  }, [onLoad]);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    load()
      .catch((error) => {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : "Failed to load retention policy"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [load]);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setErrorMessage(null);
    setMessage(null);
    setIsBusy(true);
    try {
      await action();
      setMessage(success);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Action failed");
    } finally {
      setIsBusy(false);
    }
  };

  if (isLoading) {
    return (
      <section className="canvas-surface" aria-label="Retention">
        <h3>Retention</h3>
        <p className="muted">Loading policy…</p>
      </section>
    );
  }

  const totalCandidates = preview
    ? Object.values(preview.counts).reduce((sum, count) => sum + count, 0)
    : 0;

  return (
    <section className="canvas-surface" aria-label="Retention">
      <h3>Retention</h3>
      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
      {message ? <p className="success-text">{message}</p> : null}

      <section className="connection-profile-card">
        <h4>Policy</h4>
        {!policy?.configured ? (
          <p className="muted">
            No policy configured — nothing is ever removed until you set one.
          </p>
        ) : null}

        <label className="retention-toggle">
          <input
            type="checkbox"
            checked={draft.enabled ?? false}
            onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
          />
          Retention enabled
        </label>

        <div className="catalog-filters">
          {WINDOWS.map((window) => (
            <label key={window.key} title={window.hint}>
              {window.label} (days)
              <input
                type="number"
                min={0}
                aria-label={`${window.label} retention days`}
                value={String(draft[window.key] ?? 0)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    [window.key]: Number(event.target.value)
                  })
                }
              />
            </label>
          ))}
        </div>
        <p className="muted">
          0 means keep forever. Approved requirement versions, published report
          snapshots, and runs behind a published report are never removed at any
          age.
        </p>

        <div className="confirmation-actions">
          <button
            type="button"
            className="primary-button"
            disabled={isBusy}
            onClick={() =>
              void run(async () => {
                const saved = await onSave(draft);
                setPolicy(saved);
                setPreview(null);
                setConfirmingDelete(false);
              }, "Retention policy saved.")
            }
          >
            Save Policy
          </button>
        </div>
      </section>

      <section className="connection-profile-card">
        <h4>Sweep</h4>
        <p className="muted">
          Preview first. Nothing is deleted until you confirm.
        </p>
        <div className="confirmation-actions">
          <button
            type="button"
            className="secondary-button"
            disabled={isBusy}
            onClick={() =>
              void run(async () => {
                const result = await onApply(true);
                setPreview(result);
                setConfirmingDelete(false);
              }, "Preview complete.")
            }
          >
            Preview Sweep (dry run)
          </button>
        </div>

        {preview ? (
          <>
            {preview.reason ? (
              <p className="muted">{preview.reason}</p>
            ) : (
              <>
                <p>
                  {totalCandidates === 0
                    ? "Nothing is currently eligible for removal."
                    : `${totalCandidates} record(s) eligible for removal:`}
                </p>
                {totalCandidates > 0 ? (
                  <ul className="copilot-question-list">
                    {Object.entries(preview.counts)
                      .filter(([, count]) => count > 0)
                      .map(([category, count]) => (
                        <li key={category}>
                          <strong>{CATEGORY_LABELS[category] ?? category}:</strong>{" "}
                          {count}
                          <br />
                          <span className="muted">
                            {(preview.candidates[category] ?? [])
                              .map((item) => item.label ?? item.id)
                              .join(", ")}
                          </span>
                        </li>
                      ))}
                  </ul>
                ) : null}
                {(preview.protected?.runs_with_published_reports?.length ?? 0) > 0 ? (
                  <p className="muted">
                    Protected from this sweep:{" "}
                    {preview.protected.runs_with_published_reports?.length} run(s)
                    behind a published report.
                  </p>
                ) : null}
              </>
            )}

            {totalCandidates > 0 && !preview.deleted ? (
              <div className="confirmation-actions">
                {confirmingDelete ? (
                  <>
                    <span className="error-text">
                      Permanently delete {totalCandidates} record(s)? This cannot be
                      undone.
                    </span>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => setConfirmingDelete(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="primary-button"
                      disabled={isBusy}
                      onClick={() =>
                        void run(async () => {
                          const result = await onApply(false);
                          setPreview(result);
                          setConfirmingDelete(false);
                          await load();
                        }, "Sweep applied.")
                      }
                    >
                      Yes, delete them
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => setConfirmingDelete(true)}
                  >
                    Apply Sweep…
                  </button>
                )}
              </div>
            ) : null}

            {preview.deleted ? (
              <p className="success-text">
                Removed {preview.removed ?? 0} record(s).
              </p>
            ) : null}
          </>
        ) : null}
      </section>
    </section>
  );
}
