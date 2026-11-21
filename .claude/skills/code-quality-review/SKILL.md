---
name: code-quality-review
description: Run the periodic repo-wide quality audit — duplicate code, hardwired values, security risks, documentation drift from code, duplicated content across documents, and PRD quality (readability, bloat, requirement traceability) — across the whole tree rather than one diff. Produces a ranked report plus a remediation plan grouped into PR-sized units. Use when asked for a code quality review, a codebase audit, a security review, a documentation audit, a PRD review, or a check for drift/duplication/hardcoded values/doc redundancy; and at sprint boundaries. NOT for reviewing a single PR or diff — that is the built-in `/code-review`.
---

# Code Quality Review

The periodic whole-repo audit. `/code-review` looks at a diff; this looks at the
codebase, in six dimensions, and is meant to be run every few weeks rather than
per PR.

## Invocation

`/code-quality-review` — all six dimensions.
`/code-quality-review security` (or `duplication`, `hardwired`, `docs`,
`docs-duplication`, `prd`) — one.

## The rule that makes it worth running

**Verify every finding against the source before reporting it, and say which
ones you executed.** A review that reports plausible findings is worse than no
review: it costs a maintainer the afternoon it takes to discover the claim was
inferred. Quote `file:line` you have actually opened. Where a claim is
reproducible, reproduce it and paste the output. Where it is not, say what you
read and what remains assumption.

This repository has a live example of why, found on 2026-09-09. A FinReflectKG
demo run reported `Errors: 0` and produced ten reports. Every one of them said
"No Results Generated", because all ten GAE analyses had failed at graph
loading — 0 successes, 39 failures, 30 retries in the same log. The cause was
that `GAEOrchestrator._cleanup_engine` stamped `CLEANING_UP` over the terminal
`FAILED` status the retry loop had just set, and `AnalysisExecutor.
_wait_for_completion` counts `CLEANING_UP` as success. **Each layer was correct
in isolation** — the orchestrator set `FAILED` honestly, the executor mapped
statuses honestly, the agent checked `result.success` honestly. The failure was
destroyed *between* them, and what surfaced was `success=True, error=None,
result_count=0`.

Two lessons this audit is built on. First, read what runs, not what is claimed:
the workflow's own summary line said zero errors. Second, this class recurs —
`scripts/patch_empty_adtech_reports.py` exists because six of ten AdTech reports
came back `result_count = 0`, and it was patched by regenerating the reports
rather than by fixing the status handling. A cosmetic patch for a masking bug is
itself a finding.

## Method

Fan out one subagent per dimension in parallel, then verify their headline
claims yourself before any of it reaches the user. The tree is ~49k lines of
Python across 113 modules in `graph_analytics_ai/`, 54 TypeScript modules under
`frontend/src`, ~26k lines of tests across 75 files, and ~57k lines of Markdown
across 142 files; doing this serially in the main thread does not fit.

Give each agent the repo context below, and tell it explicitly: rank by
consequence, distinguish deliberate design from drift, skip trivia, and state
what came up clean so the next run can skip it.

### 1. Duplicate code
Copy-paste families, and above all **copies that have already drifted** — a
guard present in one and missing in its twin. Deliberate parallel structure is
not a finding unless it has diverged; in this repo that means the per-industry
prompt verticals in `ai/reporting/prompts.py`, the per-algorithm dispatch
(`pagerank` / `wcc` / `scc` / `label_propagation` / `betweenness`, which recurs
in `ALGORITHM_RESULT_FIELDS`, the `run_*` branches in `gae_orchestrator.py`, the
chart builders in `scripts/_graph_view.py`, and the insight generators in
`ai/reporting/algorithm_insights.py`), and the per-demo script pairs. Name the
seam any consolidation should live in.

The demo pairs deserve naming because they are the youngest and least settled:
`scripts/run_adtech_demo.py` / `run_finreflect_demo.py` and
`seed_adtech_workspace.py` / `seed_finreflect_workspace.py`. The FinReflect
copies were written on 2026-09-09 by adapting the AdTech originals, and they
have **already diverged on purpose**: the AdTech seeder calls
`ensure_clean_workspace_db()`, which drops and recreates the entire
`aga_workspace` database, while the FinReflect seeder purges only its own
workspace id. That divergence is correct — but it means a fix applied to one
will not reach the other, which is exactly the condition this dimension exists
to catch.

