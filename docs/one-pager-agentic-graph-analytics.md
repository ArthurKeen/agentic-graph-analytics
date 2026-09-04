# Agentic Graph Analytics

**Connect a database, say what you want to know in plain English, and get back a reviewed, reproducible analysis — with no code and a human approving every consequential step.**

---

## The problem

Every organisation can produce totals. The questions that change decisions are about **relationships**:

- Which accounts sit at the centre of unusual money movement?
- Which advertising audiences secretly overlap, so we pay twice to reach the same people?
- Which suppliers are we exposed to three hops away, through companies we have never heard of?

You cannot answer these by filtering rows. They are about the shape of the connections, which means treating the data as a graph and running algorithms over its structure.

Those algorithms are a solved problem — PageRank, community detection, shortest path, a few dozen more, all well understood and fast at scale. **The maths was never the obstacle.** Pointing them at *your* data, aimed at *your* question, has been a specialist job that takes weeks.

## What it does

| Stage | What happens |
| --- | --- |
| **Connect** | Verifies reachability, permissions and engine availability before you invest time. |
| **Discover** | Reads your schema automatically — entity types, relationships, volumes, physical layout — including messy shapes like many logical types in one collection, or several unrelated graphs side by side. |
| **Specify** | Upload an existing brief and it extracts structured objectives, requirements and constraints; or let the Requirements Copilot interview you *knowing your schema*. Either way you get a versioned, approvable requirements document. |
| **Propose** | Agents turn requirements into concrete use cases and analysis templates — algorithm, parameters, scope. They arrive as **drafts**; nothing runs until a person approves it. |
| **Run & report** | A live pipeline view with retry and cooperative cancel. Results land back in your own database. Reports render from records, not stale exported files. |

## Why it holds up past the demo

- **Nothing runs unapproved.** Templates are drafts; editing an approved template creates a new version, so a published report always points at exactly what produced it.
- **Full lineage.** Any number traces back to the template, requirement version, run and graph snapshot behind it. "Where did this come from?" is a link, not an archaeology project.
- **Multi-tenant aware.** Where one database holds many customers separated by a field, it detects that from the data and warns *before* a run silently mixes them together.
- **Secrets never enter the graph database.** Credentials are held as references, not values, and excluded from exported bundles.
- **Cautious retention.** Sweeps are dry-run by default and name what they would remove. Approved requirements, published snapshots, and runs behind a published report are never removed at any age.
- **Everything consequential is audited** — create, approve, launch, publish, import, export, archive.

## Start from a vertical, not from zero

Five industry verticals ship with specialised analysis prompts and pattern detectors — **Ad-Tech / identity resolution**, **FinTech / financial services**, **fraud intelligence**, **social networks**, and a generic default — and custom verticals can be generated per project. You can also import a portable project bundle carrying a domain's use cases and templates. Bundles import as drafts, never as approved work, and cannot execute code — a file smuggling executable content is rejected rather than run. The format is documented, so your team's accumulated templates become the next project's starting point.

## Who it is for

- **Solutions and data teams** who spin up a bespoke project per engagement and would rather have one console and a reusable library.
- **Analysts who know their domain but not graph theory.** You do not need to know what a damping factor is to ask who the key players are.
- **Anyone who has to defend a number** to a regulator, client or board.

## Status

**Experimental.** The pipeline, workspace UI, requirements lifecycle, reporting and audit trail work end to end today against live ArangoDB clusters. Execution is currently single-process, so in-flight runs do not survive an API restart — a durable executor is the next milestone, and customer-facing deployments should wait for it. Open gaps are tracked as requirements in the [PRD](PRD_AGENTIC_GRAPH_ANALYTICS_UI.md).

## Try it

```bash
pip install -e .            # configure .env with your ArangoDB + LLM credentials
gaai-product-api serve      # workspace API
cd frontend && npm run dev  # workspace UI
```

Runs on **ArangoDB** — a database that stores data as a network of connected things, with an engine built to run these algorithms at scale.

*Longer read: [Medium article draft](medium-draft-agentic-graph-analytics.md) · Slides: [intro deck](deck-agentic-graph-analytics.html) · Setup: [README](../README.md)*
