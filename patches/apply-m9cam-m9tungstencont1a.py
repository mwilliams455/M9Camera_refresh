#!/usr/bin/env python3
"""Keep the M9 TG1 tungsten guard alive across transient GL2A source-contract gaps."""
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9tungstencont1a.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

gpu = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9GpuPreview2A.java"
continuity = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewSourceContinuity1A.java"
camera = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
state = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewFrameState1W.java"
renderer = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
shader = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
gradle = root / "app/build.gradle"
still = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"

expected = {
    gpu: "ab43ef6e008ec62fd0b6a56ba216178717d91810279db36c522aff015fbab81e",
    camera: "25b8e0ccecebc3358a7def4c1938cb38d6aefdc372e1e3c7d56598eacdd67f8c",
    state: "bd3f93f96ca4da30f4f024cb4b56b7de92bad38816d5aa4d3896ac70425cdfc8",
    renderer: "bd62636556af0c45a4685b8b075b6d548ae948118bd6b7ceff348474f360c4d4",
    shader: "8017fc945443515517e0e025e7498da81f7f8993233f3b92ac1e2589459e19e9",
    gradle: "50e63247bc15b4fd878c4b3548a4158bf3aa72d2508106b09719b0e0d9fc12a7",
    still: "a7dfa41df5eaa92c69ef4236e6d697f10e6681cadfbfc46d66869628d405ab56",
}
for path, want in expected.items():
    if not path.exists() or sha(path) != want:
        raise SystemExit("M9TUNGSTENCONT1A baseline mismatch: " + str(path))
if continuity.exists():
    raise SystemExit("M9TUNGSTENCONT1A unexpected existing continuity helper")

def one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"M9TUNGSTENCONT1A {label}: expected 1 anchor, found {count}")
    return text.replace(old, new, 1)

g = gpu.read_text()
g = one(g,
"""        public final float tungstenWeight;
        public final int postRawBoost;
        private final float[] undo, source, target, white;
""",
"""        public final float tungstenWeight;
        public final int postRawBoost;
        public final boolean continuityHeld;
        public final String continuityContractReason;
        public final long continuityLastGoodAgeMs;
        private final float[] undo, source, target, white;
""", "Frame continuity fields")
g = one(g,
"""        private Frame(String reason,String id,float[] requested,float[][] curves,double error) {
            ready=false; this.reason=reason; cameraId=id; tungstenWeight=0; postRawBoost=100;
            undo=source=target=new float[]{1,0,0,0,1,0,0,0,1}; white=new float[]{1,1,1}; inverse=new byte[0];
""",
"""        private Frame(String reason,String id,float[] requested,float[][] curves,double error) {
            ready=false; this.reason=reason; cameraId=id; tungstenWeight=0; postRawBoost=100;
            continuityHeld=false; continuityContractReason=reason; continuityLastGoodAgeMs=-1;
            undo=source=target=new float[]{1,0,0,0,1,0,0,0,1}; white=new float[]{1,1,1}; inverse=new byte[0];
""", "fallback continuity defaults")
g = one(g,
"""        private Frame(String id,float[] undo,float[] source,float[] target,double[] white,
                float tungsten,byte[] inverse,int boost,float[][] curves,float[] requested,double error) {
            ready=true; reason="controlled_curve_agrees_with_request_not_pixel_verified"; cameraId=id;
            this.undo=undo.clone(); this.source=source.clone(); this.target=target.clone();
""",
"""        private Frame(String id,float[] undo,float[] source,float[] target,double[] white,
                float tungsten,byte[] inverse,int boost,float[][] curves,float[] requested,double error) {
            ready=true; reason="controlled_curve_agrees_with_request_not_pixel_verified"; cameraId=id;
            continuityHeld=false; continuityContractReason=reason; continuityLastGoodAgeMs=0;
            this.undo=undo.clone(); this.source=source.clone(); this.target=target.clone();
""", "ready continuity defaults")
g = one(g,
"""        public static Frame fallback(String reason) { return new Frame(reason); }
        public float[] matrix(int index) { return (index==0?undo:index==1?source:target).clone(); }
""",
"""        private Frame(Frame base,String contractReason,long ageMs) {
            ready=true; reason="held_last_valid_source"; cameraId=base.cameraId;
            tungstenWeight=base.tungstenWeight; postRawBoost=base.postRawBoost;
            continuityHeld=true; continuityContractReason=contractReason;
            continuityLastGoodAgeMs=Math.max(0L,ageMs);
            undo=base.undo; source=base.source; target=base.target; white=base.white;
            inverse=base.inverse; reportedCurves=base.reportedCurves;
            requestedCurve=base.requestedCurve; curveError=base.curveError;
        }
        public static Frame fallback(String reason) { return new Frame(reason); }
        public Frame heldForContinuity(String contractReason,long ageMs) {
            return ready ? new Frame(this,contractReason,ageMs) : this;
        }
        public float[] matrix(int index) { return (index==0?undo:index==1?source:target).clone(); }
""", "held frame factory")
g = one(g,
"""                o.put("revision",REVISION).put("ready",ready).put("reason",reason).put("cameraId",cameraId);
                o.put("inputDomain",ready?"reported_contrast_curve_OES_reconstructed_sensor_RGB":"processed_OES_exposure_only_fallback");
""",
"""                o.put("revision",REVISION).put("ready",ready).put("reason",reason).put("cameraId",cameraId);
                o.put("continuityRevision","M9TUNGSTENCONT1A");
                o.put("continuityHeld",continuityHeld);
                o.put("currentContractReason",continuityContractReason);
                o.put("lastGoodAgeMs",continuityLastGoodAgeMs>=0?continuityLastGoodAgeMs:JSONObject.NULL);
                o.put("tungstenGuardPolicy",ready
                        ? (continuityHeld?"held_source_current_live_TG1":"native_source_TG1")
                        : "OES_fallback_current_live_TG1");
                o.put("inputDomain",ready?"reported_contrast_curve_OES_reconstructed_sensor_RGB":"processed_OES_exposure_only_fallback");
""", "continuity diagnostics")
gpu.write_text(g)

