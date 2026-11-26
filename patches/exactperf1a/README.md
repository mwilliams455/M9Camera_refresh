# M9Cam 3.43 EXACTPERF1A — faster JPEG/DNG saving with unchanged pixels

Parent: accepted **3.42-facehighlight1b** (version code 27342). Candidate: **3.43-exactperf1a**
(27343). Test candidate only; phone timing and visual comparison are pending.

Every change is performance-only. No colour, tone, exposure, noise strength, sharpening,
JPEG quality or DNG metadata value changes. Each kernel was compared byte for byte with the
3.42 code it replaces.

## Changes

1. **The installed app is no longer debuggable.** The shipped installer came from the
   `debug` Gradle variant, so Android ran its Java render/save code with debugging
   restrictions. `debuggable false` is set on that variant; the native CMake build type is
   pinned to `Debug` so that unchanged native libraries compile exactly as before. The DNG
   writer (`libdngCreator`) was the one renderer-path library built at `-O0`; it now
   uses `-O2` with strict IEEE floating point, as `libm9color` and `libmcraw` already do.
   Nothing in the app reads `BuildConfig.DEBUG`. As for any non-debuggable Android
   build, the APK also carries the AndroidX ART baseline profile (`assets/dexopt/`) and
   shortened resource file paths; the app reads resources by ID only, so neither changes
   behaviour, and the packager resolves menu files through the resource table.
2. **DNG noise stage on all cores.** The M9 DNG noise filter ran on one thread. Its 64-row
   bands read only the immutable source and write only their own rows, so they now run on
   up to 8 `std::thread` workers with private scratch (no second OpenMP runtime). The
   original serial `phone_noise_shaded` is kept unchanged; the production adapter calls
   the new `phone_noise_shaded_parallel`.
3. **Dynamic phase-noise scheduling** (the unmerged 2.96 PHASENOISEPERF1D change): the
   AMaZE RAW-noise tile loop uses `schedule(dynamic,1)` instead of `schedule(static)`.
   Tiles are disjoint with private scratch; arithmetic and accumulation order are unchanged.
4. **Lens-shading pass on all cores.** The production SHADINGLUMADECOMP1A per-pixel loop
   (12 MP, single-threaded Java) runs on independent row bands
   (`M9ShadingParallel1A`). Each pixel performs the same double operations in the same
   order; the Bayer plane comes from a 2x2 table built with the same resolver, which
   depends only on row/column parity. Map validation and gain decomposition are unchanged.
   A diagnostic-only `lensShadingApplyElapsedMs` field records the pass duration.
5. **DNG written once.** The RAW was written to its final name, then copied whole into a
   staging DNG to append the Leica profile, then renamed back. The DNG bytes are now
   written straight into the same-directory `M9_PROFILE_PENDING_*.dng` staging file, the
   profile is appended there in place (`M9DngProfileWriter.embedInPlace`), and the file is
   published by rename. The final name still supplies the capture date and the optional
   unfiltered-pair name. If the profile append fails, the staging file is truncated and its
   header restored to the exact RAW bytes before publication, matching the previous
   "bypassed, original RAW preserved" behaviour. If even that restoration fails, the
   staging file is discarded and the save reports failure.

## Evidence

Host results (`HOST_VERIFICATION.json`, x86, not phone timing):

- `host/native_parity.py`: 87/87 byte-exact cases. DNG noise: parent serial vs candidate
  at 1–64 workers, modes 1 and 2, full 12 MP frames, and the production RAW16 adapter end
  to end. Phase noise: parent static vs candidate dynamic at 1–8 workers, including
  clustered clipped highlights, and the parent against its scalar oracle.
- ThreadSanitizer reports no data race in the threaded DNG noise kernel.
- The production `dngCreator.cpp`, built at `-O0` and `-O2`, writes byte-identical DNGs
  (four CFA layouts, 12 MP and small frames, gain map, matrices, noise profile).
- New Android unit tests: `M9ShadingParallel1ATest` (4) compares the parallel pass with a
  verbatim copy of the 3.42 serial loops for every CFA layout, origin and worker count;
  `M9DngProfileStagingTest` (3) shows the in-place profile append produces the same bytes
  as the previous copy-then-append, and that failures before and after bytes are
  appended leave the staging DNG identical to the written RAW. Deliberate mutations
  (rounding, rollback) are detected.
- Host timings on 12 MP: DNG noise 620 → 199 ms (4 threads); phase noise ~570 → ~410 ms
  (4 workers, clipped window); Java shading 104–141 → 33–41 ms when JIT-compiled
  (4.6–6.3 s if interpreted); DNG serializer 172 → 118 ms.

CI (`.github/workflows/build-m9cam-exactperf1a.yml`):

- reconstructs 3.43 with `prepare_314.py --exact-perf` (pin `source-343.sha256`) and derives
  the 3.42 parent by reversing only `source.patch`;
- rebuilds the parent's native libraries at the accepted build path and requires
  `libm9color`, `libm9dngnoise` and `libdngCreator` to match the accepted 3.13 binaries'
  `.text/.rodata/.data.rel.ro/.data` exactly, every other source-built library to be
  identical between the parent and candidate builds, and the three changed libraries to
  differ (`native_provenance.py`);
- runs the native parity suite, all selected Android regression suites, CodeQL, and
  `package.py`, which keeps the 3.13 native libraries and assets except the six rebuilt
  library files, checks signing, 16 KiB alignment, version, menus and that the
  installer is not debuggable.

## CI result

[Run 45822753028](https://github.com/mwilliams455/M9Camera_refresh/actions/runs/45822753028)
passed every step. The 3.42 parent rebuild reproduced all 19 accepted source-built native
libraries exactly; in 3.43 only `libm9color`, `libm9dngnoise` and `libdngCreator` changed.
Installer `M9Cam_3.43_EXACTPERF1A.apk`, SHA-256
`54dc68d1a19d70bc4d3f190fee8cfe4501d56b9211892d4d50c1e4514198387e`, signed with the existing
certificate, not debuggable (`PACKAGED_VERIFICATION.json`).

## Phone check

Install over 3.42 (same signature). With "Save diagnostic files" on, take the same scene
with the same lens, exposure and save mode in 3.42 and 3.43: one warm-up shot, then at
least five. Compare the PRIMARY timings `renderElapsedMs`, `renderCoreElapsedMs`,
`amazePhaseNoiseMs`, `jpegEncodeWriteElapsedMs` and `dngSaveElapsedMs`, and check JPEG/DNG
colour and detail side by side. 3.43 adds the diagnostic-only `lensShadingApplyElapsedMs`
(with `lensShadingApplyWorkers`) around the shading pass; 3.42 has no equivalent field, so
its effect shows inside `renderCoreElapsedMs`. The DNG profile
report now shows `storagePolicy = same_directory_single_staging_inplace_append_rename_publish`.
Scene/ISO differences make single timings directional only.
