"use client";

import type { ReportBundle } from "@/lib/product-api/types";

interface DynamicReportCanvasProps {
  report: ReportBundle;
}

export function DynamicReportCanvas({ report }: DynamicReportCanvasProps) {
  return (
    <section className="report-canvas" aria-label="Dynamic report">
      <header>
        <div>
          <p className="muted">Version {report.manifest.version}</p>
          <h3>{report.manifest.title}</h3>
        </div>
        <span>{report.manifest.status}</span>
      </header>
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
              <strong>{chart.title}</strong>
              <span>{chart.chartType}</span>
              <pre>{JSON.stringify(chart.data, null, 2)}</pre>
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
    return <p>{text}</p>;
  }

  return <pre>{JSON.stringify(content, null, 2)}</pre>;
}
