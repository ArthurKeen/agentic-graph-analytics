"use client";

import { useState } from "react";
import type { UploadSourceDocumentInput } from "@/lib/product-api/types";

interface UploadSourceDocumentOverlayProps {
  isUploading: boolean;
  errorMessage: string | null;
  onCancel: () => void;
  onSubmit: (input: UploadSourceDocumentInput) => Promise<void>;
}

const ACCEPTED_SUFFIXES = [".md", ".markdown", ".pdf", ".docx", ".txt"];

export function UploadSourceDocumentOverlay({
  isUploading,
  errorMessage,
  onCancel,
  onSubmit
}: UploadSourceDocumentOverlayProps) {
  const [selected, setSelected] = useState<UploadSourceDocumentInput | null>(null);
  const [fileErrorMessage, setFileErrorMessage] = useState<string | null>(null);

  async function readFile(file: File) {
    setFileErrorMessage(null);
    const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_SUFFIXES.includes(suffix)) {
      setSelected(null);
      setFileErrorMessage(
        `Unsupported file type "${suffix}". Supported: ${ACCEPTED_SUFFIXES.join(", ")}`
      );
      return;
    }

    try {
      setSelected({
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        contentBase64: await readAsBase64(file)
      });
    } catch (error) {
      setSelected(null);
      setFileErrorMessage(
        error instanceof Error ? error.message : "Failed to read the selected file"
      );
    }
  }

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section className="confirmation-overlay" aria-label="Upload source document">
        <h3>Upload Source Document</h3>
        <p className="muted">
          Markdown, PDF, DOCX, or plain text. Only the extracted text is stored —
          the original file is never persisted.
        </p>
        <input
          type="file"
          accept={ACCEPTED_SUFFIXES.join(",")}
          disabled={isUploading}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void readFile(file);
            }
          }}
        />
        {selected ? (
          <p className="success-text">Ready to upload {selected.filename}.</p>
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
            disabled={!selected || isUploading}
            onClick={() => (selected ? void onSubmit(selected) : undefined)}
          >
            {isUploading ? "Uploading..." : "Upload Document"}
          </button>
        </div>
      </section>
    </div>
  );
}

function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read the selected file"));
    reader.onload = () => {
      const result = String(reader.result ?? "");
      // readAsDataURL yields "data:<mime>;base64,<payload>" — the API wants
      // only the payload.
      const separator = result.indexOf(",");
      resolve(separator >= 0 ? result.slice(separator + 1) : result);
    };
    reader.readAsDataURL(file);
  });
}
