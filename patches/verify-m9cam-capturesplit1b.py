#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-capturesplit1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CAPTURESPLIT1B verify missing: {rel}')
    return p.read_text()

def must(rel, marker):
    t = text(rel)
    if marker not in t:
        raise SystemExit(f'CAPTURESPLIT1B verify missing marker in {rel}: {marker}')
    print(f'OK   {rel}: {marker}')

def must_not(rel, marker):
    t = text(rel)
    if marker in t:
        raise SystemExit(f'CAPTURESPLIT1B verify forbidden marker in {rel}: {marker}')
    print(f'OK   {rel}: no {marker}')

scene = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
coord = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
renderer = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
render_luma = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderedLumaDiagnostic.java'
render_meter = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'
sidecar = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticSidecarIO.java'
meta = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java'
timing = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'

# Capture/render split remains diagnostic and capture math stays at 1A.
must(scene, 'm9cam.sceneexposure.v8.renderaware1h')
must(scene, 'diagnostic_only_no_exposure_mutation')
must(coord, 'm9cam.exposuresplit.v1.capturemeter1a.temporal1a')
must(coord, 'liveEligible", false')
must(coord, 'stabilizedCaptureTargetEv')
must(coord, 'jpeg_tonal_placement_must_be_evaluated_separately_from_raw_capture')

# Direct rendered luma is read-only and sparse; no pixel writing/rescaling is allowed.
must(render_luma, 'm9cam.renderedluma.v1.grid64')
must(render_luma, 'SAMPLE_LONG_SIDE = 64')
must(render_luma, 'bitmap.getPixel')
must(render_luma, 'finished_display_bitmap')
must(render_luma, 'middleCenter33')
must_not(render_luma, 'setPixel')
must_not(render_luma, 'createScaledBitmap')
must_not(render_luma, 'compress(')

rt = text(renderer)
if rt.count('M9RenderedLumaDiagnostic.measure(bitmap)') != 1:
    raise SystemExit('CAPTURESPLIT1B verify: direct rendered luma must be sampled exactly once')
if rt.index('M9RenderedLumaDiagnostic.measure(bitmap)') > rt.index('saveBitmapAsJPGPayloadM9'):
    raise SystemExit('CAPTURESPLIT1B verify: rendered luma must be sampled before JPEG helper recycles bitmap')
print('OK   renderer direct-luma sampling occurs exactly once before JPEG payload save')
must(renderer, 'M9RenderMeterDiagnostic.evaluate(diag)')

must(render_meter, 'm9cam.rendermeter.v2.directluma1b')
must(render_meter, 'diagnostic_only_no_renderer_mutation')
must(render_meter, 'correctionAppliedEv", 0.0')
must(render_meter, 'correctionCandidateEv", 0.0')
must(render_meter, 'disabled_pending_paired_direct_luma_calibration')
must(render_meter, 'direct_rendered_luma_measured_calibration_pending')

# SIDECAR1A changes development JSON transport only and exposes backlog telemetry.
must(sidecar, 'm9cam.sidecario.v1.directfirst1a')
must(sidecar, 'Files.newOutputStream(path)')
must(sidecar, 'SimpleStorageHelper.openOutputStreamByAbsPath')
must(sidecar, 'direct_filesystem_first_then_saf_fallback')
must(sidecar, 'maxPending')
must(sidecar, 'averagePersistElapsedMs')
st = text(sidecar)
if st.index('Files.newOutputStream(path)') > st.index('SimpleStorageHelper.openOutputStreamByAbsPath'):
    raise SystemExit('CAPTURESPLIT1B verify: sidecar persistence is not direct-filesystem-first')
print('OK   SIDECAR1A direct-filesystem-first ordering verified')

must(meta, 'M9DiagnosticSidecarIO.noteScheduled("capture_metadata")')
must(meta, 'M9DiagnosticSidecarIO.persist(jsonPath, bytes, "capture_metadata")')
must_not(meta, 'SimpleStorageHelper.openOutputStreamByAbsPath')

must(timing, 'm9cam.primarytiming.v7.sidecar1a')
must(timing, 'SIDECAR1A')
must(timing, 'M9DiagnosticSidecarIO.noteScheduled("primary_timing")')
must(timing, 'M9DiagnosticSidecarIO.persist(frozen.timingPath, frozen.bytes, "primary_timing")')
must(timing, 'root.put("diagnosticSidecarIo", M9DiagnosticSidecarIO.snapshotJson())')
must_not(timing, 'SimpleStorageHelper.openOutputStreamByAbsPath')

# Frozen photographic seams still have the known production markers.
must('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java', 'M9ExposureAudit')
must('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java', 'MOTION_ACTIVATE = 0.52')
must('app/src/main/cpp/m9color_jni.cpp', 'renderBlockParallel')
must(renderer, 'saveBitmapAsJPGPayloadM9')
must(renderer, 'JPEG_QUALITY = 95')
must(renderer, 'TC20NATIVE1B')
must(renderer, 'COLORNATIVE2A')

must('app/build.gradle', "versionName '1.43-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1brendermeter1bsidecar1a'")

print('CAPTURESPLIT1B PASS: direct finished-bitmap luma is observational only; sidecar transport is direct-first with telemetry; capture allocation, SCENEEXPOSURE, TC20/native colour and JPEG/DNG photographic paths remain frozen')