continuity.parent.mkdir(parents=True, exist_ok=True)
continuity.write_text("""package com.particlesdevs.photoncamera.m9.preview;

/**
 * M9TUNGSTENCONT1A.
 *
 * The raw GL2A/2F source contract remains fail-closed. This outer continuity
 * layer only holds the most recent fully valid source for a short same-camera
 * interval so a transient Camera2 metadata hole cannot flash back to vendor
 * colour. After the hold expires, the source still falls back normally; TG1 is
 * kept independently by the renderer from the live illuminant state.
 */
public final class M9PreviewSourceContinuity1A {
    public static final String REVISION = "M9TUNGSTENCONT1A";
    public static final long HOLD_LAST_GOOD_NS = 1_000_000_000L;
    private static M9GpuPreview2A.Frame lastGood;
    private static long lastGoodNs = -1L;

    private M9PreviewSourceContinuity1A() {}

    public static synchronized M9GpuPreview2A.Frame resolve(
            M9GpuPreview2A.Frame current, String cameraId, long nowNs) {
        if (current == null) current = M9GpuPreview2A.Frame.fallback("null_source_contract");
        String id = cameraId == null ? "" : cameraId;

        if (current.ready) {
            lastGood = current;
            lastGoodNs = nowNs;
            return current;
        }

        if (lastGood != null && !id.isEmpty() && !id.equals(lastGood.cameraId)) {
            lastGood = null;
            lastGoodNs = -1L;
            return current;
        }

        if (lastGood != null && id.equals(lastGood.cameraId)
                && lastGoodNs >= 0L && nowNs >= lastGoodNs) {
            long ageNs = nowNs - lastGoodNs;
            if (ageNs <= HOLD_LAST_GOOD_NS) {
                return lastGood.heldForContinuity(current.reason, ageNs / 1_000_000L);
            }
        }
        return current;
    }

    public static synchronized void reset() {
        lastGood = null;
        lastGoodNs = -1L;
    }
}
""")

c = camera.read_text()
c = one(c,
"""                        com.particlesdevs.photoncamera.m9.preview.M9GpuPreview2A.from(
                                CaptureController.mCameraCharacteristics, result,
                                PhotonCamera.getSettings().mCameraID)));
""",
"""                        com.particlesdevs.photoncamera.m9.preview.M9PreviewSourceContinuity1A.resolve(
                                com.particlesdevs.photoncamera.m9.preview.M9GpuPreview2A.from(
                                        CaptureController.mCameraCharacteristics, result,
                                        PhotonCamera.getSettings().mCameraID),
                                PhotonCamera.getSettings().mCameraID,
                                android.os.SystemClock.elapsedRealtimeNanos())));
""", "CameraFragment continuity bridge")
camera.write_text(c)

