"use client";

import { useState } from "react";

import type { ReportBundle, ReportExportFormat } from "@/lib/product-api/types";
import { MarkdownView } from "./MarkdownView";

interface DynamicReportCanvasProps {
  report: ReportBundle;
  /** Optional: when omitted (older callers, tests), the export buttons are
   * hidden so the canvas remains a pure data view. */
  onExport?: (format: ReportExportFormat) => Promise<void>;
}

export function DynamicReportCanvas({ report, onExport }: DynamicReportCanvasProps) {
  // Track which format is currently downloading so we can disable both
  // buttons together (avoids double-clicks issuing two downloads) and surface
  // a per-button "Exporting…" label without flashing the other button.
  const [exportingFormat, setExportingFormat] = useState<ReportExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async (format: ReportExportFormat) => {
    if (!onExport || exportingFormat) {
      return;
    }
    setExportingFormat(format);
    setExportError(null);
    try {
      await onExport(format);
    } catch (error) {
      setExportError(
        error instanceof Error ? error.message : "Failed to export report"
      );
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <section className="report-canvas" aria-label="Dynamic report">
      <header>
        <div>
          <p className="muted">Version {report.manifest.version}</p>
          <h3>{report.manifest.title}</h3>
        </div>
        <div className="report-canvas-header-actions">
          <span>{report.manifest.status}</span>
          {onExport ? (
            <div className="report-export-actions" role="group" aria-label="Export report">
              <button
                type="button"
                className="report-export-button"
                disabled={exportingFormat !== null}
                onClick={() => void handleExport("html")}
              >
                {exportingFormat === "html" ? "Exporting…" : "Export HTML"}
              </button>
              <button
                type="button"
                className="report-export-button"
                disabled={exportingFormat !== null}
                onClick={() => void handleExport("markdown")}
              >
                {exportingFormat === "markdown" ? "Exporting…" : "Export Markdown"}
              </button>
            </div>
          ) : null}
        </div>
      </header>
      {exportError ? (
        <p className="error-text" role="alert">
          {exportError}
        </p>
      ) : null}
      {report.manifest.summary ? <p>{report.manifest.summary}</p> : null}

      <div className="report-sections">
        {report.sections.map((section) => (
          <article key={section.sectionId} className="report-section">
            <p className="muted">{section.type}</p>
            <h4>{section.title}</h4>
            <ReportContent content={section.content} />
            {section.evidenceRefs.length > 0 ? (
              <p className="muted">{section.evidenceRefs.length} evidence reference(s)</p>
            ) : null}
          </article>
        ))}
      </div>

      {report.charts.length > 0 ? (
        <section className="report-chart-list" aria-label="Report charts">
          <h4>Charts</h4>
          {report.charts.map((chart) => (
            <article key={chart.chartId} className="report-chart">
              <header className="report-chart-header">
                <strong>{chart.title}</strong>
                <span>{chart.chartType}</span>
              </header>
              <ChartBody chart={chart} />
            </article>
          ))}
        </section>
      ) : null}
    </section>
  );
}

function ReportContent({ content }: { content: Record<string, unknown> }) {
  const text = content.text;
  if (typeof text === "string") {
    return <MarkdownView text={text} className="report-text" />;
  }

  return <pre>{JSON.stringify(content, null, 2)}</pre>;
}

const PLOTLY_CDN_URL = "https://cdn.plot.ly/plotly-2.35.2.min.js";

function ensurePlotlyRuntime(html: string): string {
  // The agent often emits Plotly fragments with `include_plotlyjs=False`,
  // i.e. inline `Plotly.newPlot(...)` calls but no <script> that loads
  // Plotly.js. Detect that case and inject the CDN runtime so the iframe
  // can actually render the chart.
  const hasPlotlyRuntime =
    /plotly[^"']*\.js/i.test(html) ||
    /cdn\.plot\.ly/i.test(html) ||
    /plotly\.min\.js/i.test(html);

  if (hasPlotlyRuntime) {
    return html;
  }

  const cdnTag = `<script src="${PLOTLY_CDN_URL}" charset="utf-8"></script>`;

  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/<head([^>]*)>/i, `<head$1>${cdnTag}`);
  }

  if (/<html[^>]*>/i.test(html)) {
    return html.replace(/<html([^>]*)>/i, `<html$1><head>${cdnTag}</head>`);
  }

  return `<!doctype html><html><head><meta charset="utf-8"/>${cdnTag}<style>body{margin:0;padding:8px;font-family:sans-serif;background:#fff;}</style></head><body>${html}</body></html>`;
}

function ChartBody({ chart }: { chart: ReportBundle["charts"][number] }) {
  const data = chart.data ?? {};
  const kind = typeof data.kind === "string" ? data.kind : undefined;
  const html = typeof data.html === "string" ? data.html : undefined;

  if (kind === "plotly_html" && html) {
    return (
      <iframe
        className="report-chart-frame"
        title={chart.title || "Plotly chart"}
        sandbox="allow-scripts allow-same-origin"
        srcDoc={ensurePlotlyRuntime(html)}
        loading="lazy"
      />
    );
  }

  return <pre>{JSON.stringify(data, null, 2)}</pre>;
}
