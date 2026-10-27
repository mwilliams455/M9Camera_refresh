#!/usr/bin/env python3
"""3.13 packager: inherit the verified 3.10 signing logic with strict 3.12 parent.

No changes to signature algorithm, keystore, certificate, ZIP handling,
native libraries, model assets, renderer or Camera2 request validation.
"""
from pathlib import Path
import hashlib
import subprocess
import sys

here=Path(__file__).resolve().parent
parent_script=here.parent/"autoeye1a"/"package.py"
data=parent_script.read_bytes()
blob=hashlib.sha1(("blob %d\0"%len(data)).encode()+data).hexdigest()
assert blob=="07b1ca5f2134cd28b2e498fec89f7548ba9955ba", ("3.10 signing packager drift",blob)
s=data.decode("utf-8")

def replace_once(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,"unexpected parent packager source",count)
    s=s.replace(old,new)

replace_once(
    "accepted='9f4501550ef57aeb32952efacf298a410c995400e819b16acb249202f5aaa2c8'",
    "accepted='434fb4a6de2e87aa883fe841db1d8abed5c38785e574a756020d8b6aa818a4ee'",
    "exact 3.12 signed parent")
replace_once("'Exact phone-positive 3.09 parent APK required'",
             "'Exact signed and phone-reviewed 3.12 parent APK required'",
             "parent diagnostic")
replace_once(
    """assert scope['parent']=='3.09-aftracking5a' and scope['autoHumanEyeDefaultOn']
assert scope['oldManualEyeKeyIgnoredByNewAutoMode'] and scope['manualObjectTapHasPriority']
assert scope['strictFrontalGateUntouched'] and scope['profileEyeFourFreshObservations']
assert scope['camera2AfRegionOnly'] and scope['afCShutterPathUnchanged']
assert scope['originalModelsNativeAndAssetsUnchanged']
assert scope['aeAwbExposureRawJpegDngRenderingUnchanged']""",
    """assert scope['parent']=='3.12-focusoverlay1b'
assert scope['freshInstallBaseTrackingDefaultOn']
assert scope['freshInstallSubjectRecognitionDefaultOn']
assert scope['savedTrackingOffPreserved']
assert scope['wideContinuousPictureAfOnly'] and scope['ordinaryAfSMfTapUnchanged']
assert scope['unsupportedAfDelegates']
assert scope['manualTapSelectAndRetapCancelPreserved']
assert scope['semanticModelLazyUntilUserTap']
assert scope['predictiveAndIdentityDefaultOff']
assert scope['inheritedAutoEyeUnchanged'] and scope['petAfPriorityUnchanged']
assert scope['inheritedBalancedExtendedTicksUnchanged']
assert scope['originalModelAssetsNativeAndRendererUnchanged']""",
    "3.13 scope and migration evidence")
replace_once("final=out/'M9Cam_3.10_AUTOEYE1A.apk'",
             "final=out/'M9Cam_3.13_TRACKINGDEFAULT1A.apk'","installer name")
replace_once(
    "'PetFocusController','AnimalSimccDecoder','TrackingFocus','M9DIAGINDEX1A_BOUNDED'",
    "'PetFocusController','AnimalSimccDecoder','TrackingFocus','FocusTickGeometry','TrackingDefaultPolicy','M9DIAGINDEX1A_BOUNDED'",
    "compiled symbols")
replace_once("versionCode='27310'","versionCode='27313'","versionCode")
replace_once("versionName='3.10-autoeye1a'","versionName='3.13-trackingdefault1a'","versionName")
replace_once("report=dict(status='PASS',version='3.10-autoeye1a',versionCode=27310,",
             "report=dict(status='PASS',version='3.13-trackingdefault1a',versionCode=27313,",
             "reported candidate")
replace_once(
    """photoRendererUntouched=True,automaticEyeDefaultOn=True,
            phoneHumanEyeValidationPending=True)""",
    """photoRendererUntouched=True,automaticEyeDefaultOn=True,
            afCTapTrackingDefaultOn=True,subjectRecognitionTapScoped=True,
            explicitTrackingOffPreserved=True,afSMfUnaffected=True,
            balancedExtendedTicksPreserved=True,
            phoneTrackingAndOpticalSharpnessValidationPending=True)""",
    "report acceptance")
generated=here/"_TRACKINGDEFAULT1A_package_runtime.py"
assert not generated.exists(),"Refusing to overwrite a temporary generated signing file"
try:
    generated.write_text(s)
    subprocess.run([sys.executable,str(generated),*sys.argv[1:]],check=True)
finally:
    generated.unlink(missing_ok=True)
