# Current M9Cam build and tests

Pull requests targeting main, pushes to main, and manual runs reconstruct
3.26-headbody1a (version code 27326). Run these from the repository
root using the Android and JDK versions in verify-m9cam-current.yml.

```sh
python3 scripts/ci/prepare_314.py /tmp/m9-326 --head-body
bash scripts/ci/test_tracking.sh /tmp/m9-326/PhotonCamera_326
python3 scripts/ci/verify_tests.py /tmp/m9-326/PhotonCamera_326 --run
```

The accepted source descends from 2.95 through the focus and tracking patches.
Reconstruction verifies the models and scoped source digest before applying
the test-only CaptureController fixture. The 2.96 experiment retains its
own historical reconstruction entry point, prepare_source.py.

The workflow runs the tracking policy programs against the reconstructed
classes and checks the selected Android suites against their JUnit XML counts.
It verifies library release resources and runs CodeQL on the same Java/Kotlin
source during Gradle compilation. The verification artifact includes test
reports, source fingerprints, scanned sources and SARIF.

The installer uses the original signing identity and verifies 16 KiB alignment.
The two archives in patches/trackingrecovery1a/baseline contain the 21 native
libraries that differ from or are missing in the Gradle APK. They were extracted
from the signed 3.13 APK (SHA-256
`167393ccfdc25c5d0c232a6012b213b8e5cf1b094ee1a35e540c75faf2e7623c`).
The adjacent manifest pins all 37 native libraries and 301 assets. Packaging
verifies every entry and the signed output. All packaging inputs are available
independently of previous Actions runs.
