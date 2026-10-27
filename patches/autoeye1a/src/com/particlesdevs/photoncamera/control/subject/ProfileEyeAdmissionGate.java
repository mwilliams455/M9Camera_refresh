package com.particlesdevs.photoncamera.control.subject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * Separate, conservative profile-eye admission. The inherited frontal-face
 * HumanEyeAdmissionGate remains unchanged and continues to require TWO eyes,
 * a nose, mouth and three observations. Here precisely one valid eye plus nose
 * and mouth may qualify, but only after FOUR separate, fresh, coherent frames
 * with a stable ML Kit tracking ID. Face rectangles alone never qualify.
 *
 * No Camera2 calls, image storage or face identity recognition.
 */
public final class ProfileEyeAdmissionGate {
    public static final int REQUIRED_HITS = 4;
    public static final long MAX_GAP_NS = 550_000_000L;
    public static final long MAX_AGE_NS = 250_000_000L;
    private static final long FORGET_NS = 1_200_000_000L;
    private static final float MAX_STEP = .17f;
    private static final int MAX_TRACKED = 12;

    private static final class Run {
        int hits;
        long lastFrame;
        float x, y;
    }
    private final Map<Integer, Run> runs = new HashMap<>();
    private long epoch = Long.MIN_VALUE, lastFrame = Long.MIN_VALUE;

    public synchronized void beginSession(long token) {
        epoch=token;
        lastFrame=Long.MIN_VALUE;
        runs.clear();
    }

    public synchronized List<SubjectFocusPolicy.Face> admit(
            long token,long frameNs,long nowNs,List<SubjectFocusPolicy.Face> candidates) {
        List<SubjectFocusPolicy.Face> admitted = new ArrayList<>();
        if (token!=epoch || frameNs<=lastFrame || frameNs<=0 || nowNs<frameNs
                || nowNs-frameNs>MAX_AGE_NS) return admitted;
        lastFrame=frameNs;
        Iterator<Map.Entry<Integer, Run>> it=runs.entrySet().iterator();
        while(it.hasNext()) {
            Map.Entry<Integer, Run> entry=it.next();
            if (frameNs-entry.getValue().lastFrame>FORGET_NS) it.remove();
        }
        if (candidates==null) return admitted;
        for (SubjectFocusPolicy.Face candidate:candidates) {
            if (candidate==null || candidate.id<0 || !plausibleProfile(candidate)) continue;
            Run run=runs.get(candidate.id);
            if (run==null && runs.size()>=MAX_TRACKED) continue;
            boolean continuous = run!=null && frameNs>run.lastFrame
                    && frameNs-run.lastFrame<=MAX_GAP_NS
                    && Math.abs(candidate.cx()-run.x)<MAX_STEP
                    && Math.abs(candidate.cy()-run.y)<MAX_STEP;
            if (!continuous) run = new Run();
            run.hits=continuous?Math.min(REQUIRED_HITS,run.hits+1):1;
            run.lastFrame=frameNs;
            run.x=candidate.cx();run.y=candidate.cy();
            runs.put(candidate.id,run);
            if (run.hits>=REQUIRED_HITS) admitted.add(candidate);
        }
        return admitted;
    }

    public static boolean plausibleProfile(SubjectFocusPolicy.Face f) {
        if (f==null || !f.valid()) return false;
        float w=f.right-f.left,h=f.bottom-f.top;
        if (w<.065f || h<.075f || w*h<.007f) return false;
        boolean left=inside(f,f.leftEyeX,f.leftEyeY);
        boolean right=inside(f,f.rightEyeX,f.rightEyeY);
        if (left==right) return false; // exactly one eye, never a face-box shortcut
        if (!inside(f,f.noseX,f.noseY) || !inside(f,f.mouthX,f.mouthY))return false;
        float ex=left?f.leftEyeX:f.rightEyeX, ey=left?f.leftEyeY:f.rightEyeY;
        float eyeY=(ey-f.top)/h, noseY=(f.noseY-f.top)/h, mouthY=(f.mouthY-f.top)/h;
        float eyeX=(ex-f.left)/w;
        float eyeToNose=(f.noseY-ey)/h;
        float noseToMouth=(f.mouthY-f.noseY)/h;
        // A single eye-like dot must have recognisable face morphology.
        return eyeY>=.08f && eyeY<=.58f
                && eyeX>=.055f && eyeX<=.945f
                && noseY>.23f && noseY<.82f
                && mouthY>.42f && mouthY<.96f
                && eyeToNose>=.09f && eyeToNose<=.52f
                && noseToMouth>=.09f && noseToMouth<=.48f
                && Math.abs(f.noseX-ex)/w<=.70f
                && Math.abs(f.mouthX-f.noseX)/w<=.60f;
    }

    private static boolean inside(SubjectFocusPolicy.Face f,float x,float y){
        return Float.isFinite(x)&&Float.isFinite(y)
                && x>=f.left && x<=f.right && y>=f.top && y<=f.bottom;
    }
}
