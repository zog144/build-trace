# build-trace

**Documentation:** [Inspection schema](docs/build-trace/schema.md) · [Usage](docs/build-trace/usage.md) · [Integration observations](docs/build-trace/integration-observations.md) · [CI and acceptance](docs/build-trace/ci.md).

Read-only inspection of retained Zog build evidence, for people and automation.
The Python library and CLI expose the same versioned JSON: recognizable package
and phase labels, recorded commands, execution evidence, inputs, outputs,
comparisons and journal pages. Version 0.12.0 separates canonical reference closure,
declared evidence/provenance gaps and observation coverage, adds bounded declared-gap
queries, and permits canonical snapshot/history/traversal inspection without any local
image-build owner-state tree. Version 0.11.0 added caller-ordered verification history
and literal forward/reverse relationship traversal across canonical snapshots. Version 0.10.0 made
build-record 0.7 immutable generation-observation snapshots the preferred
integrate-observe boundary. Version 0.9.0 extended direct producer observation
inspection to canonical verification,
relationship and source-provenance identities. Version
0.8.0 introduced the read-only producer observation provider. Version 0.7.0 added
frozen source and ordered
patch details with explanatory comparisons, alongside generation summaries,
reused-output inspection, detailed inspection and membership navigation.

build-record owns canonical immutable provenance records, relationships and export.
image-build produces build facts and owns orchestration. build-trace consumes
record references and producer observations and presents them read-only; it has no
provenance or observation datastore. box-control owns execution identity and journal
access. station-access remains the authenticated network boundary; its new build-trace
endpoints and GUI are deferred. This program has no web server, execution backend,
retry operation or controller mutation path.

## Start

Python 3.10+ on Linux; the optional current companion packages require Python 3.11+.
No third-party dependency is needed for ordinary metadata inspection. Canonical
provenance queries require the build-record library. Direct producer observation
queries require build-record 0.5.0 or newer; canonical snapshot/history/traversal
queries require build-record 0.7.0 or newer. Run from this checkout:

```sh
python3 -m zog.build_trace --help
python3 -m zog.build_trace --project-root /path/to/zog-project --host-id HOST_ID list
```

`--project-root` is the controller project containing `state/image-build`, **not**
the source checkout. `--host-id` is an explicit caller-provided scope, not an
attestation or inferred enrollment identity. The caller must authorize that scope.
Every successful command prints one JSON object; no browser scraping is needed.
Optional installation with `python3 -m pip install .` adds `build-trace` to PATH.

See [the usage guide](docs/build-trace/usage.md) for failed builds, command details, journal
continuation and comparisons, [the schema contract](docs/build-trace/schema.md) for availability,
pagination, limits and errors, and
[integration observations](docs/build-trace/integration-observations.md) for the current
integrate-observe read-only foundation.

## Supported evidence

- Schema-1 image-build pipelines and attempts, including native-check/seed-check,
  package commands and test-fixture-cache/test-fixture-runtime command folders.
- Durable command views, controller checkpoints and execution completion records.
  Legacy completion/checkpoint records without a view remain inspectable with gaps.
- Prepared package input identities; retained package output manifest summaries;
  explicit artifact-reuse receipts; pipeline recipe inventory summaries.
- Canonical package/generation provenance and material projections through build-record.
- Build-record 0.7 immutable generation-observation snapshots as the preferred
  observation/query boundary. Snapshot views expose stored canonical verification
  checks/executions, relationships, source provenance and observation coverage, compare
  exact record sets, retain logical verification history across caller-supplied
  snapshot sequences, and traverse literal relationship facts forward/reverse without
  interpreting regressions, providers, causes or blast radius.
- Image-build integration-observation v1 generation envelopes and candidate verification
  exports remain available through an explicit read-only compatibility provider.
- Optional `BoxControlReader`: only `inspect_build_job` and `build_job_logs` are used.
  Retained completion evidence remains usable after controller history is pruned.

Each inspection rereads authoritative evidence. There is no persistent derived
index, ingestion operation or independent retention policy. Repeated inspection is
idempotent, creates no files and cannot launch or refresh a job. Commands and
outcomes come from retained records, never current recipes or output heuristics.

## Discovery and inspection budgets

Listing reads command/status metadata without loading package preparation or output
inventories. It stops after a result page or scan budget and returns a continuation.
Follow `has_more` and `next_cursor`, including when a page contains no matches.
Individual command/log requests read only the selected command's records. Full build
inspection, comparison and export are explicit deep reads.

Deep inspection defaults to **256 MiB** cumulative source bytes. List pages default
to **16 MiB** and **100 candidate builds**. Limits are configurable through
`InspectionLimits` or CLI options; errors include the exhausted budget and source
record. Responses remain bounded to 1 MiB. The one-shot observation-file provider
accepts at most 32 MiB. See the usage guide for examples.

## Current limits

The 0.5 consumer passed integrated live generation and journal acceptance.
The 0.6 summary/comparison and 0.7 source/patch additions have controlled local
fixture validation. The 0.8–0.12 observation surfaces have repository-only controlled fixtures.
Public GitHub Actions run the standalone core suite and installed
independent-consumer gate on Python 3.10 and 3.13, a namespace artifact gate,
and a focused public build-record integration test on Python 3.11. The complete
image-build/box-control/root-control companion contract remains a separate
acceptance requirement until all required source revisions are publicly
available. Core-suite optional companion skips are reported rather than
treated as full cross-component acceptance.
Version 0.2 received successful live discovery, shell parsing and journal feedback;
0.3 owner diagnostic imports and live inspection also passed. Canonical package/generation joins passed real execution, process-interruption
recovery and journal inspection; reboot/power-loss recovery was not established.

