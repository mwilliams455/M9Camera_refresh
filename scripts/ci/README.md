# Current M9Cam build and tests

Pull requests targeting main, pushes to main, and manual runs reconstruct
3.42-facehighlight1b (version code 27342). Run these from the repository
root using the Android and JDK versions in verify-m9cam-current.yml.

```sh
python3 scripts/ci/prepare_314.py /tmp/m9-342 --adaptive-face-highlight
bash scripts/ci/test_tracking.sh /tmp/m9-342/PhotonCamera_342
python3 scripts/ci/verify_tests.py /tmp/m9-342/PhotonCamera_342 --run
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

## 3.43 EXACTPERF1A candidate

`build-m9cam-exactperf1a.yml` reconstructs the performance-only 3.43 candidate with
`prepare_314.py <dest> --exact-perf`, rebuilds the 3.42 parent's native libraries for the
provenance gate, runs the native parity suite and regression tests, and packages the
installer. See patches/exactperf1a/README.md. The workflow above still builds 3.42.
It now runs on manual dispatch only.

## 3.46 JPEGPERF candidate

`build-m9cam-jpegperf346.yml` reconstructs 3.44, 3.45 and the 3.46 candidate with
`prepare_346.py <dest>`. It rebuilds the 3.44 native libraries for the 3.13 provenance gate
and the 3.45 native libraries for the 3.46 delta gate. Then it runs both native parity
suites and the regression tests, and packages the installer. See
patches/jpegperf346/README.md.

## 3.49 JPEGPERF candidate

`build-m9cam-jpegperf349.yml` reconstructs 3.44 through 3.49 with `prepare_349.py <dest>`.
It rebuilds the 3.44 native libraries for the 3.13 provenance gate and the 3.48 libraries
for the delta gate. It runs the 3.46 and 3.49 parity suites and the 3.47 allocation probe,
then the regression tests. It packages the installer and runs the shared-storage suite on an
Android 15 emulator. The 3.46 workflow now runs on manual dispatch only.
See patches/jpegperf349/README.md.