The sharpest version here is **state that loses fidelity crossing a layer
boundary**. The 2026-09-09 masking bug is the archetype: a status enum written
by one layer, overwritten by a second for an unrelated reason, and read as
success by a third. Look for the same shape wherever a result, status or error
is handed across the orchestrator → executor → agent → report chain, and
wherever an exception is caught and downgraded to a log line.

### 2. Hardwired values
Hosts, ports, database and collection names, magic numbers, paths, model names,
thresholds, retry counts and timeouts.

**Unlike the sibling repos this skill was adapted from, `AGENTS.md` states no
config-ownership rule here** — it says only "configuration rather than
hardcoding for anything that could differ across environments". So you cannot
mechanically call a stray `os.getenv` a violation. Report the shape instead:
`graph_analytics_ai/config.py` exists and owns the Arango and GAE settings, yet
14 other modules in the package read `os.getenv` / `os.environ` directly
(`gae_connection.py`, `db_connection.py`, `gae_orchestrator.py`,
`product/byoc_app.py`, `product/agentic_run_supervisor.py`,
`auth/oasis_token_helper.py`, `cli/*` among them). **The finding is that the
convention is unsettled**, and the useful output is a proposed rule plus the
test that enforces it — not 14 separate paragraphs.

Two specifics that bite here. The `GAE_PLATFORM_*` tuning knobs are set by
`os.environ.setdefault` inside the demo runners, so the effective default lives
in a script rather than in `config.py` and differs per demo. And result
collection names (`uc_*_results`) are strings that appear in templates, the
orchestrator, the report builders and the chart builders — a rename that misses
one copy fails only at runtime and only on that path.

### 3. Security
**This repository is public** (`arango-solutions/agentic-graph-analytics`).
Anything committed is committed for good, retroactively. Priorities, in order:

- **Credential handling.** `.env` carries live ArangoDB passwords, an OpenAI key,
  an Anthropic key and `ARANGO_GRAPH_API_KEY_SECRET`. Confirm `.env` is
  gitignored **and** that no key has ever been committed (check history, not just
  the working tree). The product API stores `secret_refs` pointing at env var
  names rather than values — verify that indirection holds on every path,
  including the persisted connection profiles and the audit events.
- **Credentials reaching logs or storage.** Connection profiles accept endpoint,
  database and username, with the password resolved from the environment. Trace
  that end to end — structured logging, exception handlers, and the workflow
  run/report rows persisted to `aga_workspace`, which is where a credential is
  most likely to be written without anyone deciding to.
- **AQL injection** on any path that interpolates user or LLM input into a query
  rather than binding it. Bind variables are the convention; find the exceptions.
  The LLM-generated AQL paths deserve particular attention, because the input is
  not a person and the usual trust intuitions do not apply.
- **The MCP surface** (`graph_analytics_ai/mcp/`), which exposes the platform to
  an agent with the same reach as the UI. Check it enforces the same
  authorization, not a parallel weaker copy.
- **JWT handling** in `gae_connection.py`, which mints and refreshes tokens
  against `/_open/auth`.
- Dependency and CI supply chain.

Demand a concrete exploit path — who the attacker is, what they control, what
they get — and label anything without one as hardening rather than a
vulnerability.

### 4. Documentation consistency
**There is no docs-consistency test here**, so this dimension is entirely manual
and entirely uncovered. Highest value is docs-vs-code drift: a documented env
var, command, endpoint, path, count or capability that no longer matches the
source. `README.md` (1,460 lines) and `AGENTS.md` matter most because onboarding
follows them literally, and `README.md` is the front door of a **public** repo.

A live example to calibrate against, verified 2026-09-29:
`SUPPORTED_INDUSTRIES.md:5` states "**5 major industry verticals**" and its
registry table lists five, but `ai/reporting/prompts.py` registers six —
`corporate_disclosure` was added on 2026-09-09 and the doc was never updated.
That is the whole class in miniature: a count in prose, a registry in code, and
no test tying them together.

Specific things that rot here: the Quick Start command sequence, capability and
status tables, the industry-vertical list and count, the algorithm list (the
engine exposes exactly `pagerank`, `wcc`, `scc`, `label_propagation`,
`betweenness` — docs and BRDs that promise Degree Centrality or Shortest Path
are describing something that cannot run), the endpoint tables against the
registered FastAPI routes, and any architecture diagram naming a component.

