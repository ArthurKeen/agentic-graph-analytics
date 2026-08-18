"use client";

import type { ShardingProfile, WorkspaceAsset } from "@/lib/product-api/types";
import { DEPLOYMENT_LABELS } from "./GraphProfileCanvas";

interface CrossTenantRunConfirmationOverlayProps {
  asset: WorkspaceAsset;
  sharding: ShardingProfile;
  onCancel: () => void;
  onConfirm: () => void;
}

/**
 * FR-65: a run against a tenant-sharded deployment can silently mix tenants.
 * The detection is an inference from shard keys, not a policy the product can
 * enforce, so this warns and asks rather than blocking.
 */
export function CrossTenantRunConfirmationOverlay({
  asset,
  sharding,
  onCancel,
  onConfirm
}: CrossTenantRunConfirmationOverlayProps) {
  return (
    <div className="confirmation-backdrop" role="presentation">
      <section
        className="confirmation-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cross-tenant-title"
      >
        <h2 id="cross-tenant-title">Cross-Tenant Analysis</h2>
        <p>
          The connected deployment is sharded by{" "}
          <strong>{sharding.tenantKey ?? "a tenant key"}</strong>, which usually
          means each shard holds a different tenant&apos;s data. Running{" "}
          <strong>{asset.label}</strong> without scoping to one tenant will span{" "}
          {sharding.maxNumberOfShards > 1
            ? `all ${sharding.maxNumberOfShards} shards`
            : "every shard"}{" "}
          and may mix tenants in the results.
        </p>
        <dl className="detail-list">
          <div>
            <dt>Deployment</dt>
            <dd>
              {DEPLOYMENT_LABELS[sharding.deploymentKind] ??
                sharding.deploymentKind}
            </dd>
          </div>
          <div>
            <dt>Tenant key</dt>
            <dd>{sharding.tenantKey ?? "unknown"}</dd>
          </div>
          <div>
            <dt>Shard keys</dt>
            <dd>{sharding.shardKeys.join(", ") || "none reported"}</dd>
          </div>
        </dl>
        <p className="muted">
          To scope the run, add a tenant filter to the requirements before
          launching.
        </p>
        <div className="confirmation-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="primary-button" onClick={onConfirm}>
            Run Across All Tenants
          </button>
        </div>
      </section>
    </div>
  );
}
