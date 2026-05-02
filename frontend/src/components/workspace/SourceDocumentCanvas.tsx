"use client";

import type { SourceDocumentSummary } from "@/lib/product-api/types";
import { MarkdownView } from "./MarkdownView";

interface SourceDocumentCanvasProps {
  document: SourceDocumentSummary;
}

function isMarkdown(doc: SourceDocumentSummary): boolean {
  const mime = (doc.mimeType ?? "").toLowerCase();
  if (mime.includes("markdown")) {
    return true;
  }
  return /\.(md|markdown)$/i.test(doc.filename ?? "");
}

export function SourceDocumentCanvas({ document }: SourceDocumentCanvasProps) {
  return (
    <section className="source-document-canvas" aria-label="Source document">
      <header>
        <div>
          <p className="muted">{document.mimeType}</p>
          <h3>{document.filename}</h3>
        </div>
        <span>{document.storageMode}</span>
      </header>

      <section className="source-document-card">
        <h4>Document Metadata</h4>
        <dl className="detail-list">
          <div>
            <dt>SHA-256</dt>
            <dd>{document.sha256 || "Not captured"}</dd>
          </div>
          <div>
            <dt>Uploaded</dt>
            <dd>{document.uploadedAt ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Storage URI</dt>
            <dd>{document.storageUri ?? "Inline or managed storage"}</dd>
          </div>
        </dl>
      </section>

      <section className="source-document-card">
        <h4>{isMarkdown(document) ? "Document" : "Extracted Text Preview"}</h4>
        {document.extractedText ? (
          isMarkdown(document) ? (
            <MarkdownView text={document.extractedText} />
          ) : (
            <p className="source-document-extracted">{document.extractedText}</p>
          )
        ) : (
          <p className="muted">No extracted text preview is available.</p>
        )}
      </section>

      <section className="source-document-card">
        <h4>Additional Metadata</h4>
        {Object.keys(document.metadata).length > 0 ? (
          <pre>{JSON.stringify(document.metadata, null, 2)}</pre>
        ) : (
          <p className="muted">No additional metadata has been recorded.</p>
        )}
      </section>
    </section>
  );
}
