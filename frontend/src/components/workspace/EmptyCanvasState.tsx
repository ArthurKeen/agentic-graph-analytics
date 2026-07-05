export function EmptyCanvasState() {
  return (
    <section className="empty-canvas" aria-label="Getting started">
      <div className="empty-canvas-guide">
        <h2>Getting started</h2>
        <p className="muted">
          Follow these steps using the panel on the left, then pick an
          analysis mode.
        </p>
        <ol className="empty-canvas-steps">
          <li>
            <strong>Connect to a database.</strong> Left panel →{" "}
            <em>Connect to Database</em>: enter cluster credentials, click{" "}
            <em>Find databases</em>, and choose one.
          </li>
          <li>
            <strong>Pick a graph.</strong> After connecting you&apos;ll be
            prompted to select a named graph in that database (or the whole
            database). This creates a graph profile.
          </li>
          <li>
            <strong>Analyze.</strong> Choose a mode:
            <ul>
              <li>
                <strong>Quick</strong> — one prompt → one report, no setup.
              </li>
              <li>
                <strong>Guided</strong> — a short Copilot interview → focused
                analysis.
              </li>
              <li>
                <strong>Detailed</strong> — full requirements → many use cases
                &amp; reports.
              </li>
            </ul>
          </li>
        </ol>
        <p className="muted">
          Already set up? Pick a graph profile, run, document, or report from
          the explorer. Right-click the canvas for view and layout options.
        </p>
      </div>
    </section>
  );
}
