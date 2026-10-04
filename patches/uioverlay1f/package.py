"""Package the UI overlay build with all native libraries from the accepted 2.38 APK."""
from pathlib import Path
import copy, hashlib, json, re, subprocess, sys, zipfile

here = Path(__file__).resolve().parent
def sha(data): return hashlib.sha256(data).hexdigest()
def signature(name):
    return name == 'META-INF/MANIFEST.MF' or (name.startswith('META-INF/') and name.endswith(('.RSA','.DSA','.EC','.SF')))

def main(root,built,control,bt,out):
    root,built,control,bt,out = [p.resolve() for p in (root,built,control,bt,out)]
    out.mkdir(parents=True,exist_ok=True)
    assert sha(control.read_bytes()) == 'ca30fd5c41e44095f8fc1d142a967cbfd03092b978cf690c61634ce1ea608711'
    manifest = json.loads((here/'manifest.json').read_text())
    for name,digest in manifest['fileOverrides'].items(): assert sha((root/name).read_bytes()) == digest, name
    unsigned,aligned,final = [out/n for n in ['unsigned.apk','aligned.apk','M9Cam_2.44_UIOVERLAY1F.apk']]
    expected = {}
    with zipfile.ZipFile(control) as old, zipfile.ZipFile(built) as new, zipfile.ZipFile(unsigned,'w') as dst:
        assert old.testzip() is None and new.testzip() is None
        natives = {n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        assert len(natives) == 25
        assert {n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')} == natives
        assets = {n for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
        assert assets == {n for n in new.namelist() if n.startswith('assets/') and not n.endswith('/')}
        changed_assets = {name for name in assets if old.read(name) != new.read(name)}
        assert changed_assets == set()
        assert new.read('assets/shaders/preview/main_fs.glsl') == (root/'app/src/main/assets/shaders/preview/main_fs.glsl').read_bytes()
        for info in new.infolist():
            name = info.filename
            if signature(name): continue
            data = old.read(name) if name in natives else new.read(name)
            expected[name] = sha(data)
            dst.writestr(copy.copy(info),data)
        dex = b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9SHARPNESSMENU1A','pref_m9_sharpness','M9SharpnessStage','exact_stage_bypass_2_27_pixels','M9CONTRASTMENU1A','pref_m9_saturation','M9CaptureParameters','M9ShootingProfiles','pref_m9_shooting_profiles_v1','pref_m9_shooting_profile_active','M9DisplayAidsController','M9DisplayAidsView','pref_m9_highlight_warning','pref_m9_shadow_warning','M9PREVIEWBRIGHTNESS1A','uniformPreviewToneGain','M9LEICAEV1A','shared_persistent_stop_value_menu_wheel_profiles','M9AUTOISO1A','M9AutoIsoRuntime','M9ExposureAllocation','pref_m9_auto_iso_max','pref_m9_auto_iso_slowest','slowestExceededAtIsoCeiling','M9AELOCK1A','M9SELFTIMER1A','metering_memory_lock','neutralReferenceLiveDuringAeLock','M9BRACKET1A','M9BracketRuntime','leica_separate_bracket','bracketingSeriesId','bracketingRequestedEv','pref_m9_bracket_enabled']:
            assert marker.encode() in dex, marker
        for marker in ['M9OverlayController','M9OverlayPolicy','M9LinearManualView','M9LinearRulerSelection','showRenderers','selectOverlayMode','M9ShootingControls']:
            assert marker.encode() in dex, marker
        assert b'uCameraSamplingMatrix' not in dex
        assert 'res/xml/preferences_m9.xml' in new.namelist()
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signer = ['java','-jar',str(bt/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    cert = subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in cert
    badging = subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    for marker in ["name='com.m9project.m9cam.photon'","versionCode='27244'","versionName='2.44-m9uioverlay1f'"]:
        assert marker in badging, marker
    xml = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/xml/preferences_m9.xml',str(final)],text=True)
    for name in ['image','capture','output','display','advanced']:
        assert 'pref_m9_'+name+'_screen' in xml
    assert 'pref_m9_profiles_screen' in xml
    assert 'm9_ev_info' in xml
    for key in ['pref_m9_auto_iso_screen','pref_m9_auto_iso_max','pref_m9_auto_iso_slowest']: assert key in xml
    for key in ['pref_m9_highlight_warning','pref_m9_shadow_warning']:
        assert key in xml
    topbar = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/layout/layout_main_topbar.xml',str(final)],text=True)
    resources = subprocess.check_output([str(bt/'aapt2'),'dump','resources',str(final)],text=True)
    ev_key = re.search(r'resource (0x[0-9a-f]+) string/pref_expocompensation_seekbar_key\b', resources).group(1)
    ev_values = re.search(r'resource (0x[0-9a-f]+) array/m9_ev_values\b', resources).group(1)
    ev_nodes = [part for part in xml.split('E: ') if 'key(0x010101e8)=@'+ev_key in part]
    assert len(ev_nodes) == 1 and ev_nodes[0].startswith('ListPreference')
    assert 'entryValues(0x010101f8)=@'+ev_values in ev_nodes[0]
    for resource in ['m9_display_aids_button','m9_display_aids_overlay','m9_display_mode_entries','m9_ev_entries','m9_ev_values']:
        assert resource in resources,resource
    for key,default,array in [('pref_m9_auto_iso_max','2500','m9_auto_iso_max_values'),('pref_m9_auto_iso_slowest','0','m9_auto_iso_slowest_values')]:
        node=[part for part in xml.split('E: ') if '"'+key+'"' in part]
        assert len(node)==1 and node[0].startswith('ListPreference'),key
        assert re.search(r'defaultValue\(0x010101ed\)="?'+default+r'"?(?:\s|$)',node[0]),node[0]
        ref=re.search(r'resource (0x[0-9a-f]+) array/'+array+r'\b',resources).group(1)
        assert 'entryValues(0x010101f8)=@'+ref in node[0]
    for label in ['ISO 160','ISO 2500','Lens dependent','1/125 s','1/8 s']: assert label in resources,label
    for label in ['−3.0 EV' ,'−0.7 EV','0.0 EV','+0.3 EV','+3.0 EV']: assert label in resources,label
    for name in ['m9_ae_lock_button','timer_2s','timer_12s','ic_timer2s_m9','ic_timer12s_m9']:
        assert name in resources,name
    lock_id=re.search(r'resource (0x[0-9a-f]+) id/m9_ae_lock_button\b',resources).group(1)
    assert lock_id in topbar
    for label in ['AE-L','2 seconds','12 seconds','2s','12s']: assert label in resources,label
    timer_block=re.search(r'resource 0x[0-9a-f]+ array/countdowntimer_entryvalues\b(.*?)(?=\n    resource |\Z)',resources,re.S).group(1)
    assert 'size=3' in timer_block and re.search(r'\[\s*0,\s*2,\s*12\s*\]',timer_block),timer_block
    for key in ['pref_m9_bracket_enabled','pref_m9_bracket_frames','pref_m9_bracket_step','pref_m9_bracket_order']:
        assert key in xml,key
    for name in ['m9_bracket_step_seven_entries','m9_bracket_step_seven_values','m9_bracket_order_entries']:
        assert name in resources,name
    for label in ['0.5 EV','1.0 EV','1.5 EV','2.0 EV','3 photographs','5 photographs','7 photographs']:
        assert label in resources,label
    enabled=[part for part in xml.split('E: ') if '"pref_m9_bracket_enabled"' in part]
    assert len(enabled)==1 and re.search(r'defaultValue\(0x010101ed\)="?0"?(?:\s|$)',enabled[0])
    bottom = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/layout/layout_main_bottombar.xml',str(final)],text=True)
    controls = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/layout/layout_m9_overlay_controls.xml',str(final)],text=True)
    def resource_id(name): return re.search(r'resource (0x[0-9a-f]+) id/'+name+r'\b',resources).group(1)
    assert bottom.index(resource_id('m9_overlay_photo')) < bottom.index(resource_id('m9_overlay_motion'))
    control_ids=[resource_id('m9_overlay_'+n) for n in ['iso','shutter','ev','focus','wb','settings']]
    assert [controls.index(n) for n in control_ids] == sorted(controls.index(n) for n in control_ids)
    for name in ['m9_overlay_capture_status','m9_overlay_renderer','m9_overlay_lens_scroll','m9_overlay_unavailable']:
        assert name in resources,name
    assert 'Not installed' in resources
    assert resource_id('m9_overlay_quick_controls') in topbar
    assert 'Shooting controls' in resources
    for name in ['m9_overlay_mode_underline','m9_overlay_mode_text','m9_overlay_header','m9_shooting_hint','m9_overlay_highlights','m9_overlay_shadows']:
        assert name in resources,name
    assert resource_id('m9_overlay_torch') in topbar and resource_id('m9_overlay_night') in topbar
    assert resource_id('m9_overlay_capture_status') in topbar
    assert 'm9_overlay_active_render' not in root.joinpath('app/src/main/res/layout/layout_main_topbar.xml').read_text()
    camera_menu = [part for part in xml.split('E: ') if '"pref_video_settings_submenu"' in part]
    assert len(camera_menu) == 1 and re.search(r'isPreferenceVisible\([^)]*\)=false', camera_menu[0])
    flat = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/layout/layout_m9_linear_manual.xml',str(final)],text=True)
    assert 'M9LinearManualView' in flat
    assert 'm9_overlay_panel_bg' in resources and 'm9_overlay_pill_bg' in resources
    with zipfile.ZipFile(final) as apk:
        assert apk.testzip() is None
        assert {n:sha(apk.read(n)) for n in apk.namelist() if not signature(n)} == expected
    report = dict(status='passed',version='2.44-m9uioverlay1f',bytes=final.stat().st_size,
        sha256=sha(final.read_bytes()),originalNativeLibrariesPreserved=sorted(natives),
        addedNativeLibraries=[],allAssetsExactlyMatchAccepted238=True,changedAssets=sorted(changed_assets),signatureMatches238=True,
        alignment16KiB=True,compiledM9MenuPresent=True,compiledProfileScreenPresent=True,compiledClippingControlsPresent=True,compiledAutoIsoControlsAndDefaults=True,compiledAeLockButtonAndLeicaTimer=True,compiledBracketMenuDefaultOff=True,compiledFlatManualRuler=True,opaqueClippedControlBackdrops=True,compiledRefreshedOverlay=True,photoThenMotionOrder=True,settingsBesideManualControls=True,futureRendererCardsDisabled=True,phoneValidationPending=True,compiledShootingControlsChevron=True,compiledIconPanel=True,compiledTextModeStrip=True,compiledTorchAndNightButtons=True,compiledWbBeforeSettings=True,compiledVideoPreferenceScreenHidden=True)
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SIGNATURE_CHECK.txt').write_text(cert)
    (out/'APK_BADGING.txt').write_text(badging)
    (out/'COMPILED_M9_MENU.txt').write_text(xml)
    unsigned.unlink(); aligned.unlink()
    print(json.dumps(report,indent=2))

if __name__ == '__main__': main(*map(Path,sys.argv[1:]))
