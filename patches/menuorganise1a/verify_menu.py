"""Check the menu/storage contract and unchanged photographic source against 2.28."""
from pathlib import Path
import hashlib, json, sys
import xml.etree.ElementTree as ET

A = '{http://schemas.android.com/apk/res/android}'
P = '{http://schemas.android.com/apk/res-auto}'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def check(parent, root):
    resource = 'app/src/main/res/'
    values = {}
    for path in (root/resource/'values').glob('*.xml'):
        for item in ET.parse(path).getroot():
            if item.tag == 'string': values['@string/'+item.attrib['name']] = item.text
    def key(node):
        raw = node.get(A+'key')
        return values.get(raw, raw)
    old = ET.parse(parent/resource/'xml/preferences.xml').getroot()
    new = ET.parse(root/resource/'xml/preferences_m9.xml').getroot()
    oldkeys = {key(n): n for n in old.iter() if key(n)}
    newkeys = [key(n) for n in new.iter() if key(n)]
    assert len(newkeys) == len(set(newkeys)), 'Duplicate preference keys'
    screens = ['image','capture','output','display','advanced']
    assert [key(n) for n in new] == ['pref_m9_'+n+'_screen' for n in screens]
    assert all(n.tag == 'PreferenceScreen' and len(n) for n in new)
    # Every moved control retains its preference class and all persistence attributes.
    checked = []
    for node in new.iter():
        k = key(node)
        if k not in oldkeys: continue
        before = oldkeys[k]
        assert before.tag == node.tag, k
        expected = dict(before.attrib)
        if k == 'pref_show_afdata_key': expected[A+'title'] = '@string/m9_menu_hud_title'
        assert node.attrib == expected, (k, node.attrib, expected)
        checked.append(k)
    already_hidden = {
        'pref_frame_count_key','pref_save_heic_key','pref_ultrahdr_key','pref_hdrx_nr_key',
        'pref_sharpness_seekbar_key','pref_contrast_seekbar_key','pref_noise_seekbar_key',
        'pref_merge_seekbar_key','pref_shadows_seekbar_key','pref_compressor_seekbar_key',
        'pref_align_method_key',
    }
    for node in oldkeys['pref_category_jpg_key'].iter():
        if key(node): already_hidden.add(key(node))
    newly_hidden = {'pref_show_watermark_key','pref_energy_safe_key','pref_preview_format_key'}
    omitted_controls = {k for k,n in oldkeys.items() if n.tag != 'PreferenceCategory' and k not in newkeys}
    assert omitted_controls == (already_hidden | newly_hidden) - {'pref_category_jpg_key'}, omitted_controls
    menu = ET.parse(root/resource/'values/m9_menu.xml').getroot()
    arrays = {n.attrib['name']:[i.text for i in n] for n in menu if n.tag == 'string-array'}
    assert arrays['m9_menu_timer_indices'] == ['0','1','2']
    timer = next(n for n in new.iter() if key(n) == 'pref_countdown_timer_key')
    assert timer.tag == 'ListPreference' and timer.get(A+'defaultValue') == '0'
    original_arrays = ET.parse(root/resource/'values/arrays.xml').getroot()
    durations = next(n for n in original_arrays if n.get('name') == 'countdowntimer_entryvalues')
    assert [i.text for i in durations] == ['0','3','10']
    # Do not silently regenerate any source, assets, defaults or native libraries.
    changes = {'app/build.gradle','app/src/main/java/com/particlesdevs/photoncamera/ui/settings/SettingsActivity.java'}
    additions = {'app/src/main/res/xml/preferences_m9.xml','app/src/main/res/values/m9_menu.xml'}
    oldpaths = {p.relative_to(parent).as_posix():p for p in (parent/'app/src').rglob('*') if p.is_file()}
    newpaths = {p.relative_to(root).as_posix():p for p in (root/'app/src').rglob('*') if p.is_file()}
    assert newpaths.keys() - oldpaths.keys() == additions
    assert not oldpaths.keys() - newpaths.keys()
    unchanged = 0
    for name,path in oldpaths.items():
        if name not in changes:
            assert sha(path) == sha(newpaths[name]), name
            unchanged += 1
    activity = changes - {'app/build.gradle'}
    name = activity.pop()
    before = (parent/name).read_text()
    after = (root/name).read_text()
    expected = before.replace('            setPreferencesFromResource(R.xml.preferences, rootKey);',
        '            // M9MENUORGANISE1A: only change the hierarchy. Preference keys, classes,\n'
        '            // defaults and the existing child-screen navigation remain unchanged.\n'
        '            setPreferencesFromResource(usesM9PhotoSettings()\n'
        '                    ? R.xml.preferences_m9 : R.xml.preferences, rootKey);')
    assert after == expected, 'Unexpected activity change'
    routes = {}
    def visit(node, path):
        k = key(node)
        if node.tag == 'PreferenceScreen':
            path = path + [k]
            routes[k] = path
        for child in node: visit(child, path)
    visit(new, [])
    for k in ['pref_about_key','pref_video_settings_submenu','pref_tunable_submenu','pref_sensor_config_submenu','pref_video_tunable_submenu','pref_video_hdr_tunable_submenu']:
        assert k in routes, k
    return dict(status='passed',movedNodesPreservingAllAttributes=checked,
        fiveRootMenus=screens,childRoutes=routes,timerStoredIndices=['0','1','2'],
        timerSeconds=[0,3,10],newlyHiddenRows=sorted(newly_hidden),
        hiddenStoredValuesUntouched=True,originalPreferenceResourceUnchanged=True,
        unchangedAppSourceFiles=unchanged,photographicSourceUnchanged=True,
        runtimePhoneNavigationChecked=False)

if __name__ == '__main__':
    report = check(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
    output = Path(sys.argv[3]); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('Menu contract passed:', len(report['movedNodesPreservingAllAttributes']), 'preserved nodes;',report['unchangedAppSourceFiles'],'unchanged source files')
