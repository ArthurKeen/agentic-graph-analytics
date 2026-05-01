"use client";

import { useEffect, useMemo, useState } from "react";
import type { RequirementInterview, RequirementVersion } from "@/lib/product-api/types";
import { FloatingDetailPanel } from "./FloatingDetailPanel";

interface RequirementsCopilotPanelProps {
  interview: RequirementInterview;
  stackIndex?: number;
  isSavingAnswer: boolean;
  isGeneratingDraft: boolean;
  isApprovingDraft: boolean;
  errorMessage: string | null;
  approvedRequirementVersion: RequirementVersion | null;
  onAnswerQuestion: (questionId: string, answer: string) => Promise<void>;
  onGenerateDraft: () => Promise<void>;
  onApproveDraft: (version: number) => Promise<void>;
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
  onAnswerQuestion,
  onGenerateDraft,
  onApproveDraft,
  onClose
}: RequirementsCopilotPanelProps) {
  const answerMap = useMemo(() => {
    return Object.fromEntries(
      interview.answers.map((answer) => [
        String(answer.question_id ?? ""),
        String(answer.answer ?? "")
      ])
    );
  }, [interview.answers]);
  const [draftAnswers, setDraftAnswers] = useState<Record<string, string>>(answerMap);
  const [approvalVersion, setApprovalVersion] = useState(1);

  useEffect(() => {
    setDraftAnswers(answerMap);
  }, [answerMap]);

  return (
    <FloatingDetailPanel
      title="Requirements Copilot"
      stackIndex={stackIndex}
      onClose={onClose}
    >
      <p>Status: {interview.status}</p>
      <p>Domain: {interview.domain ?? "Not specified"}</p>

      <div className="copilot-question-list">
        {interview.questions.map((question, index) => {
          const questionId = String(question.id ?? `question-${index}`);
          return (
            <label key={questionId} className="copilot-question">
              <span>{String(question.text ?? "Question")}</span>
              <textarea
                value={draftAnswers[questionId] ?? ""}
                onChange={(event) =>
                  setDraftAnswers((current) => ({
                    ...current,
                    [questionId]: event.target.value
                  }))
                }
              />
              <button
                className="secondary-button"
                type="button"
                disabled={isSavingAnswer}
                onClick={() => onAnswerQuestion(questionId, draftAnswers[questionId] ?? "")}
              >
                {isSavingAnswer ? "Saving..." : "Save Answer"}
              </button>
            </label>
          );
        })}
      </div>

      {interview.draftBrd ? (
        <section className="copilot-draft-preview">
          <h4>Draft BRD</h4>
          <pre>{interview.draftBrd}</pre>
        </section>
      ) : null}

      {errorMessage ? <p className="error-text">{errorMessage}</p> : null}

      {approvedRequirementVersion ? (
        <p className="success-text">
          Approved as requirement version {approvedRequirementVersion.version}.
        </p>
      ) : null}

      <button
        className="primary-button"
        type="button"
        disabled={isGeneratingDraft}
        onClick={() => void onGenerateDraft()}
      >
        {isGeneratingDraft ? "Generating..." : "Generate Draft"}
      </button>

      {interview.draftBrd ? (
        <label className="copilot-approval">
          <span>Requirement version</span>
          <input
            type="number"
            min={1}
            value={approvalVersion}
            onChange={(event) => setApprovalVersion(Number(event.target.value))}
          />
          <button
            className="primary-button"
            type="button"
            disabled={isApprovingDraft || approvalVersion < 1}
            onClick={() => void onApproveDraft(approvalVersion)}
          >
            {isApprovingDraft ? "Approving..." : "Approve Draft"}
          </button>
        </label>
      ) : null}
    </FloatingDetailPanel>
  );
}
