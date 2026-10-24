#!/usr/bin/env python3
"""FOCUSCONTROL1A 3.04 on exact accepted 3.03.

Read-only Camera2 AF feedback + AF-only focus-region sizing. One shared
four-mode area selector and subject selection scope for human/pet/patch.
No AE/AWB, DNG/JPG, look, shading, RAW or native library modifications.
"""
from pathlib import Path
import argparse,hashlib,shutil,json

arg=argparse.ArgumentParser()
arg.add_argument("source",type=Path)
arg.add_argument("--report",type=Path)
o=arg.parse_args()
root=o.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path("app/src/main/java/com/particlesdevs/photoncamera")
changes=[]
def patch(path,before,after):
    f=root/path
    s=f.read_text()
    count=s.count(before)
    if count!=1:
        raise ValueError(f"{path}: expected one anchor, got {count}: {before[:140]!r}")
    f.write_text(s.replace(before,after))
    changes.append(path.as_posix())
def add(rel):
    target=root/prefix/rel
    assert not target.exists(),rel
    src=here/"src/com/particlesdevs/photoncamera"/rel
    assert src.is_file(),src
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,target)
    changes.append((prefix/rel).as_posix())

for rel in (
    "control/subject/FocusControlPolicy.java",
    "ui/camera/FocusControlSettings.java",
    "ui/camera/FocusAfStatusBadge.java",
    "ui/camera/FocusAreaTouchController.java",
):
    add(rel)

# The only Camera2 mutation is in the existing verified TrackingFocus:
# accepted screen/crop rotation mapper stays authoritative, region widths
# are now optional normalized sensor-crop fractions. Existing overloads
# retain their EXACT old dimensions and request state on default Wide.
capture=prefix/"capture/CaptureController.java"
patch(capture,
    "    /** AF-only ownership for one selected tracking target. All submissions run on the camera handler. */",
    """
    /** A read-only AF-result receipt bound to the actual preview session. */
    public static final class FocusStateSnapshot {
        public final CameraCaptureSession session;
        public final String camera;
        public final long atMs, frame;
        public final Integer state;
        public final MeteringRectangle[] regions;
        public FocusStateSnapshot(CameraCaptureSession session,String camera,long atMs,
                                  long frame,Integer state,MeteringRectangle[] regions) {
            this.session=session;this.camera=camera;this.atMs=atMs;this.frame=frame;
            this.state=state;
            this.regions=regions==null?null:regions.clone();
        }
    }
    private volatile FocusStateSnapshot lastFocusState1A;
    public FocusStateSnapshot focusStateSnapshot() {
        FocusStateSnapshot s=lastFocusState1A;
        long now=SystemClock.elapsedRealtime();
        return s!=null && s.session==mCaptureSession && now>=s.atMs
                && now-s.atMs<=700 && java.util.Objects.equals(s.camera,PreferenceKeys.getCameraID())
                ?s:null;
    }

    /** AF-only ownership for one selected tracking target. All submissions run on the camera handler. */""")
patch(capture,
    "            mPreviewCaptureResult = result;\n            mPreviewCaptureRequest = request;",
    """            mPreviewCaptureResult = result;
            mPreviewCaptureRequest = request;
            // Throttle immutable AF-state receipts; only report HAL feedback
            // from the still-current preview session and selected camera.
            long focusNow1A=SystemClock.elapsedRealtime();
            FocusStateSnapshot priorFocus1A=lastFocusState1A;
            if(priorFocus1A==null || priorFocus1A.session!=session
                    || focusNow1A-priorFocus1A.atMs>=110) {
                lastFocusState1A=new FocusStateSnapshot(session,
                        PreferenceKeys.getCameraID(),focusNow1A,result.getFrameNumber(),
                        result.get(CaptureResult.CONTROL_AF_STATE),
                        request.get(CONTROL_AF_REGIONS));
            }""")
