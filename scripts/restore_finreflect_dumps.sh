#!/usr/bin/env bash
# Restore the FinReflectKG arangodumps into prod.demo via the `domyn-migrate`
# tools container.
#
# WHY A JWT (the important part):
#   prod.demo.pilot.arango.ai sits behind the ArangoDB Platform's Envoy gateway
#   (see the x-arango-platform-request-id / x-envoy-upstream-service-time response
#   headers). That gateway REJECTS the client tools' username+password login
#   exchange -- every scheme (http+ssl://, http+tcp://, ssl://, https://, on both
#   :443 and :8529) fails with "Could not connect to endpoint ... cannot create
#   server connection: forbidden", from any arangodb client image. Plain REST with
#   the same credentials works fine, which is the tell.
#   Passing a pre-obtained bearer JWT via --server.jwt-token skips that broken
#   login step and the tools connect normally. The JWT comes from POST /_open/auth.
#
# WHY STAGED:
#   These JWTs expire after 1 hour (server session-timeout). `relations` is ~672 MB
#   compressed / 17.5M edges, so one long invocation risks the token expiring
#   mid-restore. Each stage below fetches a fresh token, so every stage starts with
#   a full hour.
#
# OTHER FLAGS:
#   --include-system-collections true
#       Brings across `_graphs` (the named graph definitions) plus the Graph
#       Visualizer assets (_graphThemeStore, _canvasActions, _viewpoints,
#       _viewpointQueries, _viewpointActions, _editor_saved_queries). Without it
#       you get collections but no named graph, which the agentic runner needs.
#   --collection <name> (repeated)
#       `--collection` is include-ONLY; there is no --exclude-collection. Skipping
#       `chunks` (1.4M source-text docs, deliberately outside the named graph)
#       therefore means naming every other collection explicitly.
#   --replication-factor 1
#       The dumped collections declare replicationFactor 2 with
#       distributeShardsLike=_graphs, but both target databases were created with
#       replicationFactor 1. Pinning to 1 matches the target.
#
# Usage:
#   ./scripts/restore_finreflect_dumps.sh                       # both databases
#   ./scripts/restore_finreflect_dumps.sh FinReflectKgOneShard   # just one
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENDPOINT="${ARANGO_ENDPOINT_TOOLS:-http+ssl://prod.demo.pilot.arango.ai:443}"
CONTAINER="${CONTAINER:-domyn-migrate}"
THREADS="${THREADS:-8}"
PY="${PY:-$REPO/.venv/bin/python}"

# Fetch a fresh user JWT over plain REST (the path the gateway does allow).
get_jwt() {
  "$PY" - <<'PY'
import json, urllib.request, os
from dotenv import dotenv_values
repo = os.environ["REPO"]
v = dotenv_values(f"{repo}/.env")
body = json.dumps({"username": v["ARANGO_USER"], "password": v["ARANGO_PASSWORD"]}).encode()
req = urllib.request.Request(v["ARANGO_ENDPOINT"].rstrip("/") + "/_open/auth",
                             data=body, headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req, timeout=30))["jwt"], end="")
PY
}

# restore_stage <db> <label> <collection>...
FAILED_STAGES=()

# restore_stage <db> <label> <collection>...
#
# A stage failure is RECORDED and execution CONTINUES. The first run of this
# script died on `set -e` when a transient DNS fault killed the `relations`
# stage at 80% -- which also skipped every later stage, including the named
# graph, for no good reason: those stages are independent. Failures are
# reported together at the end for individual retry, and a partially-loaded
# `relations` is repaired in place by scripts/resume_finreflect_edges.py
# rather than reloaded from zero (arangorestore --overwrite truncates first).
restore_stage() {
  local db="$1" label="$2"; shift 2
  local -a args=()
  for c in "$@"; do args+=( --collection "$c" ); done

  local jwt; jwt="$(REPO="$REPO" get_jwt)"
  echo
  echo "--- [$db] stage: $label ($# collection(s)) ---"
  local start=$SECONDS
  local rc=0
  docker exec "$CONTAINER" arangorestore \
    --server.endpoint "$ENDPOINT" \
    --server.database "$db" \
    --server.jwt-token "$jwt" \
    --input-directory "/data/domyn/2026/$db" \
    --include-system-collections true \
    --replication-factor 1 \
    --overwrite true \
    --threads "$THREADS" \
    --progress true \
    "${args[@]}" || rc=$?

  if (( rc != 0 )); then
    echo "--- [$db] $label FAILED (rc=$rc) after $(( SECONDS - start ))s; continuing ---"
    FAILED_STAGES+=( "$db/$label" )
  else
    echo "--- [$db] $label done in $(( SECONDS - start ))s ---"
  fi
}

SYSTEM_COLLECTIONS=(
  _graphs _analyzers _appbundles _apps _aqlfunctions
  _canvasActions _editor_saved_queries _frontend _graphThemeStore
  _jobs _queries _queues
  _viewpointActions _viewpointQueries _viewpoints
)

restore_db() {
  local db="$1"
  echo "==================================================================="
  echo "restoring $db  (chunks excluded)"
  echo "==================================================================="
  # Data first, so the named graph definition lands on collections that exist.
  restore_stage "$db" "Node (vertices)" Node
  restore_stage "$db" "relations (edges)" relations
  if [[ "$db" == "FinReflectKgTemporal" ]]; then
    restore_stage "$db" "precomputed pagerank" gae_pr_2014 gae_pr_2019 gae_pr_2020 gae_pr_2024
    restore_stage "$db" "time-travel snapshots" tt_snap_2014 tt_snap_2019 tt_snap_2020 tt_snap_2024
    restore_stage "$db" "aux" bnodes arango_cypher_schema_cache
  fi
  restore_stage "$db" "named graph + visualizer assets" "${SYSTEM_COLLECTIONS[@]}"
  echo
  echo "=== $db restore complete ==="
}

case "${1:-both}" in
  FinReflectKgOneShard) restore_db FinReflectKgOneShard ;;
  FinReflectKgTemporal) restore_db FinReflectKgTemporal ;;
  both) restore_db FinReflectKgOneShard; restore_db FinReflectKgTemporal ;;
  *) echo "unknown target: ${1}" >&2; exit 2 ;;
esac

if (( ${#FAILED_STAGES[@]} > 0 )); then
  echo
  echo "=== ${#FAILED_STAGES[@]} stage(s) FAILED ==="
  for f in "${FAILED_STAGES[@]}"; do echo "  - $f"; done
  echo
  echo "For a partially-loaded 'relations', repair it in place (idempotent):"
  echo "  python scripts/resume_finreflect_edges.py <database>"
  exit 1
fi
