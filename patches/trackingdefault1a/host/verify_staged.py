#!/usr/bin/env python3
"""Static integration smoke gate for exact M9/Monochrome 3.13 staged source.

Pure host proof complements (not replaces) Android/Robolectric and on-phone checks.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1])
prefix=root/"app/src/main/java/com/particlesdevs/photoncamera"
tracker=(prefix/"ui/camera/FocusTrackingController.java").read_text()
switch=(prefix/"ui/settings/custompreferences/ManagedSwitchPreference.java").read_text()
human=(prefix/"ui/camera/HumanSubjectFocusController.java").read_text()
geometry=(prefix/"ui/camera/views/FocusTickGeometry.java").read_text()
gradle=(root/"app/build.gradle").read_text()
assert "versionCode 27313" in gradle
assert "versionName '3.13-trackingdefault1a'" in gradle

def control(xml,key,expected):
    hits=re.findall(r'<[^>]+android:key="'+re.escape(key)+r'"[^>]*?/>',xml,re.DOTALL)
    assert len(hits)==1,(key,len(hits))
    assert 'android:defaultValue="'+expected+'"' in hits[0],(key,expected)

for profile in ("m9","monochrom"):
    xml=(root/f"app/src/main/res/xml/preferences_{profile}.xml").read_text()
    control(xml,"pref_focus_tracking","true")
    control(xml,"pref_focus_tracking_semantic","true")
    control(xml,"pref_focus_auto_eye_enabled","true")
    control(xml,"pref_focus_tracking_predictive","false")
    control(xml,"pref_focus_tracking_identity","false")

assert "manager.getBoolean(SettingsManager.SCOPE_GLOBAL,KEY,true)" in tracker
assert "if (!manager.getBoolean(SettingsManager.SCOPE_GLOBAL, KEY, true)) return;" in tracker
assert "return TrackingDefaultPolicy.eligible(" in tracker
assert "PreferenceKeys.getAfMode()==CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE" in tracker
assert "FocusControlSettings.mode()==FocusControlPolicy.Mode.WIDE" in tracker
assert "if (!running || !enabled() || !autofocus) return false;" in tracker
assert "if (focus == null || !focus.valid()) {" in tracker
assert "clear(); return false;" in tracker
assert "if (selected && Math.abs(u - x) <= hx && Math.abs(v - y) <= hy)" in tracker
assert tracker.count("warmSemantic();")==1, "no model init without deliberate tap"
assert "TrackingDefaultPolicy.warmSemantic(selected,recognitionEnabled())" in tracker
assert "if (settingInitialValue) return true;" in switch
assert "if(dependency.disableDependents)" in switch
assert "if(dependency.enableSubject)" in switch
assert "fragment.hasExplicitArbitraryTrackingSelection()" in human
assert "eyeDisplayHalfWidth" in geometry and "eyeDisplayHalfHeight" in geometry
assert "34" not in tracker, "eye presentation left separate from arbitrary tracking"
print("PASS 3.13 staged default, migration, AF-C policy, idle and focus overlay gates")
