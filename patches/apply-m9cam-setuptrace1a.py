#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-setuptrace1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not renderer_path.exists(): raise SystemExit(f'missing renderer: {renderer_path}')
s = renderer_path.read_text()

old = '''            long setupStartedNs = System.nanoTime();\n            ensureOpenCv();\n            if (frame == null || frame.buffer == null) throw new IllegalArgumentException("missing RAW frame");\n            // BESTFIT2A_LIVE1 capture-specific immutable evidence bridge.\n            final byte[] edgePlacementCaptureBytes = M9DeferredMetadataStore.consumeRenderSnapshotForDng(dngPath);\n\n            Parameters params = new Parameters();\n            params.FillConstParameters(characteristics, new Point(frame.width, frame.height));\n'''
new = '''            long setupStartedNs = System.nanoTime();\n            long setupTraceStageStartedNs = System.nanoTime();\n            ensureOpenCv();\n            final long setupEnsureOpenCvElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n            if (frame == null || frame.buffer == null) throw new IllegalArgumentException("missing RAW frame");\n            // BESTFIT2A_LIVE1 capture-specific immutable evidence bridge.\n            setupTraceStageStartedNs = System.nanoTime();\n            final byte[] edgePlacementCaptureBytes = M9DeferredMetadataStore.consumeRenderSnapshotForDng(dngPath);\n            final long setupSnapshotLookupElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n\n            Parameters params = new Parameters();\n            setupTraceStageStartedNs = System.nanoTime();\n            params.FillConstParameters(characteristics, new Point(frame.width, frame.height));\n            final long setupFillConstElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n'''
if 'setupEnsureOpenCvElapsedMs' not in s:
    if s.count(old) != 1: raise SystemExit('SETUPTRACE1A setup-start anchor missing/ambiguous')
    s = s.replace(old, new, 1)

old = '''            params.FillDynamicParameters(captureResult, captureRequest, iso);\n            params.cameraRotation = cameraRotation;\n\n            // DEVICEPORT1A/CFAABSTRACT1A: probe source RAW metadata before the frozen\n'''
new = '''            setupTraceStageStartedNs = System.nanoTime();\n            params.FillDynamicParameters(captureResult, captureRequest, iso);\n            final long setupFillDynamicElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n            params.cameraRotation = cameraRotation;\n\n            // DEVICEPORT1A/CFAABSTRACT1A: probe source RAW metadata before the frozen\n'''
if 'setupFillDynamicElapsedMs' not in s:
    if s.count(old) != 1: raise SystemExit('SETUPTRACE1A FillDynamic anchor missing/ambiguous')
    s = s.replace(old, new, 1)

old = '''            M9DevicePortAudit1A.captureAndWrite(\n                    dngPath,\n                    frame.width,\n                    frame.height,\n                    frame.buffer != null ? frame.buffer.capacity() : -1,\n                    params,\n                    characteristics,\n                    captureResult,\n                    captureRequest);\n\n            // CFAAUTHORITY1A: Parameters.FillConstParameters permits Photon's global CFA\n'''
new = '''            setupTraceStageStartedNs = System.nanoTime();\n            M9DevicePortAudit1A.captureAndWrite(\n                    dngPath,\n                    frame.width,\n                    frame.height,\n                    frame.buffer != null ? frame.buffer.capacity() : -1,\n                    params,\n                    characteristics,\n                    captureResult,\n                    captureRequest);\n            final long setupDevicePortAuditElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n\n            // CFAAUTHORITY1A: Parameters.FillConstParameters permits Photon's global CFA\n'''
if 'setupDevicePortAuditElapsedMs' not in s:
    if s.count(old) != 1: raise SystemExit('SETUPTRACE1A DEVICEPORT anchor missing/ambiguous')
    s = s.replace(old, new, 1)

old = '''            CaptureResult diagnosticCaptureResult1A = M9PhysicalCaptureResult1A.resolve(\n                    captureResult, params.cameraID);\n            // M9RAWSHADING1A: metadata/semantics only. No GainMap is applied to RAW here.\n            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(\n                    dngPath, frame.width, frame.height, params, characteristics,\n                    diagnosticCaptureResult1A, captureRequest);\n            // BASISHSM1P-NATIVESOURCE1A: native Camera2/DNG source characterization is now the production source transform.\n            JSONObject sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(\n                    dngPath, params, characteristics, diagnosticCaptureResult1A);\n'''
new = '''            setupTraceStageStartedNs = System.nanoTime();\n            CaptureResult diagnosticCaptureResult1A = M9PhysicalCaptureResult1A.resolve(\n                    captureResult, params.cameraID);\n            final long setupPhysicalResultResolveElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n            // M9RAWSHADING1A: metadata/semantics only. No GainMap is applied to RAW here.\n            setupTraceStageStartedNs = System.nanoTime();\n            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(\n                    dngPath, frame.width, frame.height, params, characteristics,\n                    diagnosticCaptureResult1A, captureRequest);\n            final long setupRawShadingAuditElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n            // BASISHSM1P-NATIVESOURCE1A: native Camera2/DNG source characterization is now the production source transform.\n            setupTraceStageStartedNs = System.nanoTime();\n            JSONObject sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(\n                    dngPath, params, characteristics, diagnosticCaptureResult1A);\n            final long setupSourceCalibrationAuditElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n'''
if 'setupSourceCalibrationAuditElapsedMs' not in s:
    if s.count(old) != 1: raise SystemExit('SETUPTRACE1A audit anchors missing/ambiguous')
    s = s.replace(old, new, 1)