m = renderer.read_text()
m = one(m,
"""        bindSource2A(frame1W.source2A);
        GLES20.glUniform1i(uM9Curve, 1);
""",
"""        bindSource2A(frame1W.source2A);
        // M9TUNGSTENCONT1A: TG1 is illuminant authority, not source-contract authority.
        // Preserve the native exact weight on a normal GL2A frame. If the source is
        // held or genuinely falls back, use the independently updated live neutral.
        float tungsten1A = (frame1W.source2A.continuityHeld || !frame1W.source2A.ready)
                ? frame1W.tungstenWeight : frame1W.source2A.tungstenWeight;
        if (!Float.isFinite(tungsten1A)) tungsten1A = 0.0f;
        GLES20.glUniform1f(uTungsten2A, Math.max(0.0f, Math.min(1.0f, tungsten1A)));
        GLES20.glUniform1i(uM9Curve, 1);
""", "draw-time TG1 upload")
m = one(m,
"""        GLES20.glUniform3fv(uClipWhite2A, 1, source.white(), 0);
        GLES20.glUniform1f(uTungsten2A, source.tungstenWeight);
        boundSource2A = source;
""",
"""        GLES20.glUniform3fv(uClipWhite2A, 1, source.white(), 0);
        boundSource2A = source;
""", "remove source-ready-only TG1 upload")
renderer.write_text(m)

s = shader.read_text()
s = one(s,
"""    if (!uM9Enabled || !uM9SourceReady2A)
        return clamp(linearToSrgbM9(srgbToLinearM9(clamp(oes,0.0,1.0))*uM9ExposureScale1B),0.0,1.0);
""",
"""    if (!uM9Enabled)
        return clamp(linearToSrgbM9(srgbToLinearM9(clamp(oes,0.0,1.0))*uM9ExposureScale1B),0.0,1.0);
    if (!uM9SourceReady2A) {
        // M9TUNGSTENCONT1A: source inversion may fail closed, but the encoded-domain
        // TG1 guard is independent and remains safe on the exposure-adjusted OES RGB.
        vec3 fallback1A=clamp(linearToSrgbM9(
                srgbToLinearM9(clamp(oes,0.0,1.0))*uM9ExposureScale1B),0.0,1.0);
        return tungsten2A(fallback1A);
    }
""", "TG1 fallback shader")
shader.write_text(s)

st = state.read_text()
st = one(st,
"""                o.put("colourPath", state.source2A.ready && transformEnabled
                        ? "reconstructed_sensor_native_M9_SAT2_curve02"
                        : "processed_OES_exposure_only_fallback");
                o.put("curve02Live", transformEnabled && state.source2A.ready);
                o.put("sat2Live", transformEnabled && state.source2A.ready);
                o.put("fittedResidualStack", false);
""",
"""                o.put("colourPath", state.source2A.ready && transformEnabled
                        ? "reconstructed_sensor_native_M9_SAT2_curve02"
                        : "processed_OES_exposure_plus_TG1_fallback");
                o.put("curve02Live", transformEnabled && state.source2A.ready);
                o.put("sat2Live", transformEnabled && state.source2A.ready);
                o.put("tungstenGuardLive", transformEnabled);
                o.put("tungstenGuardAuthority",
                        (state.source2A.continuityHeld || !state.source2A.ready)
                                ? "live_neutral_independent_of_source_contract"
                                : "native_source_context");
                o.put("sourceContinuity", "M9TUNGSTENCONT1A");
                o.put("fittedResidualStack", false);
""", "preview diagnostics")
state.write_text(st)

b = gradle.read_text()
b = one(b,
"""        versionName '1.61-m9detail1h-nativeguard'
""",
"""        versionName '1.61-m9detail1h-tg1cont1a'
""", "version")
gradle.write_text(b)

if sha(still) != expected[still]:
    raise SystemExit("M9TUNGSTENCONT1A still renderer changed unexpectedly")

print("M9TUNGSTENCONT1A applied")
print(" - raw GL2F source contract remains fail-closed")
print(" - same-camera last-valid source held for <= 1000 ms")
print(" - TG1 upload decoupled from source readiness")
print(" - true OES fallback now receives TG1 after exposure adjustment")
print(" - DETAIL1H still renderer/native detail path unchanged")
