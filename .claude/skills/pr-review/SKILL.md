---
name: pr-review
description: Review one pull request on arango-solutions-org/agentic-graph-analytics by verification — run every claim the PR makes rather than reading it, apply this repo's own rules (mock fidelity, wiring over deletion, test what you touch, modularity limits, PRD traceability), and produce a draft review for the user to approve before anything is posted (unless they have given standing authorisation to post, fix and merge). Use when asked to review a PR, check whether a PR can merge, or re-check a PR after its author pushed fixes. NOT the whole-repo audit — that is `/code-quality-review`.
---

# PR Review

One pull request, reviewed by verification. The built-in `/code-review` reads a
diff and finds bugs; this runs the repo's checks against the branch, in a
separate checkout, and drafts a review that says which claims were executed and
which remain read.

## Invocation

`/pr-review 22` — full review, draft only.
`/pr-review 22 recheck` — the author pushed after review: re-run each finding's
reproduction on the new head, nothing else.
`/pr-review 22 post` — post the approved draft (only after the user has seen it).

**Standing authorisation.** The user may ask for a pipeline instead of a draft
— "for all my PRs: review, comment, fix, comment, review, comment, merge". That
is consent, given once, for every step in it: post without asking, and say in
the reply what was posted. It does not extend to steps they did not name, and
merging one PR never authorises merging another.

## The two rules that make it worth running

**Nothing is posted until the user has read the draft and said so.** Draft in
the reply, offer to post in one line, post verbatim when told.

**Verify, don't opine.** Every finding names the command that produced it or
says "read, not executed". This repo's own history is the calibration — each of
these passed its tests or a reading of the diff:

- **The masking bug (2026-09-09).** A workflow printed `Errors: 0` and produced
  ten reports. All ten analyses had failed at graph loading — 0 successes, 39
  failures, 30 retries in the same log. `_cleanup_engine` stamped `CLEANING_UP`
  over the terminal `FAILED`, and `_wait_for_completion` counts `CLEANING_UP` as
  success. **Every layer was correct in isolation**; the failure was destroyed
  between them. Read what ran, not what the summary line claimed.
- **`scripts/patch_empty_adtech_reports.py` exists** because six of ten AdTech
  reports came back `result_count = 0` — and it was patched by regenerating the
  reports rather than fixing the status handling. A cosmetic patch for a masking
  bug is itself a finding.
- **Invented tuning params (2026-10-14).** `max_iterations`, `sample_size` and
  `threshold` were emitted against engine methods accepting none of them. Two
  killed analyses; `threshold` was latent, firing only when average degree
  exceeds 10. The names are authored in a different module from the signatures
  that consume them — check both ends, never one.
- **A test that proved nothing (2026-10-14).** Concurrency tests passed *with
  the semaphore removed*: the stub returned before the next task started, so
  overlap never occurred and the bound was never exercised. A test whose
  mechanism you have not confirmed is not evidence.
- **Three PRs that merged and shipped nothing (found 2026-11-18).** #21
  ("Platform login, step 2") had `base: feat/platform-login`, not `main`. It
  merged into that branch the day after #20 merged `feat/platform-login` into
  `main`, so its content never reached `main` — about 1,100 insertions across
  17 files, including whole modules (`profile_connection.py`,
  `tests/platform_fake.py`, `test_platform_profiles.py`). #19 and #15 have the
  same shape. GitHub shows all three **MERGED**, which is what a reader checks.
  A merge into a feature branch closes the PR and ships nothing.
- **A `NameError` `ast.parse` could not see.** An exception branch used four
  names the module never imported — syntactically valid, reachable only on the
  rare failure path.

Re-run every finding before you post it.

## This repo's shape — read before anything

- **PRs live on `arango-solutions-org/agentic-graph-analytics`.** Older docs and
  `CLAUDE.md` may say `arango-solutions/…`; the remote is authoritative. Pass
  `--repo` to every `gh` call.
- **The repo is PUBLIC.** A secret in a diff is published the moment it merges,
  retroactively. `.env` is gitignored and holds live ArangoDB, OpenAI, Anthropic
  and GAE credentials — check any new file, fixture, test or doc for them.
- **`origin` dual-pushes** to `arango-solutions-org` (primary) and the
  `ArthurKeen` fork. One `git push` reaches both, so a branch exists in two
  places; a merge on the primary does not delete it from the fork.
- **The main checkout's `.env` points at the `prod.demo.pilot.arango.ai`
  cluster**, which holds real demo data. Never run a PR's code from the main
  checkout — a workflow run writes result collections and deploys billable GAE
  engines. Use a worktree.
