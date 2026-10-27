#!/usr/bin/env python3
"""FOCUSOVERLAY1B: correct oversized eye overlay observed in 63341.mp4.

Pure presentation patch on reconstructed M9Cam 3.11. Camera2 focus region,
verified eye target, coordinate map, recognition, tracking and image output
must remain exactly as 3.11.
"""
from pathlib import Path
import argparse, hashlib, json, shutil

p = argparse.ArgumentParser()
p.add_argument("source", type=Path)
p.add_argument("--report", type=Path)
a = p.parse_args()
root = a.source.resolve()
here = Path(__file__).resolve().parent
java = Path("app/src/main/java/com/particlesdevs/photoncamera")
changes = []

def blob(path):
    b=path.read_bytes()
    return hashlib.sha1(("blob %d\0" % len(b)).encode()+b).hexdigest()

def replace_once(txt,old,new,where):
    count = txt.count(old)
    assert count == 1,(where,"source drift",count,old[:90])
    return txt.replace(old,new)

helper = root/java/"ui/camera/views/FocusTickGeometry.java"
assert helper.is_file() and blob(helper)=="07b595ab5cb29460935e4bd0cdc78f1369880553", (
    "FOCUSOVERLAY1B requires exact 3.11 eye geometry helper",str(helper),blob(helper))
shutil.copyfile(here/"src/com/particlesdevs/photoncamera/ui/camera/views/FocusTickGeometry.java",helper)
changes.append(helper.relative_to(root).as_posix())

human = root/java/"ui/camera/HumanSubjectFocusController.java"
h=human.read_text()
original_h=h
assert "class EyeBadge" not in h and "getOverlay().add(" not in h, "3.11 clean badge prerequisite"
assert "profileEyeGate.admit(epoch,startedNs,nowNs,faces)" in h
assert "focus.update(g,afRegion.x,afRegion.y," in h
h=replace_once(h,
    "import com.particlesdevs.photoncamera.ui.camera.views.TrackingFocusView;\n",
    "import com.particlesdevs.photoncamera.ui.camera.views.TrackingFocusView;\n"
    "import com.particlesdevs.photoncamera.ui.camera.views.FocusTickGeometry;\n",
    "import")
h=replace_once(h,
    """                        float halfW=.5f*target.regionWidth*g.w;
                        float halfH=.5f*target.regionHeight*g.h;
                        overlay.show(px,py,halfW,halfH,false);""",
    """                        // M9Cam 3.12: The Eye AF Camera2 target/region above
                        // is unchanged. Only its UI presentation is capped,
                        // so a large AF meter cannot frame the whole forehead.
                        float halfW=.5f*target.regionWidth*g.w;
                        float halfH=.5f*target.regionHeight*g.h;
                        float density=overlay.getResources().getDisplayMetrics().density;
                        float visibleW=FocusTickGeometry.eyeDisplayHalfWidth(halfW,density);
                        float visibleH=FocusTickGeometry.eyeDisplayHalfHeight(halfH,density);
                        overlay.show(px,py,visibleW,visibleH,false);""",
    "eye presentation")
assert original_h.split("            focus.update(g,afRegion.x,afRegion.y,")[0] == h.split("            focus.update(g,afRegion.x,afRegion.y,")[0].replace(
    "import com.particlesdevs.photoncamera.ui.camera.views.FocusTickGeometry;\n",""), (
        "unexpected Camera2-side source change")
assert "float px=a[0]-b[0]+g.left+target.x*g.w;" in h
assert "float py=a[1]-b[1]+g.top+target.y*g.h;" in h
assert h.count("overlay.show(px,py,visibleW,visibleH,false);")==1
assert h.count("focus.update(g,afRegion.x,afRegion.y,")==1
human.write_text(h)
changes.append(human.relative_to(root).as_posix())

build = root/"app/build.gradle"
s=build.read_text()
for old,new in (
    ("versionCode 27311","versionCode 27312"),
    ("versionName '3.11-focusoverlay1a'","versionName '3.12-focusoverlay1b'"),
    ("M9Cam_3.11_FOCUSOVERLAY1A","M9Cam_3.12_FOCUSOVERLAY1B")):
    s=replace_once(s,old,new,"Gradle")
build.write_text(s)
changes.append("app/build.gradle")

assert "eyeDisplayHalfWidth(" in helper.read_text()
assert "eyeDisplayHalfHeight(" in helper.read_text()
assert "canvas.drawRect(" not in (root/java/"ui/camera/views/TrackingFocusView.java").read_text()
assert len(changes)==3,changes
report=dict(status="STAGED_FOR_ANDROID_BUILD",version="3.12-focusoverlay1b",
    parent="3.11-focusoverlay1a",changedFiles=sorted(changes),
    cause="Eye AF visual extents inherited large Camera2 AF region",
    capWidthHalfDp=17,capHeightHalfDp=13,
    drawOnlyClamp=True,eyeTargetCenterUnchanged=True,
    camera2RegionAndAfSubmissionUnchanged=True,trackingAndRecognitionUnchanged=True,
    inheritedBalancedExtendedTicksPreserved=True,eyeBadgeAbsent=True,
    modelsAssetsLibrariesUnchanged=True,exposureAeAwbRawDngJpegRendererUnchanged=True,
    onPhoneValidationPending=True)
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
