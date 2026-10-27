#!/usr/bin/env python3
"""M9Cam 3.13 TRACKINGDEFAULT1A on exact merged 3.12 source.

Narrow scope: fresh-install AF-C tracking defaults, existing-user preference
preservation, Wide AF-C-safe tap routing and lazy tapped-subject recognition.
Do not modify Eye AF, dedicated pet AF, Camera2 internals, preview geometry,
focus overlays, photography/rendering/RAW, native libraries or model assets.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("source",type=Path)
parser.add_argument("--report",type=Path)
args = parser.parse_args()
root = args.source.resolve()
here = Path(__file__).resolve().parent
prefix = Path("app/src/main/java/com/particlesdevs/photoncamera")
changed = []

def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()

def change(path, old, new, label):
    path = root/path
    source = path.read_text()
    assert source.count(old) == 1, (label,path,source.count(old))
    path.write_text(source.replace(old,new))
    changed.append(path.relative_to(root).as_posix())

tracking = prefix/"ui/camera/FocusTrackingController.java"
managed = prefix/"ui/settings/custompreferences/ManagedSwitchPreference.java"
assert git_blob(root/tracking) == "ffefaaa9da4cb3a9e079d6ea210aa7613860b388", "3.12 tracking class must be unchanged after AUTOEYE1A"
assert git_blob(root/managed) == "25a0287ae60035db205f25a8b4c15590c535da33", "3.12 settings dependency class must match AFTRACKING5A"

policy = prefix/"control/tracking/TrackingDefaultPolicy.java"
assert not (root/policy).exists()
(root/policy).parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(here/"src/com/particlesdevs/photoncamera/control/tracking/TrackingDefaultPolicy.java",root/policy)
changed.append(policy.as_posix())

change(tracking,
    "import android.graphics.Bitmap;\n",
    "import android.graphics.Bitmap;\nimport android.hardware.camera2.CaptureRequest;\n",
    "camera2 import")
change(tracking,
    "import com.particlesdevs.photoncamera.control.tracking.TrackingTogglePolicy;\n",
    "import com.particlesdevs.photoncamera.control.tracking.TrackingTogglePolicy;\n"
    "import com.particlesdevs.photoncamera.control.tracking.TrackingDefaultPolicy;\n"
    "import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;\n"
    "import com.particlesdevs.photoncamera.settings.PreferenceKeys;\n",
    "AF-C and focus-area policy imports")

# The 3.09 dependency repair must NOT turn an existing saved OFF into ON
# because a child switch was persisted under an older camera version.
change(tracking,
    "        if(manager==null)return;\n        boolean wantsIdentity=manager.getBoolean(SettingsManager.SCOPE_GLOBAL,\n",
    "        if(manager==null)return;\n"
    "        // Parent setting takes precedence, including an explicitly saved OFF.\n"
    "        if (!manager.getBoolean(SettingsManager.SCOPE_GLOBAL, KEY, true)) return;\n"
    "        boolean wantsIdentity=manager.getBoolean(SettingsManager.SCOPE_GLOBAL,\n",
    "preserve explicit parent OFF")
change(tracking,
    """        boolean wantsTracking=wantsIdentity || manager.getBoolean(SettingsManager.SCOPE_GLOBAL,
                HYBRID_KEY, false)
                || manager.getBoolean(SettingsManager.SCOPE_GLOBAL,
                        TrackingTogglePolicy.PREDICTIVE, false);
        if(wantsTracking && !manager.getBoolean(SettingsManager.SCOPE_GLOBAL,KEY,false))
            manager.set(SettingsManager.SCOPE_GLOBAL,KEY,true);
""",
    "",
    "avoid implicit parent re-enable")
change(tracking,
    "                HYBRID_KEY, false);",
    "                HYBRID_KEY, true);",
    "semantic missing-key default")
change(tracking,
    "        if (warmRequested || destroyed || !recognitionEnabled()) return;",
    "        if (warmRequested || destroyed || !TrackingDefaultPolicy.warmSemantic(selected,recognitionEnabled())) return;",
    "idle worker guard")
change(tracking,
    """    private boolean enabled() {
        CameraMode mode = PhotonCamera.getSettings().selectedMode;
        return M9Config.isM9Modern() && (mode == CameraMode.PHOTO || mode == CameraMode.NIGHT || mode == CameraMode.MOTION)
                && PhotonCamera.getSettingsManagerStatic().getBoolean(com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, KEY, false)
                && !PhotonCamera.getSettingsManagerStatic().getBoolean(
                        com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, PetFocusController.KEY, false);
    }
