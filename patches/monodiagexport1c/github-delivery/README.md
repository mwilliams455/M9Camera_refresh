# M9Cam 2.81 signed installer delivery

The workflow **Downloadable signed M9Cam 2.81 installer** restores the exact verified
2.81 installer from the pinned Android CI artifact. It does not rebuild or change
the camera application.

## Download and install

1. Open the successful delivery workflow run on GitHub.
2. Under **Artifacts**, download **M9Cam-2.81-READY-TO-INSTALL**. GitHub sign-in may be required.
3. Extract the ZIP and install `M9Cam_2.81_MONODIAGEXPORT1C.apk` over the existing app.

The artifact contains the APK and `SHA256SUMS.txt`. The expected APK is
119,634,741 bytes, with SHA-256:

```text
e25a94426b8de7b44cf529be5f0a957a0dc047c29d7242bdb8ca976efafc8f15
```

Package: `com.m9project.m9cam.photon`; version `2.81-monodiagexport1c`;
version code `27281`.

The workflow enforces the exact APK hash, ZIP CRCs, diagnostic DEX markers,
Android v2 signature and accepted signing certificate, package/version identity,
and 16 KiB ZIP alignment before uploading the installer. Artifact retention is
90 days from upload.

## Local restoration

Download and extract the pinned `monodiagexport1c-android-build` artifact from
run 38146778173, then run from the repository root:

```sh
python3 patches/monodiagexport1c/github-delivery/restore.py /path/to/source-artifact /path/to/new-output
```

Java 17 is required. The pinned source artifact expires on 18 October 2026;
the restored delivery artifact has its own retention period. Never substitute
the intermediate debug APK for this signed installer or change a pinned hash
to bypass verification.

## Phone validation

With Monochrom diagnostics enabled, reopen the app. If the exposure-preview
warning recurs, capture its bracketed reason code or the
`MONO_EXPOSURE_READINESS_*.json` record in `DCIM/PhotonCamera/Raw`.
A successful photo taken within two minutes in the same camera session can
also carry the earlier failure in its PRIMARY diagnostic.

This build improves rejection evidence delivery. It does not establish or fix
the underlying intermittent shutter rejection. PR #99 remains a draft; phone
validation is pending.
