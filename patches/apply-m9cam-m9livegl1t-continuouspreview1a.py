#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1t-continuouspreview1a.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
ccp=root/"app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
if not ccp.exists(): raise SystemExit("GL1T missing CaptureController")
cc=ccp.read_text()

def one(old,new,label):
    global cc
    n=cc.count(old)
    if n!=1: raise SystemExit(f"GL1T {label}: expected 1 anchor, found {n}")
    cc=cc.replace(old,new,1)

method_anchor='''    public void unlockFocus() {
'''
method_new=r'''    // M9LIVEGL1T_CONTINUOUSPREVIEW1A
    // Minimal M9 post-capture AF release. Do NOT reset AE/3A or issue the historical
    // cancel/start/cancel preview rebuild sequence: device video showed that sequence
    // is where the live view collapses after a successful RAW capture.
    private void unlockFocusM9Continuous1T() {
        if (mPreviewRequestBuilder == null || mCaptureSession == null) {
            Log.d(TAG, "M9LIVEGL1T minimal unlock skipped: camera not ready");
            return;
        }
        try {
            mState = STATE_PREVIEW;
            mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER,
                    CameraMetadata.CONTROL_AF_TRIGGER_CANCEL);
            mCaptureSession.capture(mPreviewRequestBuilder.build(), mCaptureCallback,
                    mBackgroundHandler);
            mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER,
                    CameraMetadata.CONTROL_AF_TRIGGER_IDLE);
            mPreviewInputRequest = mPreviewRequestBuilder.build();
            mCaptureSession.setRepeatingRequest(mPreviewInputRequest, mCaptureCallback,
                    mBackgroundHandler);
            Log.d(TAG, "M9LIVEGL1T_CONTINUOUSPREVIEW1A minimalUnlock=true"
                    + " reset3A=false previewRebuildSequence=false");
        } catch (Exception e) {
            Log.d(TAG, "M9LIVEGL1T minimal unlock failed:" + e);
        }
    }

''' + method_anchor
one(method_anchor,method_new,"minimal unlock method")

old_bottom='''            else {
            mCaptureSession.stopRepeating();
            mCaptureSession.abortCaptures();
                switch (PhotonCamera.getSettings().selectedMode) {
'''
new_bottom='''            else {
                final CameraMode m9Mode1T = PhotonCamera.getSettings().selectedMode;
                final boolean m9KeepPreviewRepeating1T =
                        M9Config.isCaptureTest()
                                && m9Mode1T != CameraMode.UNLIMITED
                                && m9Mode1T != CameraMode.RAWVIDEO;
                if (!m9KeepPreviewRepeating1T) {
                    mCaptureSession.stopRepeating();
                    mCaptureSession.abortCaptures();
                } else {
                    Log.d(TAG, "M9LIVEGL1T_CONTINUOUSPREVIEW1A"
                            + " keepRepeating=true abortCaptures=false"
                            + " stillTarget=RAW_ONLY");
                }
                switch (m9Mode1T) {
'''
one(old_bottom,new_bottom,"capture session continuity")

old_unlock='''                            mBackgroundHandler.post(() -> {
                                if (!isDualSession)
                                    unlockFocus();
                                else
                                    createCameraPreviewSession(false);
                            });
'''
new_unlock='''                            mBackgroundHandler.post(() -> {
                                if (!isDualSession) {
                                    if (M9Config.isCaptureTest()
                                            && PhotonCamera.getSettings().selectedMode != CameraMode.UNLIMITED
                                            && PhotonCamera.getSettings().selectedMode != CameraMode.RAWVIDEO) {
                                        unlockFocusM9Continuous1T();
                                    } else {
                                        unlockFocus();
                                    }
                                } else {
                                    createCameraPreviewSession(false);
                                }
                            });
'''
one(old_unlock,new_unlock,"post capture unlock")

ccp.write_text(cc)
print("M9LIVEGL1T_CONTINUOUSPREVIEW1A applied")
print(" - M9 RAW capture is inserted while repeating preview stays active")
print(" - stopRepeating/abortCaptures bypassed for normal M9 still")
print(" - post-capture full 3A rebuild replaced by minimal AF release")
print(" - GL1B exposure authority and still renderer untouched")
