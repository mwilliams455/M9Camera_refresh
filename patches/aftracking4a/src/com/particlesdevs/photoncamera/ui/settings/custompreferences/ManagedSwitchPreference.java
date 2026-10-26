/*
 * Copyright (C) 2014 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.particlesdevs.photoncamera.ui.settings.custompreferences;

import android.content.Context;
import android.content.res.TypedArray;
import android.util.AttributeSet;

import androidx.preference.SwitchPreferenceCompat;
import androidx.preference.Preference;
import androidx.preference.PreferenceManager;
import com.particlesdevs.photoncamera.control.tracking.TrackingTogglePolicy;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.settings.SettingsManager;

/**
 * This class allows Settings UIs to display and set boolean values controlled
 * via the {@link SettingsManager}. The Default {@link SwitchPreferenceCompat} uses
 * {@link android.content.SharedPreferences} as a backing store; since the
 * {@link SettingsManager} stores all settings as Strings we need to ensure we
 * get and set boolean settings through the manager.
 */
public class ManagedSwitchPreference extends SwitchPreferenceCompat {
    private boolean fallback_value;
    /** Avoid treating switch inflation as an explicit user turn-off. */
    private boolean settingInitialValue;

    public ManagedSwitchPreference(Context context) {
        super(context);
    }

    public ManagedSwitchPreference(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    public ManagedSwitchPreference(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
    }

    @Override
    public boolean getPersistedBoolean(boolean defaultReturnValue) {
        PhotonCamera photonCamera = PhotonCamera.getInstance(getContext());
        if (photonCamera == null)
            return defaultReturnValue;
        else {
            SettingsManager settingsManager = photonCamera.getSettingsManager();
            if (settingsManager != null)
                return settingsManager.getBoolean(SettingsManager.SCOPE_GLOBAL, getKey(), defaultReturnValue);
            else
                return defaultReturnValue;
        }
    }

    @Override
    public boolean persistBoolean(boolean value) {
        PhotonCamera photonCamera = PhotonCamera.getInstance(getContext());
        if (photonCamera == null)
            return false;
        else {
            SettingsManager settingsManager = photonCamera.getSettingsManager();
            if (settingsManager != null) {
                String key=getKey();
                TrackingTogglePolicy.Correction dependency =
                        TrackingTogglePolicy.onPersist(key,value,settingInitialValue);
                settingsManager.set(SettingsManager.SCOPE_GLOBAL, key, value);
                if(dependency.enableTracking) {
                    settingsManager.set(SettingsManager.SCOPE_GLOBAL,
                            TrackingTogglePolicy.TRACKING,true);
                    refreshDependentSwitch(TrackingTogglePolicy.TRACKING,true);
                }
                if(dependency.disableDependents) {
                    settingsManager.set(SettingsManager.SCOPE_GLOBAL,
                            TrackingTogglePolicy.SUBJECT,false);
                    settingsManager.set(SettingsManager.SCOPE_GLOBAL,
                            TrackingTogglePolicy.PREDICTIVE,false);
                    refreshDependentSwitch(TrackingTogglePolicy.SUBJECT,false);
                    refreshDependentSwitch(TrackingTogglePolicy.PREDICTIVE,false);
                }
                return true;
            } else
                return false;
        }
    }

    /** Keep the visible switches in the Capture screen in sync with stored values. */
    private void refreshDependentSwitch(String key, boolean checked) {
        PreferenceManager manager=getPreferenceManager();
        if(manager==null)return;
        Preference preference=manager.findPreference(key);
        if(preference instanceof SwitchPreferenceCompat) {
            SwitchPreferenceCompat toggle=(SwitchPreferenceCompat)preference;
            if(toggle.isChecked()!=checked)toggle.setChecked(checked);
        }
    }

    private void set(boolean value) {
        setChecked(value);
        persistBoolean(value);
    }

    @Override
    protected void onSetInitialValue(Object defaultValue) {
        if (defaultValue == null) {
            defaultValue = fallback_value;
        }
        settingInitialValue=true;
        try { set(getPersistedBoolean((Boolean) defaultValue)); }
        finally { settingInitialValue=false; }
    }

    @Override
    protected Object onGetDefaultValue(TypedArray a, int index) {
        fallback_value = a.getBoolean(index, false);
        return a.getBoolean(index, false);
    }
}