### 5. Duplicate content across documents
The unit is a **fact**: a number, a command, a path, an env var, an endpoint, a
capability claim. Every place it is written is a place it can rot independently,
and the copy nobody remembers to update is the one a newcomer reads.

This repo concentrates it in two places. First, the onboarding set — `README.md`,
`AGENTS.md`, `CLAUDE.md` and `SUPPORTED_INDUSTRIES.md` — which overlap by design;
note that `CLAUDE.md` is **gitignored**, so guidance that lives only there is
invisible to everyone else and is itself a finding. Second, the 142-file `docs/`
tree, where the deck (`docs/deck-agentic-graph-analytics.html`, mirrored into
`scripts/build_deck_pptx.py`) restates architecture claims for a different
audience and can propagate a stale one into several renderings at once.

For each real finding, name which copy should be canonical and what the others
become: a link, a pointer, or nothing.

### 6. PRD quality
Scope is `docs/PRD_AGENTIC_GRAPH_ANALYTICS_UI.md`. This dimension judges the
document itself — `/prd-sync` reconciles it against the code, so do not re-run
that here.

- **Readability and requirement structure.** One requirement per statement,
  testable, unambiguous, and individually addressable by its `FR-*` marker,
  because the code and the commit messages cite them that way. A requirement that
  is really three cannot be cited, implemented or closed.
- **Bloat.** Not a subtle judgment call here: the PRD is **~3,400 lines against
  the 1,000-line limit `AGENTS.md` sets for docs** — more than three times the
  repo's own stated maximum, and past the point where anyone reads it end to end.
  So the question is not whether to split but where the seams are. Look for
  rationale that has grown into the requirement, phase/status narrative that
  belongs in a roadmap, measured-evidence blocks that belong in a research note,
  and superseded text left standing beside its replacement.
- **Traceability, both directions.** Every `FR-*` marker cited in
  `graph_analytics_ai/`, `frontend/` or a commit message resolves to a
  requirement that exists. Every requirement is implemented, tracked as an open
  drift alert, or explicitly deferred — a requirement in none of those three
  states is one nobody owns. `drift_alerts` in the shared memory is the authority
  for the middle case; check it before reporting a gap, because a known tracked
  gap is not a new finding.

## Prefer a test over a finding

The most useful output of a review is often a test, not a paragraph. A finding
becomes an assertion that fails in CI for everyone, instead of a finding someone
has to rediscover.

This repo has one worked example already, from the 2026-09-09 masking bug:
`tests/unit/ai/execution/test_failure_not_masked_as_success.py` asserts that
engine cleanup cannot erase a terminal failure. It was validated by reverting the
fix and watching it fail — **do that for every test you propose**, or you have
written an assertion that passes for reasons you have not established.

There is no calibration run yet, so the table below is **candidates, not
history** — do not cite them as past results:

| Candidate assertion | Catches |
| --- | --- |
| Every industry key in `INDUSTRY_PROMPTS` appears in `SUPPORTED_INDUSTRIES.md`, and the stated count matches | The live dimension-4 drift above |
| Every algorithm named in docs/BRDs is a key of `ALGORITHM_RESULT_FIELDS` | Docs promising algorithms the engine cannot run |
| Every `FR-*` cited in source resolves to a marker in the PRD | Dangling requirement citations |
| README's documented endpoints ⊆ the registered FastAPI routes | Dimension-4 drift on a public front door |
| No `AnalysisStatus` transition can overwrite a terminal state | The masking class, generalised |
| `scripts/` and repo-root `*.py` pass the same `black`/`flake8` gate as the package | The coverage gap in the section below |

Prefer the mechanical form wherever the fact is mechanical. A count in prose and
a registry in code can be made to agree; an `FR-*` marker cited in source but
absent from the PRD is a grep away from being a test. Reach for prose only where
judgment is the point — whether a requirement reads clearly, whether two
documents should be one.

## Repo context to hand each agent

