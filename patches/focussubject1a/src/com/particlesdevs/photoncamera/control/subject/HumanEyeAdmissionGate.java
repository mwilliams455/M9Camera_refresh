package com.particlesdevs.photoncamera.control.subject;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * FOCUSSUBJECT1B: fail-closed human eye AF admission.
 *
 * A face-shaped rectangle alone must NEVER drive the lens. Require two eyes,
 * a nose and a mouth in plausible relative positions, then three temporally
 * distinct consistent detector frames with one stable ML Kit tracking ID.
 *
 * All values are normalized displayed-preview coordinates. Face feature
 * geometry is evaluated relative to each face box, so portrait aspect ratios
 * and camera rotation do not change the proportions. This is an engineering
 * false-positive guard, not proof of human identity.
 */
public final class HumanEyeAdmissionGate {
    public static final int REQUIRED_HITS = 3;
    public static final long MAX_GAP_NS = 550_000_000L;
    public static final long MAX_INPUT_AGE_NS = 250_000_000L;
    private static final long FORGET_NS = 1_200_000_000L;
    private static final float MAX_CENTRE_STEP = .24f;
    private final Map<Integer, Run> runs = new HashMap<>();
    private long epoch = Long.MIN_VALUE;
    private long lastFrameNs = Long.MIN_VALUE;

    private static final class Run {
        int hits;
        long lastSeenNs;
        float x, y;
    }

    public synchronized void beginSession(long sessionEpoch) {
        epoch = sessionEpoch;
        lastFrameNs = Long.MIN_VALUE;
        runs.clear();
    }

    /**
     * Every rejected face is absent from the output. In particular, false
     * detections without landmarks can never fall through to "face centre".
     */
    public synchronized List<SubjectFocusPolicy.Face> admit(
            long sessionEpoch, long frameNs, long nowNs, List<SubjectFocusPolicy.Face> faces) {
        ArrayList<SubjectFocusPolicy.Face> accepted = new ArrayList<>();
        if (sessionEpoch != epoch || frameNs <= lastFrameNs || frameNs <= 0
                || nowNs < frameNs || nowNs - frameNs > MAX_INPUT_AGE_NS) {
            return accepted;
        }
        lastFrameNs = frameNs;
        Iterator<Map.Entry<Integer, Run>> it = runs.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<Integer, Run> e = it.next();
            if (nowNs - e.getValue().lastSeenNs > FORGET_NS) it.remove();
        }
        if (faces == null) return accepted;

        // Cap tracker state even when a defective detector reports many IDs.
        for (SubjectFocusPolicy.Face face : faces) {
            if (face == null || face.id < 0 || !hasCoherentEyeLandmarks(face)) continue;
            if (!runs.containsKey(face.id) && runs.size() >= 12) continue;
            Run run = runs.get(face.id);
            boolean continuous = run != null && frameNs > run.lastSeenNs
                    && frameNs - run.lastSeenNs <= MAX_GAP_NS
                    && Math.abs(face.cx() - run.x) < MAX_CENTRE_STEP
                    && Math.abs(face.cy() - run.y) < MAX_CENTRE_STEP;
            if (!continuous) run = new Run();
            run.hits = continuous ? Math.min(REQUIRED_HITS, run.hits + 1) : 1;
            run.lastSeenNs = frameNs;
            run.x = face.cx(); run.y = face.cy();
            runs.put(face.id, run);
            if (run.hits >= REQUIRED_HITS) accepted.add(face);
        }
        return accepted;
    }

    /** Validates a face-like configuration without trusting box alone. */
    public static boolean hasCoherentEyeLandmarks(SubjectFocusPolicy.Face face) {
        if (face == null || !face.valid()) return false;
        final float w = face.right - face.left, h = face.bottom - face.top;
        if (w < .055f || h < .055f) return false;
        if (!within(face,face.leftEyeX,face.leftEyeY)
                || !within(face,face.rightEyeX,face.rightEyeY)
                || !within(face,face.noseX,face.noseY)
                || !within(face,face.mouthX,face.mouthY)) return false;

        // Frame-aspect independent face-local coordinates.
        double ex = (face.rightEyeX-face.leftEyeX)/w;
        double ey = (face.rightEyeY-face.leftEyeY)/h;
        double eyeSep = Math.hypot(ex,ey);
        if (eyeSep < .18 || eyeSep > .87) return false;
        double midX = (face.leftEyeX+face.rightEyeX)*.5;
        double midY = (face.leftEyeY+face.rightEyeY)*.5;
        double nx = (face.noseX-midX)/w, ny=(face.noseY-midY)/h;
        double mx = (face.mouthX-midX)/w, my=(face.mouthY-midY)/h;
        // Cross product with eye line gives the axis toward nose/mouth
        // even when a face is tilted. Require mouth past nose on same side.
        double noseBelow = (ex*ny-ey*nx)/eyeSep;
        double mouthBelow = (ex*my-ey*mx)/eyeSep;
        if (Math.abs(noseBelow) < .085 || Math.abs(noseBelow) > .66
                || noseBelow*mouthBelow <= 0
                || Math.abs(mouthBelow) < Math.abs(noseBelow)+.045
                || Math.abs(mouthBelow) > .95) return false;
        double noseSide = (nx*ex+ny*ey)/eyeSep;
        double mouthSide = (mx*ex+my*ey)/eyeSep;
        return Math.abs(noseSide) <= .46 && Math.abs(mouthSide) <= .60;
    }

    private static boolean within(SubjectFocusPolicy.Face face,float x,float y) {
        return Float.isFinite(x) && Float.isFinite(y)
                && x >= face.left && x <= face.right
                && y >= face.top && y <= face.bottom;
    }
}
