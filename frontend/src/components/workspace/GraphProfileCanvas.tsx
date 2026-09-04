"use client";

import type { GraphProfileSummary, ShardingProfile } from "@/lib/product-api/types";

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
          {graphProfile.shardingProfile ? (
            <ShardingBadge sharding={graphProfile.shardingProfile} />
          ) : null}
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

      {graphProfile.shardingProfile?.warnings.length ? (
        <p className="error-text" role="status">
          {graphProfile.shardingProfile.warnings.join(" ")}
        </p>
      ) : null}

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

      {graphProfile.shardingProfile ? (
        <ShardingCard sharding={graphProfile.shardingProfile} />
      ) : null}

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

export const DEPLOYMENT_LABELS: Record<string, string> = {
  single_server: "Single server",
  cluster: "Cluster",
  one_shard: "OneShard",
  unknown: "Sharding unknown"
};

function ShardingBadge({ sharding }: { sharding: ShardingProfile }) {
  const label = DEPLOYMENT_LABELS[sharding.deploymentKind] ?? sharding.deploymentKind;
  return (
    <span
      className={
        sharding.isMultitenant ? "sharding-badge is-multitenant" : "sharding-badge"
      }
      title={
        sharding.isMultitenant
          ? `Sharded by ${sharding.tenantKey} — analyses may span tenants`
          : "Deployment sharding profile"
      }
    >
      {label}
      {sharding.isMultitenant ? ` · multi-tenant (${sharding.tenantKey})` : ""}
    </span>
  );
}

function ShardingCard({ sharding }: { sharding: ShardingProfile }) {
  return (
    <section className="graph-profile-card">
      <h4>Sharding &amp; Tenancy</h4>
      <dl className="detail-list">
        <div>
          <dt>Deployment</dt>
          <dd>
            {DEPLOYMENT_LABELS[sharding.deploymentKind] ?? sharding.deploymentKind}
          </dd>
        </div>
        <div>
          <dt>Multi-tenant</dt>
          <dd>{sharding.isMultitenant ? `yes (${sharding.tenantKey})` : "no"}</dd>
        </div>
        <div>
          <dt>Max shards</dt>
          <dd>{sharding.maxNumberOfShards || "n/a"}</dd>
        </div>
        <div>
          <dt>Replication factor</dt>
          <dd>{sharding.minReplicationFactor ?? "n/a"}</dd>
        </div>
        {sharding.shardKeys.length > 0 ? (
          <div>
            <dt>Shard keys</dt>
            <dd>{sharding.shardKeys.join(", ")}</dd>
          </div>
        ) : null}
        {sharding.smartGraphAttributes.length > 0 ? (
          <div>
            <dt>SmartGraph attributes</dt>
            <dd>{sharding.smartGraphAttributes.join(", ")}</dd>
          </div>
        ) : null}
        {sharding.satelliteCollections.length > 0 ? (
          <div>
            <dt>Satellite collections</dt>
            <dd>{sharding.satelliteCollections.join(", ")}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
