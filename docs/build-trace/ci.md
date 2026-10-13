# Public GitHub Actions CI and remaining acceptance

The source repository is public. Runs on pushes and pull requests to `main` and
`unstable`, plus manual workflow dispatch. GitHub-hosted runners are used;
no private account-level cross-repository access token is required.

## Public checks

1. Core tests on Python 3.10 and 3.13 run unittest discovery with standalone
   controlled fixtures. Optional companion-dependent tests may skip.
2. Independent-consumer tests on Python 3.10 and 3.13 install build-trace and
   run the consumer harness outside the source checkout. This checks the
   `zog.build_trace` API boundary.
3. A Python 3.11 artifact job builds wheel and sdist, checks the namespace
   package and command entry point, and verifies license notices, tests,
   documentation and acceptance fixtures are shipped in the appropriate form.
4. A Python 3.11 integration job checks out the *public* build-record source at
   `a866c9c4b0dd385045f00ce2de7d809f5b67c104`, without a private token.
   It exercises `tests/test_verification_history_contract.py` against real
   public build-record constructors and rejects skipped tests in this targeted
   suite.

The four groups above verify narrower public interfaces; they do not substitute
for a complete private/full-companion run.

## Outstanding cross-component gate

The former private workflow checked out exact historical source revisions of
build-record, image-build, box-control and root-control with an account-specific
secret. That workflow is **not copied** into public Actions. The historical
results remain past evidence only and do not establish a current green full
companion gate. After all companions are published, separately define fresh
public revision pins and restore an all-companions zero-skip acceptance job
using public anonymous/read-only checkouts and reviewed third-party deps.

No CI in this public repository should require private operational evidence,
private runtime credentials, production EC2 hosts or a secret-backed repository
checkout.

## Source and distribution boundaries

The branch CI validates only source and synthetic fixtures, not an on-host
deployment, root filesystem build, image-build execution or real production
verification history. The public Git history is fresh; historical private
source revisions and evidence are deliberately not relabeled as the public
commit.

Original first-party code and documentation are licensed under
`BSD-3-Clause OR GPL-3.0-only`; see the root LICENSE and THIRD-PARTY-NOTICES.md.
The independently publishable PyPI distribution remains the aggregate `zog`
assembled by release-build, not this development component.