patch(capture,
    """        public void update(com.particlesdevs.photoncamera.control.tracking.TrackingGeometry geometry,
                float u, float v, java.util.function.Consumer<Boolean> completed) {
            if (handler == null) { completed.accept(false); return; }""",
    """        public boolean matchesFocusSample(FocusStateSnapshot sample) {
            return sample!=null && sample.session==session && owned!=null
                    && java.util.Arrays.equals(owned,sample.regions);
        }
        public void update(com.particlesdevs.photoncamera.control.tracking.TrackingGeometry geometry,
                float u, float v, java.util.function.Consumer<Boolean> completed) {
            // 3.03 compatibility: zero sizes retain the original AF rectangle.
            update(geometry,u,v,0f,0f,completed);
        }
        public void update(com.particlesdevs.photoncamera.control.tracking.TrackingGeometry geometry,
                float u, float v, float fractionW, float fractionH,
                java.util.function.Consumer<Boolean> completed) {
            if (handler == null) { completed.accept(false); return; }""")
patch(capture,
    """                        if (r != null) {
                            MeteringRectangle[] region = {new MeteringRectangle(r[0], r[1], r[2], r[2], 1000)};""",
    """                        if (r != null) {
                            int regionX=r[0],regionY=r[1],regionW=r[2],regionH=r[2];
                            if(Float.isFinite(fractionW)&&Float.isFinite(fractionH)
                                    &&fractionW>=.04f&&fractionW<=.5f
                                    &&fractionH>=.04f&&fractionH<=.5f) {
                                // Preserve the verified geometry.region() rotation/
                                // mirror/sensor mapping as the actual centre.
                                int centreX=r[0]+r[2]/2,centreY=r[1]+r[2]/2;
                                regionW=Math.max(2,Math.min(crop.width(),
                                        Math.round(crop.width()*fractionW)));
                                regionH=Math.max(2,Math.min(crop.height(),
                                        Math.round(crop.height()*fractionH)));
                                regionX=Math.max(crop.left,Math.min(crop.right-regionW,centreX-regionW/2));
                                regionY=Math.max(crop.top,Math.min(crop.bottom-regionH,centreY-regionH/2));
                            }
                            MeteringRectangle[] region={new MeteringRectangle(regionX,regionY,regionW,regionH,1000)};""")
patch(capture,
    """                            if (owned == null || Math.abs(owned[0].getX() - r[0]) + Math.abs(owned[0].getY() - r[1]) >= Math.max(2, r[2] / 8)) {""",
    """                            if (owned == null ||
                                    Math.abs(owned[0].getX()-regionX)+Math.abs(owned[0].getY()-regionY)
                                        >=Math.max(2,regionW/8)
                                    ||owned[0].getWidth()!=regionW ||owned[0].getHeight()!=regionH) {""")

frag=prefix/"ui/camera/CameraFragment.java"
patch(frag,
    "    private PetFocusController focusAnimal;",
    "    private PetFocusController focusAnimal;\n    private FocusAreaTouchController focusArea;")
patch(frag,
    "        return focusTracking != null && focusTracking.tap(x, y, auto);",
    """        if (focusTracking != null && focusTracking.tap(x, y, auto)) return true;
        return focusArea != null && focusArea.tap(x, y, auto);""")
patch(frag,
    "        if (focusAnimal != null) focusAnimal.clear();",
    "        if (focusAnimal != null) focusAnimal.clear();\n        if (focusArea != null) focusArea.clear();")
patch(frag,
    "        focusAnimal = new PetFocusController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);",
    """        focusAnimal = new PetFocusController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);
        focusArea = new FocusAreaTouchController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);""")
patch(frag,
    "        if (focusAnimal != null) focusAnimal.start();",
    "        if (focusAnimal != null) focusAnimal.start();\n        if (focusArea != null) focusArea.start();")
patch(frag,
    "        if (focusAnimal != null) focusAnimal.stop();",
    "        if (focusArea != null) focusArea.stop();\n        if (focusAnimal != null) focusAnimal.stop();")