- **GAE engines cost money and outlive a failed run.** Any review that executes
  an analysis must list engines afterwards and stop strays:
  `list_services()` filtered on `gral`. Three were left orphaned by one failed
  run. Treat a PR that touches engine lifecycle as requiring this check.
- **The CI gates are weaker than they look.** `mypy graph_analytics_ai
  --ignore-missing-imports || true` — the `|| true` means **mypy can never fail
  CI**. `flake8` hard-fails only on `E9,F63,F7,F82`; its complexity/line-length
  pass is `--exit-zero`. `black --check` and both flake8 passes cover **only
  `graph_analytics_ai` and `tests`**, so `scripts/` (16 modules), `frontend/`
  and the four repo-root `.py` files are outside every Python gate. Findings
  cluster there, and a green CI says less than it appears to.
- **A stacked PR is the sharpest trap here, and it has two edges.** CI is
  `pull_request: branches: [main, develop]`, so a PR based on another feature
  branch **gets no checks at all** — `gh pr checks` says "no checks reported"
  and a reviewer reads that as pending. And merging it merges into its base,
  not into `main`. Always read `baseRefName` first; if it is not `main` or
  `develop`, say so in the verdict, and check the base's own PR before
  treating anything in the stack as shipped.
- **`black --check` is the one hard formatting gate.** A PR that adds an
  unformatted file under `graph_analytics_ai/` or `tests/` fails CI even though
  mypy and complexity do not.

## Method

### 0. Load the context before reading the diff

```sh
R=arango-solutions-org/agentic-graph-analytics
gh pr view N --repo $R \
  --json title,author,headRefName,baseRefName,headRefOid,isDraft,mergeStateStatus,files,body,reviews,comments
gh pr checks N --repo $R
gh issue list --repo $R --state open
git fetch origin "pull/N/head:refs/remotes/origin/pr/N" && H=origin/pr/N   # works for fork PRs too
git log --oneline origin/main..$H && git diff origin/main...$H --stat
```

Read existing reviews first; if one already asked for changes, the job is
`recheck`. If the base is not `main`, review only what this PR adds on top of
its base, and say so. Then read the whole diff and every new file in full.

**Check the base is current.** `main` moves fast here and a stale branch is
common: `git log --oneline $H..origin/main | wc -l`. A branch cut from a
superseded branch (rather than `main`) is a finding, not a detail.

### 1. Does it merge, really

`mergeStateStatus` lags. Do the merge:

```sh
W=$SCRATCH/wt-merge && git worktree add -q --detach $W origin/main && cd $W \
  && (git merge -q --no-edit $H && echo clean || { git diff --name-only --diff-filter=U; git merge --abort; }) \
  ; cd - && git worktree remove --force $W
```

**Does merging it actually ship anything?** `mergeStateStatus` and a MERGED
badge both answer the wrong question for a stacked PR. The test that is safe
under squash merges:

```sh
mt=$(git rev-parse origin/main^{tree})
t=$(git merge-tree --write-tree origin/main $H | head -1)
[ "$t" = "$mt" ] && echo "adds nothing to main" || git diff --name-only $mt $t
```

An empty result means `main` already has the content, whatever the commit
history looks like. A non-empty result on a PR whose base is `main` is normal;
on a *merged* branch it means work never landed. `git cherry` and
`merge-base --is-ancestor` both give the wrong answer after a squash merge —
neither is a substitute.

### 2. Run what CI runs, in a worktree

The worktree has no `.env`, so it cannot reach the production cluster or deploy
an engine by accident.

```sh
REPO=$(git rev-parse --show-toplevel); V=$REPO/.venv/bin
W=$SCRATCH/pr-N && git worktree add -q --detach $W $H

cd $W
# confirm the worktree's source is the one imported — the venv is an editable
# install pointing at the MAIN checkout, so this is not optional
PYTHONPATH=$W $V/python -c 'import graph_analytics_ai as g; print(g.__file__)'   # must be under $W
PYTHONPATH=$W $V/python -m pytest tests/unit -q
$V/python -m black --check graph_analytics_ai tests
$V/python -m flake8 graph_analytics_ai tests --count --select=E9,F63,F7,F82

# advisory only — these never fail CI, so report them as information
$V/python -m mypy graph_analytics_ai --ignore-missing-imports
$V/python -m flake8 graph_analytics_ai tests --max-complexity=10 --max-line-length=127 --exit-zero

# frontend, if touched — borrow node_modules only if package-lock.json is unchanged
ln -s $REPO/frontend/node_modules $W/frontend/node_modules
cd $W/frontend && npx tsc --noEmit && npm test
```

