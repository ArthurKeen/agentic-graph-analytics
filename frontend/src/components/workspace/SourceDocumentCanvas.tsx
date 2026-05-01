"use client";

import type { SourceDocumentSummary } from "@/lib/product-api/types";

interface SourceDocumentCanvasProps {
  document: SourceDocumentSummary;
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
        <h4>Extracted Text Preview</h4>
        {document.extractedText ? (
          <p>{document.extractedText}</p>
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