patch(frag,
    "        if (focusAnimal != null) focusAnimal.close();\n        focusAnimal = null;",
    "        if (focusArea != null) focusArea.close();\n        focusArea = null;\n        if (focusAnimal != null) focusAnimal.close();\n        focusAnimal = null;")

# Physical RAW/calibration provenance is already collected by the M9 and Mono
# renderer audits. Join it in the existing per-capture PRIMARY diagnostics,
# rather than changing source calibration or writing extra sidecar files.
provenance=Path("app/src/main/java/com/particlesdevs/photoncamera/m9/provenance")
pFile=provenance/"M9SourceProvenance1A.java"
assert not (root/pFile).exists()
src=here/"src/com/particlesdevs/photoncamera/m9/provenance/M9SourceProvenance1A.java"
(root/pFile).parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(src,root/pFile)
changes.append(pFile.as_posix())
for pkgName,marker in (
    ("m9",'''            out.diagnostics.put("sensorDescriptor1A", stillSensorDescriptor1A);'''),
    ("monochrom",'''            out.diagnostics.put("monoDevicePortRevision", "MONO_DEVICEPORT2A_CFA_ORIGIN");''')
):
    renderer=Path("app/src/main/java/com/particlesdevs/photoncamera")/pkgName/"render/M9R35Renderer.java"
    patch(renderer,marker,marker+'''
            out.diagnostics.put("physicalRawProvenance1A",
                    com.particlesdevs.photoncamera.m9.provenance.M9SourceProvenance1A.describe(
                            params,characteristics,diagnosticCaptureResult1A,
                            sourceCalibrationAudit1A,rawShadingAudit1A));''')

# Scope semantic face and pet subjects to the selected AF area. Existing
# tap-to-select retains identity when the subject moves. Wide is unchanged.
human=prefix/"ui/camera/HumanSubjectFocusController.java"
patch(human,
    "import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;",
    """import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;""")
patch(human,
    "    private final SubjectFocusPolicy policy = new SubjectFocusPolicy();",
    """    private final SubjectFocusPolicy policy = new SubjectFocusPolicy();
    private final FocusControlPolicy focusScope = new FocusControlPolicy();""")
patch(human,
    "        admissionGate.beginSession(epoch);\n    }\n\n    private boolean enabled()",
    "        admissionGate.beginSession(epoch);\n        focusScope.beginSession(epoch);\n    }\n\n    private boolean enabled()")
patch(human,
    "        epoch++;\n        policy.beginSession(epoch);\n        admissionGate.beginSession(epoch);",
    "        epoch++;\n        policy.beginSession(epoch);\n        admissionGate.beginSession(epoch);\n        focusScope.beginSession(epoch);")
patch(human,
    "            admissionGate.beginSession(epoch);\n            policy.tapSelect(latestFaces,u,v);",
    """            admissionGate.beginSession(epoch);
            focusScope.beginSession(epoch);
            FocusControlSettings.configure(focusScope);
            focusScope.tap(epoch,u,v);
            policy.tapSelect(latestFaces,u,v);""")
patch(human,
    "        if (focus!=null && !focus.valid()) { clear(); return; }",
    """        if (focus!=null && !focus.valid()) { clear(); return; }
        FocusControlSettings.configure(focusScope);
        CaptureController focusStateOwner=fragment.getCaptureController();
        CaptureController.FocusStateSnapshot focusSample=
                focusStateOwner==null?null:focusStateOwner.focusStateSnapshot();
        if(focusSample!=null && focus!=null && focus.matchesFocusSample(focusSample))
            focusScope.observeAf(epoch,focusSample.state,SystemClock.elapsedRealtime());""")
