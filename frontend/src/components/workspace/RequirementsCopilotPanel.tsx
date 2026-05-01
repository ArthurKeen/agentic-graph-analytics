"use client";

import { useEffect, useMemo, useState } from "react";
import type { RequirementInterview } from "@/lib/product-api/types";
import { FloatingDetailPanel } from "./FloatingDetailPanel";

interface RequirementsCopilotPanelProps {
  interview: RequirementInterview;
  stackIndex?: number;
  isSavingAnswer: boolean;
  isGeneratingDraft: boolean;
  errorMessage: string | null;
  onAnswerQuestion: (questionId: string, answer: string) => Promise<void>;
  onGenerateDraft: () => Promise<void>;
  onClose: () => void;
}

export function RequirementsCopilotPanel({
  interview,
  stackIndex = 0,
  isSavingAnswer,
  isGeneratingDraft,
  errorMessage,
  onAnswerQuestion,
  onGenerateDraft,
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

      <button
        className="primary-button"
        type="button"
        disabled={isGeneratingDraft}
        onClick={() => void onGenerateDraft()}
      >
        {isGeneratingDraft ? "Generating..." : "Generate Draft"}
      </button>
    </FloatingDetailPanel>
  );
}
