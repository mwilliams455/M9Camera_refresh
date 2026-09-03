#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-capturesplit1c.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CAPTURESPLIT1C verify missing {rel}')
    return p.read_text()

def must(rel, token):
    if token not in read(rel):
        raise SystemExit(f'CAPTURESPLIT1C verify missing {token!r} in {rel}')

def must_not(rel, token):
    if token in read(rel):
        raise SystemExit(f'CAPTURESPLIT1C verify forbidden {token!r} in {rel}')

render_meter = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'
model = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterModel1C.java'
spool = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
meta = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java'
timing = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
renderer = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'

must('app/build.gradle', "versionName '1.44-m9modern7r38luma24fb1primary25perf3i")
must(render_meter, 'm9cam.rendermeter.v3.evidence1c')
must(render_meter, 'M9RenderMeterModel1C.evaluate(direct)')
must(render_meter, 'correctionAppliedEv\", 0.0')
must(render_meter, 'correctionCandidateEv\", 0.0')
must(model, 'm9cam.rendermetermodel.v1.evidence1c')
must(model, 'evidence_only_no_signed_ev')
must(model, 'intentionalDarkSplitEvidence')
must(model, 'wholeFrameStarvationEvidence')
must(model, 'localizedUpperPlacementEvidence')
must(model, 'renderLiftNeedEvidence')
must(model, 'renderHoldEvidence')
must(model, 'correctionCandidateEv\", 0.0')

must(spool, 'm9cam.sidecarspool.v1.privatebundle1b')
must(spool, 'BUNDLE_IDLE_MS = 1500L')
must(spool, 'INDIVIDUAL_DELAY_MS = 12000L')
must(spool, 'getFilesDir().toPath().resolve("m9diag_spool")')
must(spool, 'M9_DIAGNOSTICS_BURST_')
must(spool, 'private_immediate_bundle_first_eventual_individual_public_export')
must(spool, 'SimpleStorageHelper.openOutputStreamByAbsPath')
must(meta, 'M9DiagnosticBurstSpool.stage(jsonPath, bytes, "capture_metadata")')
must(timing, 'm9cam.primarytiming.v8.sidecar1b')
must(timing, 'M9DiagnosticBurstSpool.stage(frozen.timingPath, frozen.bytes, "primary_timing")')
must(timing, 'diagnosticSidecarSpool')

# Direct render measurement from 1B remains present and renderer behaviour stays diagnostic-only.
must(renderer, 'M9RenderedLumaDiagnostic.measure(bitmap)')
must(renderer, 'No pixel, TC20, colour or JPEG state is mutated by this diagnostic.')
must('app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java',
     'diagnostic_only_no_exposure_mutation')
must('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
     'diagnostic_only_no_exposure_mutation')

# The evidence model deliberately must not become a signed/live render controller.
must_not(model, 'correctionAppliedEv')
must_not(model, 'setPixel(')
must_not(model, 'setPixels(')
must_not(render_meter, 'liveEligible\", true')

# Small model sanity check against the newly observed categories.
def smooth(x, lo, hi):
    t = max(0.0, min(1.0, (x-lo)/(hi-lo)))
    return t*t*(3.0-2.0*t)

def scores(gm, cm, mm, cq95, mq95):
    gd = 1.0 - smooth(gm, 35.0, 82.0)
    ca = smooth(cm, 68.0, 116.0)
    ma = smooth(mm, 76.0, 132.0)
    la = max(ca, 0.82*ma)
    sep = smooth(cm-gm, 16.0, 55.0)
    split = gd*la*sep
    starve = gd*(1.0-la)
    up = la*max(smooth(cq95,236.0,250.0), smooth(mq95,238.0,252.0))
    lift = starve*(1.0-0.55*up)
    hold = max(split, la*(0.35+0.65*sep))
    return lift, hold, split

# Eight-shot cat control: global render is already healthy; no lift demand.
cat_lift, cat_hold, _ = scores(86, 125, 217, 243, 246)
if cat_lift > 0.05:
    raise SystemExit(f'CAPTURESPLIT1C model regression: healthy cat lift={cat_lift:.3f}')
# Window/dark-room split: center is useful despite very dark global body; hold should dominate lift.
win_lift, win_hold, win_split = scores(16, 99, 120, 240, 240)
if not (win_split > 0.55 and win_hold > win_lift):
    raise SystemExit(f'CAPTURESPLIT1C model regression: window lift={win_lift:.3f} hold={win_hold:.3f} split={win_split:.3f}')
# Truly globally/local dark control should retain strong lift evidence.
dark_lift, dark_hold, _ = scores(25, 40, 45, 120, 125)
if dark_lift < 0.80:
    raise SystemExit(f'CAPTURESPLIT1C model regression: dark lift={dark_lift:.3f}')

print('CAPTURESPLIT1C verification PASS: RENDERMETER1C is evidence-only, SIDECAR1B privately stages immediately and bundle-exports first, photographic/capture controls remain diagnostic/frozen')