patch(human,
    """        List<SubjectFocusPolicy.Face> admitted=admissionGate.admit(epoch,startedNs,nowNs,faces);
        latestFaces=Collections.unmodifiableList(new ArrayList<>(admitted));""",
    """        List<SubjectFocusPolicy.Face> admitted=admissionGate.admit(epoch,startedNs,nowNs,faces);
        FocusControlSettings.configure(focusScope);
        java.util.List<SubjectFocusPolicy.Face> allowed=new java.util.ArrayList<>();
        for(SubjectFocusPolicy.Face face:admitted)
            if(focusScope.pinned() || focusScope.mayAcquire(face.left,face.top,face.right,face.bottom))
                allowed.add(face);
        latestFaces=Collections.unmodifiableList(new ArrayList<>(allowed));""")
patch(human,
    """            focus.update(g,target.x,target.y,applied -> main.post(() -> {""",
    """            FocusControlPolicy.Region afRegion=focusScope.area(target.x,target.y,
                    target.regionWidth,target.regionHeight);
            if(afRegion==null){releaseFocus();finish();return;}
            boolean wide=focusScope.mode()==FocusControlPolicy.Mode.WIDE;
            focus.update(g,afRegion.x,afRegion.y,
                    wide?0f:afRegion.width,wide?0f:afRegion.height,
                    applied -> main.post(() -> {""")

pet=prefix/"ui/camera/PetFocusController.java"
patch(pet,
    "import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;",
    """import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;""")
patch(pet,
    "    private final PetTargetPolicy policy=new PetTargetPolicy();",
    """    private final PetTargetPolicy policy=new PetTargetPolicy();
    private final FocusControlPolicy focusScope=new FocusControlPolicy();""")
patch(pet,
    "        policy.beginSession(epoch);\n        eyePolicy.beginSession(epoch);",
    "        policy.beginSession(epoch);\n        eyePolicy.beginSession(epoch);\n        focusScope.beginSession(epoch);")
patch(pet,
    "        epoch++;policy.beginSession(epoch);eyePolicy.beginSession(epoch);\n        currentBodyX=Float.NaN",
    "        epoch++;policy.beginSession(epoch);eyePolicy.beginSession(epoch);\n        focusScope.beginSession(epoch);\n        currentBodyX=Float.NaN")
patch(pet,
    """            policy.tapSelect(u,v,lastCandidates);
            lastFrameNs=Long.MIN_VALUE;""",
    """            policy.tapSelect(u,v,lastCandidates);
            focusScope.beginSession(epoch);
            FocusControlSettings.configure(focusScope);
            focusScope.tap(epoch,u,v);
            lastFrameNs=Long.MIN_VALUE;""")
patch(pet,
    "        if(af!=null&&!af.valid()) {clear();return;}",
    """        if(af!=null&&!af.valid()) {clear();return;}
        FocusControlSettings.configure(focusScope);
        CaptureController owner=fragment.getCaptureController();
        CaptureController.FocusStateSnapshot sample=
                owner==null?null:owner.focusStateSnapshot();
        if(sample!=null && af!=null && af.matchesFocusSample(sample))
            focusScope.observeAf(epoch,sample.state,SystemClock.elapsedRealtime());""")
patch(pet,
    """        PetTargetPolicy.Target target=policy.update(token,frameNs,nowNs,candidates);""",
    """        FocusControlSettings.configure(focusScope);
        java.util.List<PetTargetPolicy.Candidate> scopedCandidates=new java.util.ArrayList<>();
        for(PetTargetPolicy.Candidate candidate:candidates) {
            if(candidate!=null && (focusScope.pinned()
                    ||focusScope.mayAcquire(candidate.left,candidate.top,candidate.right,candidate.bottom)))
                scopedCandidates.add(candidate);
        }
        PetTargetPolicy.Target target=policy.update(token,frameNs,nowNs,scopedCandidates);""")
patch(pet,
    """            af.update(g,focusX,focusY,accepted->main.post(()->{""",
    """            FocusControlPolicy.Region afRegion=focusScope.area(focusX,focusY,
                    target.halfWidth*2f,target.halfHeight*2f);
            if(afRegion==null)return false;
            boolean wide=focusScope.mode()==FocusControlPolicy.Mode.WIDE;
            af.update(g,afRegion.x,afRegion.y,
                    wide?0f:afRegion.width,wide?0f:afRegion.height,
                    accepted->main.post(()->{""")

