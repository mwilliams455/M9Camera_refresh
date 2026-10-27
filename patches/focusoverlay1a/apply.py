#!/usr/bin/env python3
"""FOCUSOVERLAY1A: presentation-only 3.11 patch over exact reconstructed 3.10.

No touch, Camera2, AF policy, detector, predictor, exposure, or rendering edit.
All source parents are pinned by their Git blob SHA; drift is an error.
"""
from pathlib import Path
import argparse, hashlib, json, shutil

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
root = args.source.resolve()
here = Path(__file__).resolve().parent
base = Path("app/src/main/java/com/particlesdevs/photoncamera")
changed = []

def blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()

def require_parent(path, expected):
    assert path.is_file(), str(path)
    actual = blob_sha(path)
    assert actual == expected, (str(path), "parent changed", actual, expected)

def replace_once(text, before, after, name):
    count = text.count(before)
    assert count == 1, (name, "anchor count", count, before[:90])
    return text.replace(before, after)

tracking = root / base / "ui/camera/views/TrackingFocusView.java"
require_parent(tracking, "5a072e0da3eda5345593a1b7bd3f186535331980")
source_tracking = here / "src/com/particlesdevs/photoncamera/ui/camera/views/TrackingFocusView.java"
assert source_tracking.is_file()
shutil.copyfile(source_tracking, tracking)
changed.append(tracking.relative_to(root).as_posix())

geometry = root / base / "ui/camera/views/FocusTickGeometry.java"
assert not geometry.exists(), "Do not shadow an existing UI geometry helper"
source_geometry = here / "src/com/particlesdevs/photoncamera/ui/camera/views/FocusTickGeometry.java"
assert source_geometry.is_file()
shutil.copyfile(source_geometry, geometry)
changed.append(geometry.relative_to(root).as_posix())

human = root / base / "ui/camera/HumanSubjectFocusController.java"
require_parent(human, "b903422d273b1752015c6f777ef2d68061612b2f")
original_human = human.read_text()
text = original_human
for imported in (
    "import android.graphics.Canvas;\n",
    "import android.graphics.ColorFilter;\n",
    "import android.graphics.Paint;\n",
    "import android.graphics.PixelFormat;\n",
    "import android.graphics.drawable.Drawable;\n",
):
    text = replace_once(text, imported, "", "unused EyeBadge import")
text = replace_once(text,
    "    private final EyeBadge eyeBadge;\n    private boolean badgeAttached;\n", "",
    "EyeBadge-only fields")
text = replace_once(text,
    "        this.eyeBadge = new EyeBadge(overlay);\n", "",
    "EyeBadge constructor only")
text = replace_once(text,
    '''                        // Keep the inherited shared TrackingFocusView unchanged.
                        // Draw an explicit "Eye AF" label above its generic
                        // tracking text, solely when a verified eye is admitted.
''',
    '''                        // Shared focus overlay uses these already-mapped view pixels.
''', "obsolete EyeBadge comment")
text = replace_once(text,
    '''                        if (!badgeAttached) {
                            overlay.getOverlay().add(eyeBadge);
                            badgeAttached=true;
                        }
                        eyeBadge.place(px,py,halfW,halfH);
''', "", "EyeBadge visual-only attachment")
text = replace_once(text,
    '''        if (badgeAttached) {
            overlay.getOverlay().remove(eyeBadge);
            badgeAttached=false;
        }
''', "", "EyeBadge visual-only retirement")
begin = "    /** Lightweight label overlay for Eye AF; changes no inherited view class. */\n"
end = "    private void finish() {"
assert text.count(begin) == 1 and text.count(end) == 1
start = text.index(begin)
finish = text.index(end)
assert finish > start, "EyeBadge class boundary mismatch"
text = text[:start] + text[finish:]
assert "EyeBadge" not in text
assert "overlay.show(px,py,halfW,halfH,false);" in text
assert "R.string.focus_subject_eye_active" in text
assert "focus.update(g,afRegion.x,afRegion.y," in text
assert "profileEyeGate.admit(epoch,startedNs,nowNs,faces)" in text
assert "setContentDescription" in text
human.write_text(text)
changed.append(human.relative_to(root).as_posix())

build = root / "app/build.gradle"
b = build.read_text()
for old, new in (
    ("versionCode 27310", "versionCode 27311"),
    ("versionName '3.10-autoeye1a'", "versionName '3.11-focusoverlay1a'"),
    ("M9Cam_3.10_AUTOEYE1A", "M9Cam_3.11_FOCUSOVERLAY1A"),
):
    b = replace_once(b, old, new, "Gradle visual-only version")
build.write_text(b)
changed.append("app/build.gradle")

view = tracking.read_text()
geometry_text = geometry.read_text()
assert "canvas.drawRect(" not in view
assert "canvas.drawLines(ticks, paint)" in view
assert "private final float[] ticks = new float[32]" in view
assert "showHolding(" in view and "showPending(" in view and "show(" in view
assert "setContentDescription" in view
assert "paint.setColor(uncertain ? 0xffffba59 : 0xfffcfcf8)" in view
assert "if (uncertain)" in view and "focus_tracking_lost" in view
assert "public static boolean populate(" in geometry_text
assert "new " not in geometry_text.replace('new IllegalArgumentException', ''), "Do not allocate on draw path"
assert "CONTROL_AF_TRIGGER" not in view and "CONTROL_AE_REGIONS" not in view
assert "CONTROL_AF_TRIGGER" not in text and "CONTROL_AE_REGIONS" not in text
assert "CONTROL_AWB_REGIONS" not in text
assert len(changed) == 4, changed

report = dict(
    status="STAGED_FOR_ANDROID_BUILD", version="3.11-focusoverlay1a",
    parent="3.10-autoeye1a", changedFiles=sorted(changed),
    balancedExtendedTicksDefault=True, eightSegmentsFourOpenCorners=True,
    whiteActiveAmberPendingHoldingLost=True, eyeBadgeRemoved=True,
    eyeTalkBackDescriptionPreserved=True,
    originalOverlayShowHoldPendingContractsPreserved=True,
    originalEyeAfCamera2SubmissionPreserved=True,
    afTapTrackingDetectorPredictorUnchanged=True,
    exposureAeAwbJpegDngRawRendererUnchanged=True,
    original37NativeLibraries301AssetsRequired=True,
    userOnPhoneAcceptancePending=True)
if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
