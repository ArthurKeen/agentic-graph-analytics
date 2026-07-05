"use client";

import type {
  ConnectionProfileSummary,
  ConnectionVerificationResult
} from "@/lib/product-api/types";

interface ConnectionProfileCanvasProps {
  connectionProfile: ConnectionProfileSummary;
  verificationResult: ConnectionVerificationResult | null;
  isVerifying: boolean;
  isDiscovering: boolean;
  verificationErrorMessage: string | null;
  onVerify: (connectionProfileId: string) => void;
  onDiscoverGraph: (connectionProfileId: string) => void;
}

export function ConnectionProfileCanvas({
  connectionProfile,
  verificationResult,
  isVerifying,
  isDiscovering,
  verificationErrorMessage,
  onVerify,
  onDiscoverGraph
}: ConnectionProfileCanvasProps) {
  const secretRefKeys = Object.keys(connectionProfile.secretRefs);

  return (
    <section className="connection-profile-canvas" aria-label="Connection profile">
      <header>
        <div>
          <p className="muted">{connectionProfile.deploymentMode}</p>
          <h3>{connectionProfile.name}</h3>
        </div>
        <span>{connectionProfile.lastVerificationStatus}</span>
      </header>

      <section className="connection-profile-card">
        <div className="connection-profile-card-header">
          <h4>Connection Details</h4>
          <button
            className="primary-button"
            type="button"
            disabled={isVerifying}
            onClick={() => onVerify(connectionProfile.connectionProfileId)}
          >
            {isVerifying ? "Verifying..." : "Verify Connection"}
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={isDiscovering}
            onClick={() => onDiscoverGraph(connectionProfile.connectionProfileId)}
          >
            {isDiscovering ? "Discovering..." : "Discover Graph"}
          </button>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Endpoint</dt>
            <dd>{connectionProfile.endpoint}</dd>
          </div>
          <div>
            <dt>Database</dt>
            <dd>{connectionProfile.database}</dd>
          </div>
          <div>
            <dt>Username</dt>
            <dd>{connectionProfile.username}</dd>
          </div>
          <div>
            <dt>Verify SSL</dt>
            <dd>{connectionProfile.verifySsl ? "Yes" : "No"}</dd>
          </div>
        </dl>
      </section>

      <section className="connection-profile-card">
        <h4>Credential References</h4>
        {secretRefKeys.length > 0 ? (
          <ul>
            {secretRefKeys.map((key) => (
              <li key={key}>
                {key}: {connectionProfile.secretRefs[key].kind}/
                {connectionProfile.secretRefs[key].ref}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No credential references have been configured.</p>
        )}
      </section>

      <section className="connection-profile-card">
        <h4>Verification</h4>
        <dl className="detail-list">
          <div>
            <dt>Status</dt>
            <dd>{verificationResult?.status ?? connectionProfile.lastVerificationStatus}</dd>
          </div>
          <div>
            <dt>Last Verified</dt>
            <dd>{verificationResult?.verifiedAt ?? connectionProfile.lastVerifiedAt ?? "Never"}</dd>
          </div>
          <div>
            <dt>Message</dt>
            <dd>
              {verificationErrorMessage ??
                verificationResult?.errorMessage ??
                "No verification message."}
            </dd>
          </div>
        </dl>
      </section>
    </section>
  );
}
