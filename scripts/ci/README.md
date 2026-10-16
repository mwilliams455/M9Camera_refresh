# Current M9Cam CI

Adapts the build, verification and CodeQL work in PhotonCamera commit
`ac62e920a2aed5ba6b311d0b7a591d419354f022` to this patch-based repository.
The current source target is **2.89-rawgeometry1a**, based on main
`44807fb8e3b0cc18bd9ba698a86f0bef547297f4`, with RAW geometry validation.

The new workflow checks each relevant pull-request revision, main push and
manual run. It checks the event revision; it does not create a build matrix for
every intermediate commit in a batch push. Historical installer workflows remain
available, and their signing/native-library packaging is unchanged.

`prepare_source.py` reconstructs and verifies the pinned source chain using the
existing assembly and verification scripts. It then applies the upstream
CaptureControllerTest fixture fix, with teardown that restores the previous app
singleton so the fixture cannot leak into other tests. A before/after inventory
requires that this test file is the only changed scoped file. App version, Java
production code, resources, rendering assets and native source remain at the verified 2.89 candidate.
Assembly runs outside the checkout to keep historical git-format patches from
resolving against the packaging repository; the verified tree is then moved
into the workspace for CodeQL.

`verify_tests.py` preserves the existing 183-test gate and adds 22 RAW geometry
regressions. Missing suites, failures, errors and skipped tests fail
the job. Library release-resource verification remains enabled.

CodeQL v4 uses manual Java/Kotlin compilation after source reconstruction, with
incremental/build-cache reuse disabled. Diff-informed PR filtering is disabled:
Git diffs contain patch archives rather than the reconstructed Java paths, so
every run must analyze the whole reconstructed tree. Findings are uploaded to GitHub code
scanning; SARIF, verification JSON, test reports and the reconstructed Java/Kotlin
source (including compiled test sources) are also retained as a 30-day artifact. Since source files are held in
compressed patches rather than individual tracked files, GitHub source links for
findings may not resolve; use the source included with the scan artifact.
The scan covers Java/Kotlin, not native C/C++.

This verification workflow does not publish an installer. The separate
`build-m9cam-rawgeometry1a.yml` workflow packages the signed 2.89 candidate. Advancing the current CI
target requires updating the chain, baseline fingerprint source and workflow
source paths together.

Local source-only verification with an existing verified 2.89 tree:

```sh
python3 scripts/ci/prepare_source.py /tmp/m9-ci --verified-source /path/to/PhotonCamera_289
```

Android build and tests (requires the workflow's Android SDK/NDK and Java 17):

```sh
python3 scripts/ci/verify_tests.py /tmp/m9-ci/PhotonCamera_289 --run
```
