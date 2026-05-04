"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { RequirementInterview, RequirementVersion } from "@/lib/product-api/types";
import { FloatingDetailPanel } from "./FloatingDetailPanel";

interface RequirementsCopilotPanelProps {
  interview: RequirementInterview;
  stackIndex?: number;
  /** Becomes the question id while a Save Answer request is in flight, so
   * only that row shows "Saving…" instead of every Save button locking up.
   * Use the parent's existing `isSavingCopilotAnswer` boolean as a fallback
   * trigger when the parent hasn't propagated the per-question id (the panel
   * detects which row to highlight by comparing the user's last click). */
  isSavingAnswer: boolean;
  isGeneratingDraft: boolean;
  isApprovingDraft: boolean;
  errorMessage: string | null;
  approvedRequirementVersion: RequirementVersion | null;
  /** All RequirementVersions visible in this workspace, used to display the
   * next auto-assigned version number to the user before they approve. */
  existingRequirementVersions?: RequirementVersion[];
  onAnswerQuestion: (questionId: string, answer: string) => Promise<void>;
  onGenerateDraft: () => Promise<void>;
  /** Approve the draft. Pass `null` to let the backend auto-increment to
   * `max(existing.version) + 1`; an explicit number is only accepted by the
   * backend if it does not collide with an existing version. */
  onApproveDraft: (version: number | null) => Promise<void>;
  onClose: () => void;
}

