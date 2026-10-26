package com.particlesdevs.photoncamera.control.tracking;

/** Settings-only relationship for opt-in focus-tracking switches. */
public final class TrackingTogglePolicy {
    public static final String TRACKING = "pref_focus_tracking";
    public static final String SUBJECT = "pref_focus_tracking_semantic";
    public static final String PREDICTIVE = "pref_focus_tracking_predictive";
    public static final String IDENTITY = "pref_focus_tracking_identity";
    private TrackingTogglePolicy() { }
    public static final class Correction {
        public final boolean enableTracking;
        public final boolean disableDependents,enableSubject,disableIdentity;
        private Correction(boolean enableTracking, boolean disableDependents,
                           boolean enableSubject,boolean disableIdentity) {
            this.enableTracking=enableTracking;
            this.disableDependents=disableDependents;
            this.enableSubject=enableSubject;
            this.disableIdentity=disableIdentity;
        }
    }
    /**
     * Do not disable previously saved dependent modes just because a disabled
     * parent switch is being inflated into the settings UI (initialization).
     */
    public static Correction onPersist(String changedKey,boolean enabled,boolean initializing) {
        boolean enableParent=enabled && (SUBJECT.equals(changedKey)||
                PREDICTIVE.equals(changedKey)||IDENTITY.equals(changedKey));
        boolean disableChildren=!initializing && !enabled && TRACKING.equals(changedKey);
        boolean enableSubject=enabled && IDENTITY.equals(changedKey);
        boolean disableIdentity=!initializing && !enabled && SUBJECT.equals(changedKey);
        return new Correction(enableParent,disableChildren,enableSubject,disableIdentity);
    }
}