""",
    """    private boolean enabled() {
        SettingsManager manager=PhotonCamera.getSettingsManagerStatic();
        if (manager==null || PhotonCamera.getSettings()==null) return false;
        CameraMode captureMode=PhotonCamera.getSettings().selectedMode;
        return TrackingDefaultPolicy.eligible(
                M9Config.isM9Modern(),
                captureMode==CameraMode.PHOTO || captureMode==CameraMode.NIGHT
                        || captureMode==CameraMode.MOTION,
                manager.getBoolean(SettingsManager.SCOPE_GLOBAL,KEY,true),
                PreferenceKeys.getAfMode()==CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE,
                FocusControlSettings.mode()==FocusControlPolicy.Mode.WIDE,
                manager.getBoolean(SettingsManager.SCOPE_GLOBAL,PetFocusController.KEY,false));
    }
""",
    "Wide/AF-C runtime admission")
change(tracking,
    "        freshSince = SystemClock.elapsedRealtimeNanos(); warmSemantic(); main.post(tick); }",
    "        freshSince = SystemClock.elapsedRealtimeNanos(); main.post(tick); }",
    "do not warm detector during idle start")
change(tracking,
    "        if (!running || !enabled()) return false;\n        TrackingGeometry g = TrackingGeometry.current(",
    "        // No persistent interception in AF-S, manual, Spot, or fixed-focus modes.\n"
    "        if (!running || !enabled() || !autofocus) return false;\n"
    "        TrackingGeometry g = TrackingGeometry.current(",
    "tap must be eligible")
change(tracking,
    """        if (g == null || g.published < freshSince || !cameraGeometry(g) || !source.isAttachedToWindow()) {
            fragment.showToast(fragment.getString(R.string.focus_tracking_preview_required)); return true;
        }
""",
    """        if (g == null || g.published < freshSince || !cameraGeometry(g)
                || !source.isAttachedToWindow() || g.w<=0 || g.h<=0) return false;
""",
    "stale preview delegates to ordinary focus")
change(tracking,
    """        if (u < 0 || v < 0 || u >= 1 || v >= 1) return true;
        if (selected && Math.abs(u - x) <= hx && Math.abs(v - y) <= hy) { clear(); return true; }
        clear();
        if (!autofocus) { fragment.showToast(fragment.getString(R.string.focus_tracking_auto_required)); return true; }
        focus = fragment.getCaptureController().newTrackingFocus();
        if (focus != null) focus.enableArbitraryCadence();
        if (focus == null || !focus.valid()) { clear(); fragment.showToast(fragment.getString(R.string.focus_tracking_unavailable)); return true; }
""",
    """        if (u < 0 || v < 0 || u >= 1 || v >= 1) return false;
        if (selected && Math.abs(u - x) <= hx && Math.abs(v - y) <= hy) {
            clear(); return true;
        }
        CaptureController capture=fragment.getCaptureController();
        if (capture==null) return false;
        clear();
        focus=capture.newTrackingFocus();
        if (focus == null || !focus.valid()) {
            // Fixed-focus/unsupported HAL: let the inherited ordinary tap path run.
            clear(); return false;
        }
        focus.enableArbitraryCadence();
