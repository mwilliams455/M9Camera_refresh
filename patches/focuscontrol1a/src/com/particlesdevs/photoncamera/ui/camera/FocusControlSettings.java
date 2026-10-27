package com.particlesdevs.photoncamera.ui.camera;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;
import com.particlesdevs.photoncamera.settings.SettingsManager;

/** Shared focus-area preferences for M9 and Monochrom; Wide preserves 3.03. */
final class FocusControlSettings {
    static final String AREA_KEY="pref_focus_area_mode";
    static final String WIDTH_KEY="pref_focus_area_custom_width";
    static final String HEIGHT_KEY="pref_focus_area_custom_height";
    static final String AF_FEEDBACK_KEY="pref_focus_af_state_feedback";
    private FocusControlSettings(){}

    static FocusControlPolicy.Mode mode(){
        return FocusControlPolicy.parseMode(PhotonCamera.getSettingsManagerStatic()
                .getString(SettingsManager.SCOPE_GLOBAL,AREA_KEY,"WIDE"));
    }
    static void configure(FocusControlPolicy policy){
        policy.configure(mode(),dim(WIDTH_KEY),dim(HEIGHT_KEY));
    }
    static boolean showAfFeedback(){
        return PhotonCamera.getSettingsManagerStatic().getBoolean(
                SettingsManager.SCOPE_GLOBAL,AF_FEEDBACK_KEY,true);
    }
    private static float dim(String key) {
        String value=PhotonCamera.getSettingsManagerStatic()
                .getString(SettingsManager.SCOPE_GLOBAL,key,"0.20");
        try{
            float fraction=Float.parseFloat(value);
            return Float.isFinite(fraction)?fraction:.20f;
        }catch(NumberFormatException ignored){return .20f;}
    }
}