old = '''            float[] encodedBlack = new float[4];\n            for (int i = 0; i < 4; i++) {\n                int q = ((short)params.blackLevel[i]) & 0xffff;\n                encodedBlack[i] = q;\n            }\n            long setupElapsedMs = (System.nanoTime() - setupStartedNs) / 1_000_000L;\n'''
new = '''            setupTraceStageStartedNs = System.nanoTime();\n            float[] encodedBlack = new float[4];\n            for (int i = 0; i < 4; i++) {\n                int q = ((short)params.blackLevel[i]) & 0xffff;\n                encodedBlack[i] = q;\n            }\n            final long setupFinalBookkeepingElapsedMs = (System.nanoTime() - setupTraceStageStartedNs) / 1_000_000L;\n            long setupElapsedMs = (System.nanoTime() - setupStartedNs) / 1_000_000L;\n'''
if 'setupFinalBookkeepingElapsedMs' not in s:
    if s.count(old) != 1: raise SystemExit('SETUPTRACE1A bookkeeping anchor missing/ambiguous')
    s = s.replace(old, new, 1)

old = '''            long renderCoreElapsedMs = (System.nanoTime() - renderCoreStartedNs) / 1_000_000L;\n            out.diagnostics.put("cfaAuthority", sourceCfaAuthority);\n'''
new = '''            long renderCoreElapsedMs = (System.nanoTime() - renderCoreStartedNs) / 1_000_000L;\n            JSONObject setupTrace1A = new JSONObject();\n            setupTrace1A.put("schema", "m9cam.setuptrace.v1a.readonly");\n            setupTrace1A.put("diagnosticOnly", true);\n            setupTrace1A.put("totalSetupElapsedMs", setupElapsedMs);\n            setupTrace1A.put("ensureOpenCvElapsedMs", setupEnsureOpenCvElapsedMs);\n            setupTrace1A.put("snapshotLookupElapsedMs", setupSnapshotLookupElapsedMs);\n            setupTrace1A.put("fillConstParametersElapsedMs", setupFillConstElapsedMs);\n            setupTrace1A.put("fillDynamicParametersElapsedMs", setupFillDynamicElapsedMs);\n            setupTrace1A.put("devicePortAuditElapsedMs", setupDevicePortAuditElapsedMs);\n            setupTrace1A.put("physicalResultResolveElapsedMs", setupPhysicalResultResolveElapsedMs);\n            setupTrace1A.put("rawShadingAuditElapsedMs", setupRawShadingAuditElapsedMs);\n            setupTrace1A.put("sourceCalibrationAuditElapsedMs", setupSourceCalibrationAuditElapsedMs);\n            setupTrace1A.put("finalBookkeepingElapsedMs", setupFinalBookkeepingElapsedMs);\n            long setupTraceAccountedMs = setupEnsureOpenCvElapsedMs + setupSnapshotLookupElapsedMs\n                    + setupFillConstElapsedMs + setupFillDynamicElapsedMs + setupDevicePortAuditElapsedMs\n                    + setupPhysicalResultResolveElapsedMs + setupRawShadingAuditElapsedMs\n                    + setupSourceCalibrationAuditElapsedMs + setupFinalBookkeepingElapsedMs;\n            setupTrace1A.put("accountedElapsedMs", setupTraceAccountedMs);\n            setupTrace1A.put("unaccountedElapsedMs", Math.max(0L, setupElapsedMs - setupTraceAccountedMs));\n            out.diagnostics.put("setupTrace1A", setupTrace1A);\n            out.diagnostics.put("cfaAuthority", sourceCfaAuthority);\n'''
if 'm9cam.setuptrace.v1a.readonly' not in s:
    if s.count(old) != 1: raise SystemExit('SETUPTRACE1A diagnostics anchor missing/ambiguous')
    s = s.replace(old, new, 1)

renderer_path.write_text(s)

# TARGETINPUTADAPTER1A-PHYSICALSOURCEAGNOSTIC1A: this is deliberately chained
# after SETUPTRACE so the existing proven assembly recipe stays unchanged while
# the final pixel path becomes camera-array/role agnostic. Both tools fail closed.
patch_dir = Path(__file__).resolve().parent
saved_argv = list(sys.argv)
try:
    for tool_name in ('apply-m9cam-physicalsourceagnostic1a.py',
                      'verify-m9cam-physicalsourceagnostic1a.py'):
        tool = patch_dir / tool_name
        if not tool.exists():
            raise SystemExit(f'SETUPTRACE1A missing chained physical-source tool: {tool}')
        sys.argv = [str(tool), str(root)]
        runpy.run_path(str(tool), run_name='__main__')
finally:
    sys.argv = saved_argv

print('SETUPTRACE1A applied')
print(' - pre-render setup split into OpenCV, snapshot, FillConst, FillDynamic, DEVICEPORT, physical-result, shading, SOURCECAL and bookkeeping timings')
print(' - PHYSICALSOURCEAGNOSTIC1A chained after trace: camera ID is provenance/lookup only; geometry/CFA/source metadata drive pixels')