# Vertical Project Bundle format

Import format for PRD **FR-49** (AdTech-style YAML/docs projects) and **FR-50**
(clinical trials / CRO and open-source-intelligence analysis template files).

## Why one format for two requirements

The PRD names two source shapes, but no concrete schema for either exists in
this repository or in the historical sibling repos it refers to (`dnb_er`,
`matpriskollen`, `psi-graph-analytics`). Rather than guess at a third party's
file layout, this defines a single documented bundle. The two requirements
differ in **domain vocabulary**, not structure — both describe "here are the
analytical questions, and here are the algorithm configurations that answer
them" — so a `vertical` discriminator carries the difference and a second
parser would be duplication.

If a real upstream format later appears, write a thin adapter that emits this
bundle rather than a second importer.

## Safety

Bundles are parsed with `yaml.safe_load`, never `yaml.load`. The default PyYAML
loader can construct arbitrary Python objects from tags such as
`!!python/object/apply`, which is precisely the arbitrary code execution these
requirements forbid. A bundle carrying such a tag is **rejected**, not executed.

YAML is a superset of JSON, so `.json` bundles parse with the same reader.

Everything imports as **DRAFT**. Importing is not approving.

## Schema

```yaml
vertical: adtech              # adtech | clinical_trials | osint | anything
name: Audience Planning       # optional, recorded on the audit event
description: Optional prose.  # optional

use_cases:
  - title: Rank audiences by influence     # required
    type: centrality                       # a UseCaseType; unknown -> pattern + warning
    priority: high                         # critical|high|medium|low; unknown -> medium
    description: Optional prose.
    algorithms: [pagerank]
    data_needs: [Audience, targets]
    expected_outputs: [ranked audience list]
    success_metrics: ["top-50 reviewed"]

templates:
  - name: PageRank on Audience             # required
    algorithm: pagerank                    # required
    description: Optional prose.
    parameters: {damping_factor: 0.85}
    config: {graph_name: adtech_graph}
    use_case: Rank audiences by influence  # matched to a use case by title
```

## Partial imports

A malformed entry does not fail the bundle. Unknown enum values fall back to a
default, and a `use_case` reference that matches nothing imports the template
unlinked. Every such decision is reported in the response's `warnings`, because
a partially linked import a user can inspect is more useful than a rejected one
— but it is never silent.

## Endpoint

```
POST /api/workspaces/{workspace_id}/vertical-projects/import
{"document": "<raw yaml or json>", "document_format": "yaml"}
```
