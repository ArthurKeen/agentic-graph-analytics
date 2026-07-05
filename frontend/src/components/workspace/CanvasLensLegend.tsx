interface CanvasLensLegendProps {
  lensName: string;
}

export function CanvasLensLegend({ lensName }: CanvasLensLegendProps) {
  return (
    <aside className="legend" aria-label={`${lensName} legend`}>
      <h3>{lensName} Legend</h3>
      <ul>
        <li>Node color shows workflow status: lime running, green completed, red failed.</li>
        <li>Node border uses the same status color so color is not the only signal.</li>
        <li>Node size is structural and stable; it does not change when the lens changes.</li>
        <li>Edges show declared step dependencies. Heavier edges are reserved for critical-path data.</li>
      </ul>
    </aside>
  );
}