- Python library + FastAPI product API + Next.js frontend, with ArangoDB as the
  store and the Graph Analytics Engine (GAE) as the compute.
  `graph_analytics_ai/**` is the engine (113 modules, ~49k lines),
  `frontend/src/**` the workspace UI (54 modules), `docs/**` the doc tree,
  `docs/PRD_AGENTIC_GRAPH_ANALYTICS_UI.md` the spec.
- **The repo is public** (`arango-solutions/agentic-graph-analytics`).
- **The CI gates are weaker than they look, and findings will cluster in the
  gaps.** `mypy graph_analytics_ai --ignore-missing-imports || true` — the
  `|| true` means **mypy can never fail CI**. `flake8` fails only on
  `E9,F63,F7,F82`; its complexity and line-length pass is `--exit-zero`. `black
  --check` and both `flake8` passes cover **only `graph_analytics_ai` and
  `tests`**, so `scripts/` (16 modules), `frontend/`, and the repo-root Python
  files are outside every Python gate.
- **Four Python files sit at the repo root** — `run_agentic_workflow.py`,
  `test_connection.py`, `test_custom_vertical.py`, `validate_tests.py` — against
  `AGENTS.md`'s own placement rule ("scripts in `scripts/` — not the repo root").
  Note `test_connection.py` exists at the root *and* as
  `graph_analytics_ai/cli/test_connection.py`; the root ones also read as tests
  to pytest's naming convention without being tests.
- Engineering rules live in `AGENTS.md`; `.cursor/rules/` holds only
  `workflow.mdc`, so the two-copy mirroring the sibling repos have does not
  apply here. The rules with teeth for this audit: `modularity-and-structure`
  (source 1500 lines, tests 2000, config 500, docs 1000),
  `wiring-over-deletion` (unused code is usually a missing feature, not
  garbage), `mock-fidelity` (a mock whose signature drifts from the real symbol
  is a test that did not run), and `verify-before-claiming-done`.
- Spec-driven with enforcement: `/prd-sync` audits code against the PRD in both
  directions, `drift_alerts` holds open gaps, and PRD changes go through proposed
  patches rather than silent edits.
- **GAE is external and currently unreachable.** The engine control plane
  (`/gen-ai/v1/*`) works, but the per-engine data plane (`/gral/<id>/v1/*`) has
  no ingress route on the demo deployment — requests fall through to arangod,
  which 404s them. So any analysis path will fail end to end for reasons that are
  not this codebase's fault. Do not report that as a code finding; do report code
  that mistakes it for success.
- `origin` is `arango-solutions` (primary) and dual-pushes to the personal fork,
  so a branch you open is published to both.

## Nothing is pre-cleared

Sibling repos carry a "known clean as of <date>" list here, so a run can state
those areas as covered instead of re-deriving them. **This repo has no such list
because this audit has never been run on it.** Do not import another repo's list:
it describes another repo's code paths, and inheriting it would mark as verified
exactly the things nobody has looked at.

The first run should end by writing this section — what it checked and found
clean, specific enough that the next run can skip it and re-check only if the
relevant code moved.

## Output

Two parts, and the second is the one that gets acted on: **the report** is what
you found, **the plan** is what someone does with Monday morning.

### The report

Ranked by consequence, most severe first, leading with the single thing to fix
today. Say what is healthy before what is broken — it is load-bearing context
for how much the findings mean, and a review that opens on a wall of defects
reads as noise even when every item is real.

For each finding: `file:line`, the defect in one sentence, the scenario in which
it bites, the fix, and **whether you verified it by execution or it remains
inference**. Never blur those two — the whole value of this audit is that its
claims were checked, and one unmarked guess costs the reader their trust in the
rest.

### The plan

Group the findings into PR-sized units of one concern each, per
`incremental-over-atomic` — a unit a reviewer can hold in their head in five
minutes and roll back on its own. Then:

- **Order them**, and say why that order: which must land first because another
  reads its output or edits the same lines, and which are independent and can go
  in parallel.
- **For each unit, say whether it becomes a test or stays a prose finding.**
- **Separate the mechanizable from the judgment calls**, because they need
  different people and different amounts of time. "Bring `scripts/` under the
  black and flake8 gate" is an afternoon; "this PRD should be four documents" is
  a decision someone owns.
- **Say what you are deliberately not proposing**, and why. A finding left
  unfixed on purpose is a decision; a finding left out silently is a gap.

Then offer to open them as separate branches.
