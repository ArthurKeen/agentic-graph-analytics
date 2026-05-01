"use client";

import type { GraphProfileSummary } from "@/lib/product-api/types";

interface GraphProfileCanvasProps {
  graphProfile: GraphProfileSummary;
  isStartingRequirementsCopilot: boolean;
  onStartRequirementsCopilot: (graphProfileId: string) => void;
}

export function GraphProfileCanvas({
  graphProfile,
  isStartingRequirementsCopilot,
  onStartRequirementsCopilot
}: GraphProfileCanvasProps) {
  return (
    <section className="graph-profile-canvas" aria-label="Graph profile">
      <header>
        <div>
          <p className="muted">Version {graphProfile.version}</p>
          <h3>{graphProfile.graphName}</h3>
        </div>
        <div className="graph-profile-header-actions">
          <span>{graphProfile.status}</span>
          <button
            className="primary-button"
            type="button"
            disabled={isStartingRequirementsCopilot}
            onClick={() => onStartRequirementsCopilot(graphProfile.graphProfileId)}
          >
            {isStartingRequirementsCopilot ? "Starting..." : "Start Requirements Copilot"}
          </button>
        </div>
      </header>

      <div className="graph-profile-grid">
        <CollectionList
          title="Vertex Collections"
          collections={graphProfile.vertexCollections}
        />
        <CollectionList
          title="Edge Collections"
          collections={graphProfile.edgeCollections}
        />
      </div>

      <section className="graph-profile-card">
        <h4>Counts</h4>
        {Object.keys(graphProfile.counts).length > 0 ? (
          <dl className="detail-list">
            {Object.entries(graphProfile.counts).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="muted">No collection counts have been captured yet.</p>
        )}
      </section>

      <section className="graph-profile-card">
        <h4>Edge Definitions</h4>
        {graphProfile.edgeDefinitions.length > 0 ? (
          <pre>{JSON.stringify(graphProfile.edgeDefinitions, null, 2)}</pre>
        ) : (
          <p className="muted">No edge definitions available.</p>
        )}
      </section>
    </section>
  );
}

function CollectionList({
  title,
  collections
}: {
  title: string;
  collections: string[];
}) {
  return (
    <section className="graph-profile-card">
      <h4>{title}</h4>
      {collections.length > 0 ? (
        <ul>
          {collections.map((collection) => (
            <li key={collection}>{collection}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">No collections discovered.</p>
      )}
    </section>
  );
}