CI runs Python **3.10, 3.11 and 3.12**; the local venv is 3.11 only. A
version-sensitive change (typing syntax, stdlib behaviour) needs the matrix from
`gh pr checks`, not a local pass.

Compare test counts to the description. Remove the worktree when done:
`git worktree remove --force $W`.

### 3. Verify every claim that can be verified

| The PR says | Run |
|---|---|
| "fixes X" / "adds a regression test" | revert the fix in the worktree (`git show origin/main:<file> > <file>`), run the test, confirm it **fails**, restore. A test that passes both ways is not a regression test. **Revert one file at a time** — see below |
| a summary, report or status line that states a value | ask of each value: is this the **request** or the **result**? Wire-to-the-plan is this repo's recurring bug. Two of four fields in the FR-75 Discovery Summary read the plan, so a use case naming `centrality` reported `centrality` while WCC ran, and a dropped target was reported as the scope |
| an empty collection, list or set rendered to a user | distinguish *empty* from *unknown*. An unknown scope rendering as "the whole graph" is a claim where there should be silence |
| "the test proves the bound/limit holds" | confirm the mechanism, not just the assertion — a stub that returns instantly never exercises concurrency |
| a new agent/algorithm/engine path | run it against the assembled workflow, not the function. Does a failure surface as a failure, or as a success with zero results? |
| "no results" handling | check the status actually reaching the reporting layer; `CLEANING_UP`-over-`FAILED` is this repo's known masking shape |
| params passed to an engine method | check both ends — the emitting module and the consuming signature |
| new endpoint or router | hit it through the assembled app (`TestClient`), not the handler |
| "see `path`" / "uses `scripts/foo.py`" | `git cat-file -e "${H}:path"` |
| "closes #N" | read the issue; say which bullets it does and does not address |
| a number in the description or docs | recompute it |

**Revert one file at a time.** A wholesale revert of a multi-file change proves
nothing: every test fails for one trivial reason — a missing constructor
argument, an absent attribute — and the failures say nothing about which change
each test pins. On PR #30 a full revert failed all five new tests with the same
`TypeError`, which would have passed as evidence and was not. Reverting each
changed file separately and recording which tests fail against which file is
what distinguishes "this test pins the rendering" from "this test pins the
attribution".

Sharper still, where the PR fixes a behaviour rather than adding one: keep the
whole PR and restore **only the old logic**, leaving new fields and scaffolding
in place. That is the only configuration in which the test can fail *with the
original defect* rather than with an import error. On PR #30 it produced the
defect verbatim — a report headed `Analysis selected: Venues … Why: Venues are
small.` on an analysis of Authors — which is evidence; `TypeError` is not.

### 4. The repository's own rules

From `AGENTS.md`:

- **Mock fidelity.** A test passing against a wrong-signature mock is a test
  that did not run. Open the real declaration; the mock must mirror constructor
  args, method signatures and field types.
- **Wiring over deletion.** Deleted "unused" code needs proof it is obsolete.
  New code must be reachable from something that runs.
- **Test what you touch.** Every changed behaviour has a test that fails
  without it.
- **Verify before claiming done.** A PR description asserting a result must
  name how it was checked.
- **Incremental over atomic.** One concern per PR; a reviewer should hold it in
  five minutes and roll it back alone.
- **Modularity limits.** Source 1500 lines, tests 2000, config 500, docs 1000.
  Scripts belong in `scripts/`, not the repo root — four root `.py` files
  already violate this, so a PR adding a fifth is a finding.
- **PRD traceability.** A behaviour change names the requirement it implements
  (`FR-*` / `NFR-*`). If the PRD does not describe it, the PRD text goes in the
  same PR or the review raises it as a decision. Check `drift_alerts` before
  calling something a new gap — a tracked gap is not a finding. Note that
  `FR-65a`, `FR-65c` and `FR-67b` are cited in code but absent from the PRD, so
  a dangling marker has precedent here and is worth grepping for.
- **Truthful outcomes (NFR-19).** A terminal failure must not be overwritten by
  a later non-terminal status; a result carrying an error is a failure whatever
  its status says; an unconfirmed success reports as *not* succeeded. This is
  the requirement the masking bug produced — check any status handling against it.
