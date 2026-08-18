# Your Data Already Knows Who the Key Players Are. Ask It.

*Connect a database, describe what you want to know in plain English, and get a reviewed, reproducible analysis back — without writing a line of code.*

---

## The questions spreadsheets can't answer

Every organisation can tell you totals. How many accounts, how many claims, how many devices, how much spend. That's what tables are good at.

The questions that actually change decisions tend to be about **relationships**:

- *Which accounts sit at the centre of unusual money movement?*
- *Which of our advertising audiences secretly overlap, so we're paying twice to reach the same people?*
- *Which clinical trial sites cluster around the same handful of investigators — and what happens to enrolment if one of them leaves?*
- *Which suppliers are we exposed to indirectly, three hops away, through companies we've never heard of?*

None of these are answerable by filtering rows. They're about the *shape of the connections* between things. Answering them means treating your data as a **graph** — a network of entities and the links between them — and running algorithms over that network's structure.

The good news: those algorithms are a solved problem. **PageRank**, the technique that made Google work, tells you what's influential in a network. **Community detection** tells you what clusters together. **Shortest path** tells you how exposure travels. There are a few dozen more, all well understood, all fast even on very large networks.

The bad news, until now: pointing them at *your* data, aimed at *your* question, has been a specialist job that takes weeks.

**Agentic Graph Analytics closes that gap.** It's a console that takes you from "here's my database and here's what I need to know" to a reviewed, reproducible, shareable analysis — with a human approving every consequential step, and no code to write.

---

## What it actually does

### 1. Connect, and let it read the map

You add a connection to your database. The product verifies it can reach it, checks the permissions it has, and confirms the analytics engine is available — before you invest any time.

Then it **discovers your schema automatically**. Not "please describe your data model in this form" — it inspects the database and works out what your entities are, how they connect, how many of each there are, and what role each one plays.

This matters more than it sounds. Real databases are messy. Some store each entity type in its own container; others cram many logical types into one, distinguished by a `type` field. Some databases hold several unrelated graphs side by side — a document corpus next to an extracted knowledge graph next to a straightforward HR dataset. Naive tooling looks at that and reports "one entity type: `Entities`," which is useless.

The discovery step handles all of those shapes, classifies what each graph is *for*, and notes how the data is physically laid out across machines. Everything downstream depends on getting this right, so it's the part that got the most attention.

### 2. Say what you want to know

Two ways in, depending on where you're starting from.

**Upload what you already have.** Business requirements are usually already written down — a Word document, a PDF, a Markdown brief. Upload it and the product extracts the structured objectives, requirements and constraints from the prose.

**Or let the Copilot interview you.** If nothing's written down, the Requirements Copilot asks questions — and, crucially, it asks them *knowing your schema*. It's not a generic questionnaire. It has already seen your entity types, your relationship types, your volumes, and whether your data is partitioned by customer, so its questions are about your actual graph.

Either way you end up with a versioned requirements document you can review, edit, approve, and revisit later. Every subsequent analysis traces back to it.

### 3. Let agents propose the analyses — then approve them yourself

This is where the "agentic" part earns its name. Given your requirements and your schema, AI agents propose **use cases**: concrete analytical questions worth asking of this specific graph. Each use case becomes one or more **analysis templates** — a chosen algorithm, its parameters, which parts of the graph it runs on, and what it will produce.

Then you review them. Not as a formality:

- Templates arrive as **drafts**. Nothing runs until a person approves it.
- Editing an approved template **creates a new version** rather than mutating the old one, so a published report always points at exactly what produced it.
- Every parameter is visible and adjustable. If you disagree with the agent's choice of algorithm or its damping factor, change it.

The agents do the tedious part — mapping business questions onto the right algorithms with sensible settings. You keep the judgement.

### 4. Run it, and watch it work

Launch a run and you get a **live pipeline view**: every step, its status, what it produced, what it warned about. Steps can be retried, paused and resumed. If something fails at step four, you don't start over.

