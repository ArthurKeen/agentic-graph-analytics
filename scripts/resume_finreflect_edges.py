#!/usr/bin/env python3
"""Resume a partially-restored FinReflect `relations` collection.

WHY THIS EXISTS
---------------
`arangorestore` is the only ArangoDB client tool that can authenticate against
this deployment: the Platform's Envoy gateway rejects the tools' username +
password login, and only `arangorestore`/`arangodump` accept a pre-obtained
bearer JWT via `--server.jwt-token`. `arangoimport` has no such flag (passing
the JWT as `--server.password` returns HTTP 401), so the natural
`arangoimport --on-duplicate ignore` resume path is unavailable.

`arangorestore` itself cannot resume: `--overwrite true` truncates the
collection first, so recovering from a mid-load failure would mean re-loading
every edge from zero.

This script closes that gap using python-arango, whose plain-REST auth the
gateway does allow. It streams the dump's edge payload and bulk-inserts with
``on_duplicate="ignore"``, which makes it idempotent against the deterministic
edge `_key`s in this dataset (e.g. ``ctas_2022_page_15_chunk_1_triplet_2``).
Re-running it is always safe, so a transient network fault costs only the
batches still outstanding.

Usage:
    python scripts/resume_finreflect_edges.py FinReflectKgOneShard
    SKIP_LINES=13900000 python scripts/resume_finreflect_edges.py FinReflectKgOneShard
    python scripts/resume_finreflect_edges.py FinReflectKgTemporal --expect 17513372

`SKIP_LINES` is an optimisation, not a correctness mechanism: `arangorestore`
reads the dump sequentially, so lines well before the failure point are already
present and re-sending them is pure cost. The final count is always verified
against `--expect`, and the script tells you to re-run with SKIP_LINES=0 if the
total falls short.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

from arango import ArangoClient

DUMP_ROOT = Path.home() / "data" / "domyn" / "2026"
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "5000"))
SKIP_LINES = int(os.environ.get("SKIP_LINES", "0"))
MAX_RETRIES = 8


def find_edge_datafile(dump_dir: Path) -> Path:
    """Locate the `relations` data payload inside an arangodump directory."""

    matches = sorted(dump_dir.glob("relations_*.data.json.gz"))
    if not matches:
        raise SystemExit(f"No relations data file under {dump_dir}")
    if len(matches) > 1:
        raise SystemExit(f"Expected one relations data file, found {len(matches)}")
    return matches[0]


def connect(database: str):
    client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
    return client.db(
        database,
        username=os.environ["ARANGO_USER"],
        password=os.environ["ARANGO_PASSWORD"],
    )


def flush(collection, batch: list, stats: dict) -> None:
    """Insert one batch, retrying transient faults with backoff.

    The failure that made this script necessary was a DNS blip inside the
    container mid-load (`getaddrinfo ... Name or service not known`), so
    transient network faults are expected rather than exceptional.
    """

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = collection.import_bulk(
                batch,
                on_duplicate="ignore",
                halt_on_error=False,
                sync=False,
            )
            stats["created"] += result.get("created", 0)
            stats["ignored"] += result.get("ignored", 0)
            stats["errors"] += result.get("errors", 0)
            return
        except Exception as exc:  # noqa: BLE001 - deliberately broad; retry anything
            if attempt == MAX_RETRIES:
                raise
            wait = min(2 ** attempt, 60)
            print(
                f"  ! batch failed ({type(exc).__name__}: {str(exc)[:90]}); "
                f"retry {attempt}/{MAX_RETRIES - 1} in {wait}s",
                flush=True,
            )
            time.sleep(wait)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", help="Target database (must already exist)")
    parser.add_argument(
        "--expect",
        type=int,
        default=17_513_372,
        help="Expected final edge count (default: the full FinReflectKG corpus)",
    )
    args = parser.parse_args()

    dump_dir = DUMP_ROOT / args.database
    datafile = find_edge_datafile(dump_dir)

    db = connect(args.database)
    collection = db.collection("relations")
    before = collection.count()

    print("=" * 68)
    print(f"RESUME relations -> {args.database}")
    print("=" * 68)
    print(f"datafile : {datafile.name}")
    print(f"present  : {before:,}")
    print(f"expected : {args.expect:,}  (gap {args.expect - before:,})")
    print(f"skip     : {SKIP_LINES:,} line(s)")
    print(f"batch    : {BATCH_SIZE:,}")
    print()

    if before >= args.expect:
        print("Already complete; nothing to do.")
        return

    stats = {"created": 0, "ignored": 0, "errors": 0}
    batch: list = []
    read = 0
    start = time.time()
    last_report = start

    with gzip.open(datafile, "rt", encoding="utf-8") as handle:
        for line in handle:
            read += 1
            if read <= SKIP_LINES:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                stats["errors"] += 1
                continue
            # `_rev` is dump metadata; let the server assign a fresh revision.
            doc.pop("_rev", None)
            batch.append(doc)

            if len(batch) >= BATCH_SIZE:
                flush(collection, batch, stats)
                batch = []
                now = time.time()
                if now - last_report >= 30:
                    sent = stats["created"] + stats["ignored"]
                    rate = sent / max(now - start, 1)
                    print(
                        f"  line {read:,} | created {stats['created']:,} "
                        f"ignored {stats['ignored']:,} | {rate:,.0f} docs/s",
                        flush=True,
                    )
                    last_report = now

    if batch:
        flush(collection, batch, stats)

    after = collection.count()
    elapsed = time.time() - start
    print()
    print("-" * 68)
    print(f"lines read : {read:,}")
    print(f"created    : {stats['created']:,}")
    print(f"ignored    : {stats['ignored']:,}  (already present)")
    print(f"errors     : {stats['errors']:,}")
    print(f"count      : {before:,} -> {after:,}  (expected {args.expect:,})")
    print(f"elapsed    : {elapsed/60:.1f} min")

    if after != args.expect:
        print()
        print(
            f"INCOMPLETE: {args.expect - after:,} edge(s) missing. If SKIP_LINES "
            "was set, re-run with SKIP_LINES=0 to sweep the whole file."
        )
        sys.exit(1)
    print()
    print("COMPLETE: edge count matches the expected corpus size.")


if __name__ == "__main__":
    main()