- **Secrets.** No `.env`, keys, real hostnames or customer credentials in code,
  tests, fixtures, docs or build artefacts. The repo is public.

### 5. Flag for the next code-quality-review

`code-quality-review` is this repo's periodic whole-tree audit (duplication,
hardwired values, security, docs drift, docs duplication, PRD quality) — run
every few weeks across six parallel agents, not scoped to one diff. Don't
invoke it here. But if this PR's diff introduces or reveals a duplication, a
value that should flow through env but is baked in instead, or a pattern one
of its six dimensions would flag, say so explicitly in the report — that's
what lets the next periodic run skip ground this review already covered,
instead of rediscovering it cold. If `code-quality-review`'s own file has a
"Known clean" section, check it first: don't re-raise something already
verified there unless the code it covers has moved.

### 6. `recheck` — after the author pushes

Re-fetch `pull/N/head`. For each finding, re-run its reproduction on the new
head and report pass or fail. If the review gave no reproduction, build one
before judging, and say so.

## Output

Draft in the reply. Say in one line who it is written for, then the review,
ready to paste:

1. **Verdict in one sentence**: merge / merge after X / don't merge yet, and why.
2. **Verified**: what was run and passed. Lead with this.
3. **Must fix before merge**, numbered, each with its command or `file:line`.
4. **Should fix** and **Minor**.
5. **Answers to the author's own open questions**, if any.
6. **Decisions for the user**, kept separate (a product trade-off, a PRD change
   to accept), never buried among findings.

Plain language; for each finding, **Context / Action / Result**. No generic
praise and no first person ("X does not hold: Y", not "I checked X"). No
internal code names a reader cannot look up.

Post with `gh pr review N --repo $R --comment|--request-changes|--approve --body-file -`.
**GitHub refuses `--approve` and `--request-changes` on your own PR**, so use
`--comment` whenever the author is the user (which is most PRs here).

## Reviewing your own work

Most PRs here are the user's, and when an agent wrote them this is a
self-review. It still earns its keep: on #29, #30 and #31 it found six defects,
including two NFR-19 violations in the feature built to make reports truthful.
Every one came from running something, and none would have come from re-reading
the diff — which is the whole argument for this skill over `/code-review`.

What it cannot do is notice a framing you never had. The #30 review missed that
an empty collection list rendered as "the whole graph"; that only surfaced while
writing the fix, because implementing forced the empty/unknown distinction the
review had not thought to make. So:

- Write probes that could **falsify** the change, not tests that confirm it.
  Feed it the input it was not designed for — an algorithm name that does not
  parse, a target the schema lacks, an execution that failed.
- Say in the review that the author and reviewer are the same, and name what
  that leaves unchecked. A reader who knows it is a self-review weights it
  correctly; one who does not, cannot.

## Known gotchas

- `git fetch origin <short-sha>` fails. Fetch `pull/N/head`.
- zsh: write `"${H}:path"`, never `$H:path` (`:t`, `:r` are modifiers).
- `.venv/bin/pytest` run from outside the worktree imports the **main**
  checkout (editable install). Use `python -m pytest` from `$W` with
  `PYTHONPATH`, and check `graph_analytics_ai.__file__`.
- A background run started during a review can be killed by the Stop drift
  gate. Check the task's exit status before concluding it died — a `pgrep`
  miss at one instant is not proof.
- GAE engines survive a killed run. List and stop them before finishing.
- `gh pr checks --watch` can exit while a job is still pending. Loop on
  pending/queued/in_progress instead.
- **"no checks reported" has two unrelated causes.** Either the PR is stacked
  and no workflow ever triggered, or a run exists and wedged. `gh run list
  --branch <head>` tells you which; `gh pr checks` alone cannot.
- **A queued run can wedge with zero jobs attached** and sit there for over an
  hour against a five-minute norm (seen 2026-11-11, run 43095195772).
  `gh run cancel` may refuse it as "completed" while the API still reports it
  queued. Re-trigger by closing and reopening the PR — a base change alone does
  **not** fire the workflow, because its triggers are the default
  `opened`/`synchronize`/`reopened`.
- **Line numbers a review cites move while the review is being written.** Edits
  made in the same PR push the cited function down —
  `_create_discovery_summary_content` went 167 → 183 → 186 in one session, and
  PRD text written an hour earlier was stale before it was committed. Re-run
  the evidence gate as the **last** step before committing a PRD edit, not the
  first after writing it.
- The drift Stop gate re-arms on every uncommitted implementation edit. A
  review that edits files will fire it; commit or expect the loop.