- Ad hoc operation directories outside `state/image-build/attempts` are not scanned.
  In particular, custom GCC diagnostic receipt layouts are reported explicitly as
  `unsupported-layout`, with command count unknown until explicitly adopted using
  the image-build diagnostic import contract. New GCC diagnostic jobs capture identity.
- New owner records expose source declarations and recipe identities; package
  versions, recipe text and patch/configure-option projections remain incomplete. Prepared recipe/toolchain/dependency identities
  and recorded argv are exposed. Source and recipe files are never executed.
- Commands are grouped by package directory, then the schema-1 phase order and
  numeric command index. There is no invented cross-package timeline or retry chain.
- Common shell option sequences, including `bash -eu -o pipefail -c SCRIPT`,
  expose the recorded body; unsupported parsing is distinct from missing evidence.
  A shell `-c` body is recorded text; subprocesses and external script contents are
  not individually captured. Timestamps remain missing unless present in records.
- Controller reads do not refresh stale states. No atomic snapshot spans the builder
  and controller. Changed evidence during one filesystem read returns an explicit error.
- Initial journal reads follow box-control's **tail** behavior. An empty initial page
  cannot distinguish no output from expired history. This limitation is preserved.
- Exports contain bounded metadata only. They do not include logs or workspace archives.
- Redaction is conservative presentation filtering, not a guarantee that arbitrary
  command/log text contains no secrets. Existing owner records are not rewritten.
  Treat output as administrator-only and review before sharing externally.

## Validation

```sh
python3 -m unittest discover -s tests -v
# Against separately retrieved companions; install their dbus-next==0.2.3 dependency:
PYTHONPATH=../build-record/src:../image-build/src:../box-control/box-control/src:../root-control/src python3 -m unittest discover -s tests -v
```

The independent-consumer Actions gate additionally installs build-trace, changes out of the source checkout, and verifies that a downstream consumer can
perform snapshot inspection/comparison, verification history and relationship traversal
using only the public `zog.build_trace` package surface. See
[acceptance/README.md](acceptance/README.md).

The optional companion contract tests use the real image-build engine/runner and
box-control record and journal reader with synthetic execution and journal rows. They do not
start systemd services or compile milestone packages. Detailed historical operational acceptance evidence is retained privately by maintainers and is not republished as part of the clean source repository.

Development should preserve the repository's clean history and use the public
CI, factual contracts and project-maintained contributor guidance.

For field-by-field authority, including legacy provenance snapshots and generation
locators, see [ownership classifications](docs/build-trace/schema.md#ownership-and-authority-of-inspection-fields).


## Canonical-only snapshot inspection

BuildTrace construction no longer requires `PROJECT/state/image-build` to exist.
Canonical snapshot operations need only the canonical record store, explicit host
scope, explicit project identity and caller-selected canonical snapshot IDs:

```sh
build-trace \
  --project-root /offline/release-view \
  --host-id HOST \
  --record-store /evidence/build-record/records \
  --record-project-id PROJECT \
  observation-snapshot sha256:SNAPSHOT
```

The project root may have no `state/image-build` directory. Snapshot inspection,
snapshot comparison, verification history and relationship traversal remain available.
Owner-local attempt/pipeline/command and generation-owner operations still return
`source-unavailable` when that state tree is absent.

Snapshot manifests keep three factual dimensions separate:

- `reference_closure_complete` / `missing_record_count`;
- `declared_gap_free`, `declared_gap_count`,
  `declared_gap_reason_count` and `declared_gap_summary`;
- canonical observation `coverage`.

Use `--collection declared-gaps` for paged exact canonical gap detail and optional
`--gap-category` filtering.


## Python namespace and aggregate release

The canonical Python import path is `zog.build_trace`; the human-facing program and
console command remain `build-trace`. Installable source lives only under
`src/zog/build_trace/`. This repository intentionally does not provide a top-level
`build_trace` compatibility package and does not own `src/zog/__init__.py`.

Repository packaging metadata is for component development only. Public Python
publication occurs only through the aggregate `zog` distribution assembled by
release-build, which can copy `src/zog/build_trace/` without rewriting Python
source. This repository is public source, not a separate approved PyPI upload.


## Verification execution environments

Build-trace 0.13 adds literal execution-environment evidence to canonical
`verification_history(...)` rows. Legacy opaque `environment_digest` records are
explicitly labeled `legacy-opaque`; newer canonical `execution_environment`
records expose their contract, digest and descriptor together with the separate
`producer_policy_digest`. Build-trace does not compare or classify environments.


## Public license and source lineage

The reviewed first-party source is licensed under `BSD-3-Clause OR GPL-3.0-only`;
see [LICENSE](LICENSE), [LICENSES](LICENSES/) and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). The public repository uses
fresh Git history. Historical private source commits, handoff tags and production
evidence were not imported; release-build must separately adopt the public
source commit in a newly verified source selection.
