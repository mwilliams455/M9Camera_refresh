#!/usr/bin/env python3
"""3.12 compact-eye packager using the frozen 3.10 signing implementation.

This wrapper changes only package metadata, exact parent verification and
FOCUSOVERLAY1B evidence gates. It does not change signing methods, cert,
zip handling, native libraries or original assets.
"""
from pathlib import Path
import hashlib, subprocess, sys

here = Path(__file__).resolve().parent
parent_script = here.parent / "autoeye1a" / "package.py"
data = parent_script.read_bytes()
blob = hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()
assert blob == "07b1ca5f2134cd28b2e498fec89f7548ba9955ba", ("3.10 signed packager drift", blob)
s = data.decode("utf-8")

def replace_once(old, new, label):
    global s
    n = s.count(old)
    assert n == 1, (label, "unexpected 3.10 packager", n)
    s = s.replace(old, new)

replace_once("accepted='9f4501550ef57aeb32952efacf298a410c995400e819b16acb249202f5aaa2c8'",
             "accepted='e6d63e7016193acbef9fd59fa8b3fc674b6bd7cb0bae522f294715b34372849d'",
             "pinned 3.10 parent sha256")
replace_once("'Exact phone-positive 3.09 parent APK required'",
             "'Exact signed 3.11 parent APK required'", "parent warning")
replace_once(
    """assert scope['parent']=='3.09-aftracking5a' and scope['autoHumanEyeDefaultOn']
assert scope['oldManualEyeKeyIgnoredByNewAutoMode'] and scope['manualObjectTapHasPriority']
assert scope['strictFrontalGateUntouched'] and scope['profileEyeFourFreshObservations']
assert scope['camera2AfRegionOnly'] and scope['afCShutterPathUnchanged']
assert scope['originalModelsNativeAndAssetsUnchanged']
assert scope['aeAwbExposureRawJpegDngRenderingUnchanged']""",
    """assert scope['parent']=='3.11-focusoverlay1a'
assert scope['drawOnlyClamp'] and scope['eyeTargetCenterUnchanged']
assert scope['camera2RegionAndAfSubmissionUnchanged']
assert scope['trackingAndRecognitionUnchanged']
assert scope['inheritedBalancedExtendedTicksPreserved'] and scope['eyeBadgeAbsent']
assert scope['modelsAssetsLibrariesUnchanged']
assert scope['exposureAeAwbRawDngJpegRendererUnchanged']""",
    "3.11 source verification")
replace_once("final=out/'M9Cam_3.10_AUTOEYE1A.apk'",
             "final=out/'M9Cam_3.12_FOCUSOVERLAY1B.apk'", "output name")
replace_once("'PetFocusController','AnimalSimccDecoder','TrackingFocus','M9DIAGINDEX1A_BOUNDED'",
             "'PetFocusController','AnimalSimccDecoder','TrackingFocus','FocusTickGeometry','M9DIAGINDEX1A_BOUNDED'",
             "compiled geometry proof")
replace_once("versionCode='27310'", "versionCode='27312'", "versioncode badge")
replace_once("versionName='3.10-autoeye1a'", "versionName='3.12-focusoverlay1b'", "version badge")
replace_once("report=dict(status='PASS',version='3.10-autoeye1a',versionCode=27310,",
             "report=dict(status='PASS',version='3.12-focusoverlay1b',versionCode=27312,",
             "report metadata")
replace_once(
    """photoRendererUntouched=True,automaticEyeDefaultOn=True,
            phoneHumanEyeValidationPending=True)""",
    """photoRendererUntouched=True,automaticEyeDefaultOn=True,
            balancedExtendedTicks=True,eyeBadgeRemoved=True,
            eyeDisplayClampOnly=True,focusAlgorithmAndCamera2Untouched=True,
            phoneEyeMarkerValidationPending=True)""",
    "report acceptance")
generated = here / "_FOCUSOVERLAY1A_package_runtime.py"
assert not generated.exists(), "Refusing to overwrite an existing script"
try:
    generated.write_text(s)
    subprocess.run([sys.executable, str(generated), *sys.argv[1:]], check=True)
finally:
    generated.unlink(missing_ok=True)
