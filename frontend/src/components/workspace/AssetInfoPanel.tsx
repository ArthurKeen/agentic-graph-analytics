"use client";

import type { WorkspaceAsset } from "@/lib/product-api/types";
import { FloatingDetailPanel } from "./FloatingDetailPanel";

interface AssetInfoPanelProps {
  asset: WorkspaceAsset;
  onClose: () => void;
}

const assetKindLabels: Record<WorkspaceAsset["kind"], string> = {
  "connection-profile": "Connection Profile",
  document: "Document",
  "graph-profile": "Graph Profile",
  report: "Report",
  run: "Run"
};

export function AssetInfoPanel({ asset, onClose }: AssetInfoPanelProps) {
  return (
    <FloatingDetailPanel
      title={`${assetKindLabels[asset.kind]} Info`}
      placement="viewportTopRight"
      onClose={onClose}
    >
      <dl className="detail-list">
        <div>
          <dt>Name</dt>
          <dd>{asset.label}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{assetKindLabels[asset.kind]}</dd>
        </div>
        <div>
          <dt>ID</dt>
          <dd>{asset.id}</dd>
        </div>
        <div>
          <dt>Description</dt>
          <dd>{asset.description ?? "No description available."}</dd>
        </div>
      </dl>
    </FloatingDetailPanel>
  );
}