export function RequirementsCopilotPanel({
  interview,
  stackIndex = 0,
  isSavingAnswer,
  isGeneratingDraft,
  isApprovingDraft,
  errorMessage,
  approvedRequirementVersion,
  existingRequirementVersions = [],
  onAnswerQuestion,
  onGenerateDraft,
  onApproveDraft,
  onClose
}: RequirementsCopilotPanelProps) {
  // Server truth: what's actually persisted in the interview right now. This
  // re-derives whenever the parent updates `interview` (e.g. after a save).
  const savedAnswers = useMemo(() => {
    return Object.fromEntries(
      interview.answers.map((answer) => [
        String(answer.question_id ?? ""),
        String(answer.answer ?? "")
      ])
    );
  }, [interview.answers]);
  // Local edits, seeded once from server state. We deliberately do NOT
  // re-sync this from `savedAnswers` on every prop change — doing so would
  // wipe in-flight edits in OTHER textareas every time one question saves.
  // After a save, dirty-state clears naturally because savedAnswers catches
  // up to draftAnswers for that one question.
  const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>(savedAnswers);
  // The id of the question whose Save button was last clicked. Combined with
  // `isSavingAnswer` this gives us per-row spinner/disabled state instead of
  // every Save button locking when one is in flight.
  const [savingQuestionId, setSavingQuestionId] = useState<string | null>(null);
  // Once the user has clicked Save (or the persisted state matches the
  // typed text), we show a "Saved" pill. We track explicit acknowledgement
  // separately from auto-detected match so the pill only appears for
  // questions the user has actually interacted with this session — pre-
  // populated answers from a Reopen flow shouldn't all read "Saved" before
  // the user has even looked at them.
  const [acknowledgedQuestionIds, setAcknowledgedQuestionIds] = useState<Set<string>>(
    () => new Set()
  );
  // The draft preview anchor, scrolled into view after a successful Generate
  // so the user actually sees the result instead of having to hunt for it.
  const draftRef = useRef<HTMLElement | null>(null);
  const previousDraftBrd = useRef<string | undefined>(interview.draftBrd ?? undefined);

  useEffect(() => {
    if (
      interview.draftBrd &&
      interview.draftBrd !== previousDraftBrd.current &&
      draftRef.current
    ) {
      draftRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    previousDraftBrd.current = interview.draftBrd ?? undefined;
  }, [interview.draftBrd]);

  const nextAutoVersion = useMemo(() => {
    const numbers = existingRequirementVersions.map((version) => version.version);
    return numbers.length > 0 ? Math.max(...numbers) + 1 : 1;
  }, [existingRequirementVersions]);
  const basedOnVersion =
    typeof interview.metadata === "object" && interview.metadata !== null
      ? (interview.metadata as Record<string, unknown>).based_on_version
      : undefined;

  // Once a version has been approved, lock all interactive controls — the
  // interview is sealed in the audit log and editing it further would be
  // confusing (the user's typing would silently NOT affect the approved v2).
  const isApproved = approvedRequirementVersion !== null;
  // Disable the Approve button when ANY question still has unsaved edits, to
  // avoid the user accidentally approving a draft that doesn't include their
  // most recent typing.
  const dirtyQuestionIds = useMemo(() => {
    return interview.questions
      .map((question, index) => String(question.id ?? `question-${index}`))
      .filter((qid) => (draftAnswers[qid] ?? "") !== (savedAnswers[qid] ?? ""));
  }, [draftAnswers, interview.questions, savedAnswers]);
  const hasUnsavedAnswers = dirtyQuestionIds.length > 0;

  async function handleSaveAnswer(questionId: string) {
    setSavingQuestionId(questionId);
    try {
      await onAnswerQuestion(questionId, draftAnswers[questionId] ?? "");
      setAcknowledgedQuestionIds((prev) => {
        const next = new Set(prev);
        next.add(questionId);
        return next;
      });
    } finally {
      setSavingQuestionId(null);
    }
  }

  return (
    <FloatingDetailPanel
      title="Requirements Copilot"
      stackIndex={stackIndex}
      onClose={onClose}
    >
      <p>Status: {interview.status}</p>
      <p>Domain: {interview.domain ?? "Not specified"}</p>
      {basedOnVersion ? (
        <p className="muted">
          Based on Requirements v{String(basedOnVersion)}; on approve this
          becomes v{nextAutoVersion} and v{String(basedOnVersion)} is marked
          superseded.
        </p>
      ) : nextAutoVersion > 1 ? (
        <p className="muted">
          On approve this becomes v{nextAutoVersion}. Any prior approved
          versions in this workspace will be marked superseded.
        </p>
      ) : null}

      <div className="copilot-question-list">
        {interview.questions.map((question, index) => {
          const questionId = String(question.id ?? `question-${index}`);
          const isThisRowSaving =
            savingQuestionId === questionId || (isSavingAnswer && savingQuestionId === questionId);
          const isDirty =
            (draftAnswers[questionId] ?? "") !== (savedAnswers[questionId] ?? "");
          const wasSaved = acknowledgedQuestionIds.has(questionId) && !isDirty;
          const status: "saving" | "unsaved" | "saved" | "untouched" = isThisRowSaving
            ? "saving"
            : isDirty
              ? "unsaved"
              : wasSaved
                ? "saved"
                : "untouched";
          return (
            <label key={questionId} className="copilot-question" data-status={status}>
              <span className="copilot-question-prompt">
                <span>{String(question.text ?? "Question")}</span>
                <CopilotSaveBadge status={status} />
              </span>
              <textarea
                value={draftAnswers[questionId] ?? ""}
                disabled={isApproved || isApprovingDraft}
                onChange={(event) => {
                  const next = event.target.value;
                  setDraftAnswers((current) => ({ ...current, [questionId]: next }));
                  // Editing always clears the "Saved" pill for this row so
                  // the user gets immediate feedback that there's pending
                  // work to save.
                  if (acknowledgedQuestionIds.has(questionId)) {
                    setAcknowledgedQuestionIds((prev) => {
                      const updated = new Set(prev);
                      updated.delete(questionId);
                      return updated;
                    });
                  }
                }}
              />
              <button
                className="secondary-button"
                type="button"
                disabled={isThisRowSaving || isApproved || isApprovingDraft || !isDirty}
                onClick={() => void handleSaveAnswer(questionId)}
              >
                {isThisRowSaving ? "Saving…" : isDirty ? "Save Answer" : "Saved"}
              </button>
            </label>
          );
        })}
      </div>

      {interview.draftBrd ? (
        <section className="copilot-draft-preview" ref={draftRef}>
          <h4>Draft BRD</h4>
          <pre>{interview.draftBrd}</pre>
        </section>
      ) : null}

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      {isApproved && approvedRequirementVersion ? (
        <div
          className="copilot-approval-success"
          role="status"
          aria-live="polite"
        >
          <p className="success-text">
            <strong>
              Approved as Requirements v{approvedRequirementVersion.version}
            </strong>
          </p>
          <p className="muted">
            The new version is now visible in the Assets panel; any prior
            approved version has been marked superseded.
          </p>
          <button className="primary-button" type="button" onClick={onClose}>
            Close
          </button>
        </div>
      ) : (
        <>
          <button
            className="primary-button"
            type="button"
            disabled={isGeneratingDraft || isApprovingDraft}
            onClick={() => void onGenerateDraft()}
          >
            {isGeneratingDraft
              ? "Generating…"
              : interview.draftBrd
                ? "Re-generate Draft"
                : "Generate Draft"}
          </button>

          {interview.draftBrd ? (
            <div className="copilot-approval">
              <span className="muted">
                {hasUnsavedAnswers
                  ? `${dirtyQuestionIds.length} unsaved answer${
                      dirtyQuestionIds.length === 1 ? "" : "s"
                    } — save before approving so v${nextAutoVersion} reflects them.`
                  : `Will be approved as Requirements v${nextAutoVersion}.`}
              </span>
              <button
                className="primary-button"
                type="button"
                disabled={isApprovingDraft || isGeneratingDraft || hasUnsavedAnswers}
                onClick={() => void onApproveDraft(null)}
              >
                {isApprovingDraft
                  ? "Approving…"
                  : `Approve as v${nextAutoVersion}`}
              </button>
            </div>
          ) : null}
        </>
      )}
    </FloatingDetailPanel>
  );
}

function CopilotSaveBadge({
  status
}: {
  status: "saving" | "unsaved" | "saved" | "untouched";
}) {
  if (status === "saving") {
    return (
      <span className="copilot-save-badge" data-state="saving">
        Saving…
      </span>
    );
  }
  if (status === "unsaved") {
    return (
      <span className="copilot-save-badge" data-state="unsaved">
        Unsaved
      </span>
    );
  }
  if (status === "saved") {
    return (
      <span className="copilot-save-badge" data-state="saved">
        Saved ✓
      </span>
    );
  }
  return null;
}
