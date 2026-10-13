# Independent consumer acceptance

This directory contains a deliberately small consumer for the early
`integrate-observe` contract.

`integrate_observe_consumer.py` is not part of the build-trace runtime package. Its
purpose is to prove that a downstream consumer can obtain the required factual views
without importing build-record, image-build or build-trace internals.

The consumer imports only:

```python
from zog.build_trace import BuildTrace
```

and invokes these public methods:

- `observation_snapshot`;
- `compare_observation_snapshots`;
- `verification_history`;
- `relationship_traversal`.

The acceptance test mechanically parses the consumer source and fails if it imports
`zog.build_record`, `zog.image_build` or any `zog.build_trace.*` internal module. It also
checks that the set of public methods used by the consumer remains exactly the
documented four-method observation surface.

The consumer produces a neutral factual digest for a caller-selected snapshot
sequence. It intentionally records that it did **not**:

- select a baseline;
- infer chronology;
- choose a representative verification execution;
- resolve interface providers;
- classify regressions;
- compute blast radius.

Those belong to `integrate-observe`.

The acceptance harness supplies a controlled canonical fixture behind a real public
`BuildTrace` object. The fixture wiring is test infrastructure, not part of the
consumer. Existing build-trace tests separately validate the canonical reader/storage
projection and authorization rules.

GitHub Actions runs this acceptance suite as its own job so a green ordinary unit-test
matrix is distinguishable from a green downstream-consumer contract.


## Canonical-only mode (0.12)

The acceptance harness now removes `PROJECT/state/image-build` before constructing
the public `BuildTrace` object. The consumer still imports only:

```python
from zog.build_trace import BuildTrace
```

Its factual digest now includes reference-closure, declared-gap and coverage dimensions
for the first/last worlds and both sides of the comparison. The consumer has no direct
knowledge of build-record's legacy aggregate completeness semantics.


## Aggregate namespace acceptance

The consumer now imports `BuildTrace` only from `zog.build_trace`. The installed-
package Actions gate runs outside the source checkout on Python 3.10 and 3.13, so it
cannot succeed through the removed repository-root package layout.
