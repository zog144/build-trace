# build-trace public source and dependency notices

First-party build-trace code, documentation and controlled fixtures included in
this public repository are licensed under `BSD-3-Clause OR GPL-3.0-only`.
See [LICENSE](LICENSE), [LICENSES/BSD-3-Clause.txt](LICENSES/BSD-3-Clause.txt)
and [LICENSES/GPL-3.0-only.txt](LICENSES/GPL-3.0-only.txt).

## Separate companion projects

build-record, image-build, box-control, root-control and integrate-observe are
separately maintained Zog projects. This repository does not vendor their
source, private observations, build host state or dependencies. When acquired
separately, those components and third-party build/test dependencies retain
their respective licenses and associated notices.

Core build-trace inspection requires no separately declared runtime dependency.
Companion tests may use independently installed build-record, dbus-next,
pytest and other separately obtained software. License review must be repeated
for any future redistribution that bundles additional dependencies or assets.

## Historical evidence boundary

Synthetic fixture credentials, source URLs and record identities in the test
suite are not production credentials or production host details. No private
Git history, operational evidence, historical Actions logs or private
companion checkout tokens are included in this public export.
The first-party grant does not retroactively relicense previous private commits.

This repository is a development component. Public PyPI distributions remain
owned by release-build's aggregated `zog` project; there is no independently
approved build-trace upload to PyPI.
