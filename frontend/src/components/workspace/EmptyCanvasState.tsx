export function EmptyCanvasState() {
  return (
    <section className="empty-canvas" aria-label="Empty workspace canvas">
      <div>
        <h2>Select an object to begin</h2>
        <p className="muted">
          Pick a graph profile, run, document, or report from the explorer. Right-click
          the canvas for view and layout options.
        </p>
      </div>
    </section>
  );
}