track=prefix/"ui/camera/FocusTrackingController.java"
patch(track,
    """                        focus.update(g, tracked.x, tracked.y, applied -> main.post(() -> {""",
    """                        FocusControlPolicyRegion304Holder holder=
                                new FocusControlPolicyRegion304Holder(tracked.x,tracked.y);
                        focus.update(g,holder.x,holder.y,holder.width,holder.height,
                                applied -> main.post(() -> {""")
# A tiny local helper makes the existing patch tracker opt into region sizing
# while preserving its original Wide mapping. This is package-private, never
# imports any vendor firmware or changes tracking algorithm.
helper=root/prefix/"ui/camera/FocusControlPolicyRegion304Holder.java"
assert not (root/helper).exists()
helper.write_text("""package com.particlesdevs.photoncamera.ui.camera;
import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;
final class FocusControlPolicyRegion304Holder {
    final float x,y,width,height;
    FocusControlPolicyRegion304Holder(float x,float y){
        FocusControlPolicy p=new FocusControlPolicy();
        p.beginSession(1L);
        FocusControlSettings.configure(p);
        FocusControlPolicy.Region r=p.area(x,y,0f,0f);
        this.x=r==null?x:r.x;
        this.y=r==null?y:r.y;
        this.width=p.mode()==FocusControlPolicy.Mode.WIDE?0f:r.width;
        this.height=p.mode()==FocusControlPolicy.Mode.WIDE?0f:r.height;
    }
}
""")
changes.append(helper.relative_to(root).as_posix())

prefs=prefix/"settings/PreferenceKeys.java"
patch(prefs,
    'COMMON_KEYS.add("pref_focus_subject_pet_eye");',
    'COMMON_KEYS.add("pref_focus_subject_pet_eye");\n'
    '        COMMON_KEYS.add("pref_focus_area_mode");\n'
    '        COMMON_KEYS.add("pref_focus_area_custom_width");\n'
    '        COMMON_KEYS.add("pref_focus_area_custom_height");\n'
    '        COMMON_KEYS.add("pref_focus_af_state_feedback");')

# New preference keys in both capture screens, never replace original modes.
for name in ("preferences_m9.xml","preferences_monochrom.xml"):
    path=Path("app/src/main/res/xml")/name
    anchor='<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference android:key="pref_focus_subject_pet_eye"'
    controls=(
        '<ListPreference android:key="pref_focus_area_mode" '
        'android:title="@string/focus_area_mode_title" '
        'android:summary="@string/focus_area_mode_summary" '
        'android:entries="@array/focus_area_mode_labels" '
        'android:entryValues="@array/focus_area_mode_values" '
        'android:defaultValue="WIDE" app:useSimpleSummaryProvider="true" '
        'android:layout="@layout/preference_with_margin" android:icon="@drawable/ic_focus" />\\n        '
        '<ListPreference android:key="pref_focus_area_custom_width" '
        'android:title="@string/focus_area_width_title" '
        'android:entries="@array/focus_area_size_labels" '
        'android:entryValues="@array/focus_area_size_values" '
        'android:defaultValue="0.20" app:useSimpleSummaryProvider="true" '
        'android:layout="@layout/preference_with_margin" />\\n        '
        '<ListPreference android:key="pref_focus_area_custom_height" '
        'android:title="@string/focus_area_height_title" '
        'android:entries="@array/focus_area_size_labels" '
        'android:entryValues="@array/focus_area_size_values" '
        'android:defaultValue="0.20" app:useSimpleSummaryProvider="true" '
        'android:layout="@layout/preference_with_margin" />\\n        '
        '<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference '
        'android:key="pref_focus_af_state_feedback" '
        'android:title="@string/focus_af_feedback_title" '
        'android:summary="@string/focus_af_feedback_summary" '
        'android:defaultValue="true" android:layout="@layout/preference_with_margin" '
        'android:icon="@drawable/ic_focus" />\\n        '
    )
    patch(path,anchor,controls+anchor)

