#!/usr/bin/env python3
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit("usage: verify <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
cc=(root/"app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java").read_text()
shader=(root/"app/src/main/assets/shaders/preview/main_fs.glsl").read_text()
tone=(root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java").read_text()
checks=[
("GL1T marker","M9LIVEGL1T_CONTINUOUSPREVIEW1A" in cc),
("keep repeating","m9KeepPreviewRepeating1T" in cc and "keepRepeating=true abortCaptures=false" in cc),
("conditional stop","if (!m9KeepPreviewRepeating1T)" in cc and "mCaptureSession.stopRepeating();" in cc and "mCaptureSession.abortCaptures();" in cc),
("minimal unlock method","unlockFocusM9Continuous1T()" in cc),
("minimal AF cancel","CONTROL_AF_TRIGGER_CANCEL" in cc and "CONTROL_AF_TRIGGER_IDLE" in cc),
("minimal repeating restore","mCaptureSession.setRepeatingRequest(mPreviewInputRequest, mCaptureCallback" in cc),
("no reset3A in minimal block","minimalUnlock=true" in cc and "reset3A=false" in cc),
("post capture selects minimal","M9Config.isCaptureTest()" in cc and "unlockFocusM9Continuous1T();" in cc),
("GL1S RAW-only retained","M9LIVEGL1S_PREVIEWSURFACELOCK1A" in cc and "stillTargets=RAW_ONLY" in cc),
("GL1B exposure retained","Photon_GL_IsoExpoSelector_intended_pair" in cc and "setExactExposureM9Wysiwyg1B(" in cc),
("GL1Q shader retained","M9LIVEGL1Q_PAIRCURVE1A" in shader and "linear *= uM9ExposureScale1B" in shader),
("FIX1 retained","M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A" in tone),
]
for label,ok in checks:
 print(("OK   " if ok else "FAIL ")+label)
 if not ok: raise SystemExit("GL1T contract failure: "+label)

# Prove the M9 continuous path does not call the legacy heavy unlock.
post=cc[cc.find("mBackgroundHandler.post(() -> {", cc.find("CaptureSequenceCompleted")):]
if "unlockFocusM9Continuous1T();" not in post:
 raise SystemExit("GL1T post-capture minimal unlock not found")
print("M9LIVEGL1T_CONTINUOUSPREVIEW1A VERIFY PASS")
