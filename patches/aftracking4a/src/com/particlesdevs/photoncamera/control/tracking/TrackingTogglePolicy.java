package com.particlesdevs.photoncamera.control.tracking;

/** Settings-only relationship for opt-in focus-tracking switches. */
public final class TrackingTogglePolicy {
    public static final String TRACKING = "pref_focus_tracking";
    public static final String SUBJECT = "pref_focus_tracking_semantic";
    public static final String PREDICTIVE = "pref_focus_tracking_predictive";
    private TrackingTogglePolicy() { }
    public static final class Correction {
        public final boolean enableTracking;
        public final boolean disableDependents;
        private Correction(boolean enableTracking, boolean disableDependents) {
            this.enableTracking=enableTracking;
            this.disableDependents=disableDependents;
        }
    }
    /**
     * Do not disable previously saved dependent modes just because a disabled
     * parent switch is being inflated into the settings UI (initialization).
     */
    public static Correction onPersist(String changedKey,boolean enabled,boolean initializing) {
        boolean enableParent=enabled && (SUBJECT.equals(changedKey)||PREDICTIVE.equals(changedKey));
        boolean disableChildren=!initializing && !enabled && TRACKING.equals(changedKey);
        return new Correction(enableParent,disableChildren);
    }
}