# Labels, custom dimensions and explicit distinction between AF-detected and
# Camera2 HAL-reported focus are UI-only, with no other resource modifications.
resources=root/"app/src/main/res/values/focuscontrol1a.xml"
assert not resources.exists()
resources.write_text("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="focus_area_mode_title">Focus Area</string>
    <string name="focus_area_mode_summary">Spot / Expand Spot / Custom / Wide. Wide preserves 3.03.</string>
    <string name="focus_area_width_title">Custom width</string>
    <string name="focus_area_height_title">Custom height</string>
    <string name="focus_af_feedback_title">AF state feedback</string>
    <string name="focus_af_feedback_summary">Shows actual Camera2 scan/focus report separately from subject recognition.</string>
    <string-array name="focus_area_mode_labels">
        <item>Spot</item><item>Expand Spot</item><item>Custom</item><item>Wide</item>
    </string-array>
    <string-array name="focus_area_mode_values">
        <item>SPOT</item><item>EXPAND_SPOT</item><item>CUSTOM</item><item>WIDE</item>
    </string-array>
    <string-array name="focus_area_size_labels">
        <item>5%</item><item>10%</item><item>15%</item><item>20%</item><item>25%</item><item>30%</item><item>40%</item><item>50%</item>
    </string-array>
    <string-array name="focus_area_size_values">
        <item>0.05</item><item>0.10</item><item>0.15</item><item>0.20</item><item>0.25</item><item>0.30</item><item>0.40</item><item>0.50</item>
    </string-array>
</resources>
""")
changes.append(resources.relative_to(root).as_posix())

gradle=Path("app/build.gradle")
patch(gradle,"versionCode 27303","versionCode 27304")
patch(gradle,"versionName '3.03-animaleye1b'","versionName '3.04-focuscontrol1a'")
patch(gradle,"M9Cam_3.03_ANIMALEYE1B","M9Cam_3.04_FOCUSCONTROL1A")

c=(root/capture).read_text()
assert "FocusStateSnapshot focusStateSnapshot()" in c
assert "focusScope.observeAf(epoch,focusSample.state" in (root/human).read_text()
assert "focusScope.observeAf(epoch,sample.state" in (root/pet).read_text()
assert "public boolean matchesFocusSample(FocusStateSnapshot sample)" in c
assert "fractionW>=.04f" in c
assert "CONTROL_AE_REGIONS, region" not in c
assert "CONTROL_AWB_REGIONS, region" not in c
assert "CONTROL_AF_TRIGGER_IDLE" in c
assert (root/"app/src/main/assets/rtm_animal_fp16.tflite").exists()
assert '"physicalRawProvenance1A"' in (root/Path("app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java")).read_text()
assert '"physicalRawProvenance1A"' in (root/Path("app/src/main/java/com/particlesdevs/photoncamera/monochrom/render/M9R35Renderer.java")).read_text()
report=dict(
    status="STAGED_FOR_BUILD",version="3.04-focuscontrol1a",parent="3.03-animaleye1b",
    implementation=dict(spot=True,expandSpot=True,custom=True,wide=True,
        customHorizontalVerticalIndependent=True,subjectScope=True,
        tapToChangeSubjectRetained=True,afStateReportedFromCamera2=True),
    changedFiles=sorted(set(changes)),defaultArea="WIDE",
    defaultColourAndRawUnchanged=True,nativeAndOriginalAssetsUnchanged=True,
    physicalCalibrationReadOnlyReceiptInBothProfiles=True,
    phoneAutofocusValidationPending=True)
if o.report:
    o.report.parent.mkdir(parents=True,exist_ok=True)
    o.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