Three execution modes, depending on what you need:

- **Quick Analysis** — one prompt, one report, no setup. For when you want an answer, not a project.
- **Guided Analysis** — the Copilot interview, then a focused analysis.
- **Detailed Analysis** — full requirements producing many use cases and reports, with agents running independent branches in parallel.

Results land back **in your own database**, next to the data they were computed from. Nothing important lives in a folder on someone's laptop.

### 5. Reports that stay true

Reports are rendered from database records, not exported as static files. That distinction sounds academic until the third time someone circulates a PDF that's four months stale.

Because everything is a record with lineage, you can:

- **Compare runs over time** — the same analysis on this quarter's data versus last quarter's, with the deltas surfaced.
- **Trace any number back to its source** — which template produced it, which requirement version justified it, which run executed it, against which snapshot of the graph.
- **Re-run and re-explain** an analysis months later, and get a defensible answer about what changed.

For anything that ends up in front of a regulator, a client or a board, that provenance is the whole ballgame.

---

## Built for the way real deployments actually look

A few things that only matter once you're past the demo:

**It knows when your data is partitioned by customer.** Many production databases hold many tenants' data in one place, kept apart by a field. Run an analysis blind across that and you produce a beautiful result that mixes customers together — which is worse than no result. The product detects that layout from the database itself and warns you *before* the run starts, naming the field it found. It warns rather than blocks, because it's an inference, not a policy — but you'll never do it by accident.

**It knows how your data is spread across machines.** Physical layout determines whether an analysis needs an expensive shuffle between servers or can stay local. That's read directly from the database and used to plan the work.

**Secrets never go in the graph database.** Connection credentials are held as references, not values. Exported bundles exclude them.

**Everything consequential is audited.** Create, update, approve, launch, publish, import, export, archive — all recorded, all attributable.

**Retention is configurable, and cautious.** Set windows for drafts, runs, documents, report snapshots and audit logs. The sweep is a **dry run by default**: it shows you exactly which records it would remove, by name, before anything is deleted. Approved requirements, published report snapshots, and any run sitting behind a published report are never removed at any age — the compliance trail is the last thing that should evaporate.

---

## Start from a vertical, not from zero

Some domains ask the same questions repeatedly. Rather than rediscovering them each time, you can import a **project bundle** — a portable file carrying a vertical's use cases and analysis templates in one go.

- **AdTech / identity graphs** — audience overlap, identity resolution, influence ranking across the ad supply chain.
- **Clinical trials and CRO networks** — site clustering, investigator networks, enrolment-path analysis.
- **Open source intelligence** — entity linkage, indirect-exposure discovery, community structure.

Bundles import as **drafts**, never as approved work, so a starter pack is a starting point rather than something that quietly starts running. Importing cannot execute code — bundles are parsed strictly, and a file that tries to smuggle executable content is rejected rather than run.

Bring your own, too: the format is documented, so an internal team's accumulated templates become a bundle you hand to the next project.

---

## Who this is for

**Solutions and data teams** who currently spin up a bespoke project for every engagement, and would rather have one console and a library of reusable templates.

**Analysts who know their domain but not graph theory.** You do not need to know what a damping factor is to ask "who are the key players here?" The agents map your question onto the right algorithm; you review the proposal in business terms.

**Anyone who has to defend a number.** Versioned requirements, immutable approved templates, run lineage, comparison across time and a full audit trail mean the answer to "where did this come from?" is a link, not an archaeology project.

---

## The short version

Graph algorithms have been able to answer your most valuable questions for a decade. The obstacle was never the maths — it was the weeks of specialist work between having a database and having an answer.

Connect a database. Say what you want to know. Review what the agents propose. Run it, share it, and come back next quarter to see what changed.

*Agentic Graph Analytics runs on ArangoDB — a database that stores your data as a network of connected things, and ships with an engine built to run these algorithms at scale.*
