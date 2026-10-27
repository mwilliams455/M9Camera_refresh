package com.particlesdevs.photoncamera.control.subject;

/** Camera-independent admission for default automatic HUMAN eye autofocus.
 * Not a replacement for Camera2 AF-C or the existing opt-in object tracker.
 * Default ON applies only to standard Wide-area still shooting on AF-C.
 */
public final class AutoEyeFocusPolicy {
    private AutoEyeFocusPolicy() {}

    public static boolean allowed(boolean settingEnabled, boolean stillPhotoMode,
                                  boolean continuousPictureAf, boolean wideArea,
                                  boolean petFocusExplicit) {
        return settingEnabled && stillPhotoMode && continuousPictureAf
                && wideArea && !petFocusExplicit;
    }

    /** Deliberately selected objects always outrank automatically found faces. */
    public static boolean mayOwnRegion(boolean allowed, boolean manualTapOverride,
                                       boolean explicitObjectSelected) {
        return allowed && !manualTapOverride && !explicitObjectSelected;
    }
}
