# M9Cam 3.46 JPEGPERF — faster JPEG finishing with unchanged pixels

Parent: released **3.45-performance** (version code 27345). Candidate: **3.46-jpegperf**
(27346). Test candidate only; phone timing and visual comparison are pending.

Every change is performance-only. No colour, tone, exposure, noise strength, sharpening,
falloff, JPEG quality (95) or EXIF value changes. Each change is checked byte for byte
against the 3.45 code it replaces.

## Changes

1. **Edge-placement scan on all cores.** The 12 MP read-only luminance scan that feeds the
   edge-placement diagnostic (88.7 ms on the phone in 3.43) runs on row bands from the
   existing `M9ShadingParallel1A` pool. Each band keeps private grid/histogram counters,
   and they are summed in band order. All of them are integer counts, so the result is
   identical to the serial loop. The per-pixel arithmetic is unchanged. The diagnostic
   records `scanRevision` and `scanWorkers`.
2. **JPEG encode overlaps the post-render diagnostics.** With a shared exposure plan (normal
   M9 shooting) the edge-placement selector is forced to HOLD, so the bitmap is final as
   soon as rendering ends. The quality-95 JPEG (same payload writer, same EXIF, same
   physical-ISO override) is now encoded on one background thread while the read-only
   post-render diagnostics (rendered-luma sampling, the edge-placement scan and the other
   read-only measurements) run. The render thread waits for the encode before recycling
   the bitmap and before reporting success.
   - If any code path ever asked for a DARK/BRIGHT treatment while an encode is in flight,
     the save fails loudly instead of writing a stale JPEG.
   - Without an exposure plan, in the live WYSIWYG route, or when the parity PNG is
     enabled, the 3.45 sequential path runs unchanged.
   - New diagnostics: `postRenderDiagnosticsElapsedMs`, `jpegOverlapMode` and
     `jpegOverlapWaitElapsedMs`.
3. **Lens falloff on all cores.** The 3.44 Summicron falloff pass (single-threaded,
   32-row `Mat` strips) runs on contiguous row bands. Each band uses its own strip buffers,
   and a short final strip never crosses into the next band. Pixel arithmetic is unchanged.
4. **Crash breadcrumbs without fsync.** The render-stage breadcrumb (`M9RenderCrash1D`)
   was written through `AtomicFile`, which fsyncs on every stage. It is now written to a
   temporary file and renamed. The reader is unchanged. After a power loss the breadcrumb
   might be missing, which only affects crash diagnosis, never a photo.
5. **Dynamic work-sharing in the colour library** (`libm9color`, the only native library
   that changes):
   - pre-SAT chroma preparation rows: `schedule(dynamic,1)`;
   - demosaic periphery loops: variance, quarter blend, float input and quantize use
     `schedule(dynamic, …)`;
   - the chroma noise cancel splits the frame into up to 64 preloaded bands, which an
     atomic work queue hands to the workers. Accumulators are combined in band order.

   On the phone's mixed big/little cores, the fast cores no longer wait for the slow ones.
   Every loop iteration writes only its own pixels.

## Evidence

Host results (x86, not phone timing):

- `host/native_parity346.py` (3.45 parent vs 3.46 candidate, separately compiled):
  - **Noise cancel:** pixels and integer statistics are exact against both the parent and
    the frozen scalar reference, from 64x258 up to full 12 MP. The two mean diagnostics
    agree within 1e-11 and 1e-9.
  - **Chroma preparation:** exact against the parent and the scalar `trial_prepare`, from
    1x9 up to 4096x3072, at band heights 2, 31, 128 and full height.
  - **Demosaic periphery** (`trial_variance_parallel` + `trial_reconstruct_perf`): exact
    for all four CFA layouts at 1, 3 and 8 workers, plus 12 MP.
  - **ThreadSanitizer:** no data race in the noise-cancel work queue.
- Odd-width frames with CFA layouts 1 and 3 are left out of the demosaic check. The
  unchanged 3.45 AMaZE reads one column past the edge there, so 3.45 itself is not
  repeatable from run to run. Real Bayer frames always have even widths.
- `exactperf1a/host/native_parity.py` (3.44 vs 3.46) still passes: DNG noise, phase noise,
  ThreadSanitizer and the DNG writer at -O0/-O2.
- New Android unit tests:
  - `M9EdgePlacementGateScanTest` (2) compares the banded scan with a verbatim copy of the
    3.45 loop, at 1–8 workers and full-frame sizes in both orientations.
  - `M9LensFalloffBandsTest` (2) compares banded falloff with the 3.45 whole-frame strip
    loop through a `Mat.get`/`put`-equivalent adapter, including 12 MP frames.
- All changed Java files compile against the 3.45 tree with no new errors.

CI (`build-m9cam-jpegperf346.yml`) adds:

- the existing provenance gate: the 3.44 rebuild reproduces the accepted 3.13 binaries;
- `native_delta.py`: every library in the 3.46 APK is section-identical to a 3.45 rebuild
  at the same path, except `libm9color.so`;
- all regression suites, CodeQL, and the signed, 16 KiB-aligned installer.