""",
    "nonconsuming fallback and explicit cancellation")
change(tracking,
    "            if (recognitionEnabled()) warmSemantic();\n",
    "",
    "no idle model warm in 100 ms tick")

# Switch inflation and default-true subject must never manufacture a user
# action that turns parent tracking ON over an explicitly persisted OFF.
change(managed,
    """                settingsManager.set(SettingsManager.SCOPE_GLOBAL, key, value);
                if(dependency.enableTracking) {""",
    """                settingsManager.set(SettingsManager.SCOPE_GLOBAL, key, value);
                // Only a real user toggle may cascade into other settings.
                // In particular, inflating the new default-ON subject switch
                // must not undo an upgraded user's explicit tracking OFF.
                if (settingInitialValue) return true;
                if(dependency.enableTracking) {""",
    "UI inflation may not overwrite user choices")

# The two capture menus have separate files but the same persistence keys.
menus = ("preferences_m9.xml","preferences_monochrom.xml")
for name in menus:
    path = Path("app/src/main/res/xml")/name
    f = root/path
    xml = f.read_text()
    for key,summary in (
        ("pref_focus_tracking","tracking_default_base_summary1a"),
        ("pref_focus_tracking_semantic","tracking_default_subject_summary1a"),
    ):
        rx = re.compile(r'(<com\.particlesdevs\.photoncamera\.ui\.settings\.custompreferences\.ManagedSwitchPreference\s+android:key="'+key+r'"[^>]*?)/>',re.DOTALL)
        hits = list(rx.finditer(xml))
        assert len(hits)==1,(name,key,len(hits))
        old = hits[0].group(0)
        assert old.count('android:defaultValue="false"')==1,(name,key,"old default missing")
        assert re.search(r'android:summary="@string/[^"]+"',old),(name,key,"old summary missing")
        new = old.replace('android:defaultValue="false"','android:defaultValue="true"')
        new = re.sub(r'android:summary="@string/[^"]+"',
                'android:summary="@string/'+summary+'"',new,count=1)
        xml = xml[:hits[0].start()]+new+xml[hits[0].end():]
    assert xml.count('android:key="pref_focus_tracking_predictive"')==1
    assert xml.count('android:key="pref_focus_tracking_identity"')==1
    assert xml.count('android:key="pref_focus_auto_eye_enabled"')==1
    f.write_text(xml)
    changed.append(path.as_posix())

resource = Path("app/src/main/res/values/trackingdefault1a.xml")
assert not (root/resource).exists()
(root/resource).write_text("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="tracking_default_base_summary1a">On by default in Wide AF-C for Photo, Night and Motion. Tap a subject to follow it; tap the selected bracket again to cancel. Not used in AF-S or manual focus.</string>
    <string name="tracking_default_subject_summary1a">On by default when Focus tracking is active. After a deliberate tap, locally recognise a person, cat or dog; other objects use patch tracking. Inactive when Focus tracking is off.</string>
</resources>
""")
changed.append(resource.as_posix())

build = Path("app/build.gradle")
change(build,"versionCode 27312","versionCode 27313","version code")
change(build,"versionName '3.12-focusoverlay1b'",
             "versionName '3.13-trackingdefault1a'","version name")
change(build,"M9Cam_3.12_FOCUSOVERLAY1B",
             "M9Cam_3.13_TRACKINGDEFAULT1A","APK file name")

# Inherited 2.72 Robolectric fixture was written when opt-in tracking
# read getBoolean(KEY,false). The candidate now reads KEY,true, and only
# allows a tap in Wide Continuous Picture AF. Keep the actual pause/retap/
# bitmap lifetime assertions unchanged: update ONLY its setup preconditions.
lifecycle = Path("app/src/test/java/com/particlesdevs/photoncamera/ui/camera/FocusTrackingLifecycleTest.java")
change(lifecycle,
    "        when(manager.getBoolean(SettingsManager.SCOPE_GLOBAL, FocusTrackingController.KEY, false)).thenReturn(true);",
    "        when(manager.getBoolean(SettingsManager.SCOPE_GLOBAL, FocusTrackingController.KEY, true)).thenReturn(true);",
    "fixture: current pref default ON")
change(lifecycle,
    '        preferences.when(PreferenceKeys::getCameraID).thenReturn("0");',
    '        preferences.when(PreferenceKeys::getCameraID).thenReturn("0");\n'
    '        preferences.when(PreferenceKeys::getAfMode).thenReturn(\n'
    '                android.hardware.camera2.CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE);',
    "fixture: set eligible AF-C")
test_content=(root/lifecycle).read_text()
assert test_content.count("tracking.tap(150, 200, true)")==1
assert "closeDefersRecyclingUntilCopyReleasesBitmap" in test_content
assert "retapRejectsOldCallbackAndDoesNotOverlapCopies" in test_content
assert "pausedCopyCannotUpdateAfOrShowTracking" in test_content

source = (root/tracking).read_text()
assert "if (recognitionEnabled()) warmSemantic();" not in source
assert "freshSince = SystemClock.elapsedRealtimeNanos(); warmSemantic()" not in source
assert source.count("warmSemantic();")==1, "semantic loading only at deliberate tap"
assert "manager.getBoolean(SettingsManager.SCOPE_GLOBAL,KEY,true)" in source
assert "TrackingDefaultPolicy.eligible(" in source
assert "fragment.showToast(fragment.getString(R.string.focus_tracking_auto_required))" not in source
assert "float density=" not in source, "Eye marker remains owned by FOCUSOVERLAY1B"

changes = sorted(set(changed))
expected = sorted({
    str(tracking),str(managed),str(policy),
    "app/src/main/res/xml/preferences_m9.xml",
    "app/src/main/res/xml/preferences_monochrom.xml",
    str(resource),str(lifecycle),"app/build.gradle",
})
assert changes==expected,(changes,expected)
report = dict(status="STAGED_FOR_ANDROID_BUILD",version="3.13-trackingdefault1a",
              parent="3.12-focusoverlay1b",changedFiles=changes,
              freshInstallBaseTrackingDefaultOn=True,
              freshInstallSubjectRecognitionDefaultOn=True,
              savedTrackingOffPreserved=True,
              wideContinuousPictureAfOnly=True,ordinaryAfSMfTapUnchanged=True,
              unsupportedAfDelegates=True,manualTapSelectAndRetapCancelPreserved=True,
              semanticModelLazyUntilUserTap=True,predictiveAndIdentityDefaultOff=True,
              inheritedAutoEyeUnchanged=True,petAfPriorityUnchanged=True,
              inheritedBalancedExtendedTicksUnchanged=True,
              originalModelAssetsNativeAndRendererUnchanged=True,
              deviceFocusAccuracyValidationPending=True)
if args.report:
    args.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
