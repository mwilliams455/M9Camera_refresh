"""Check display-only integration, existing preference contracts and photographic source."""
from pathlib import Path
import hashlib,json,sys
import xml.etree.ElementTree as ET
A='{http://schemas.android.com/apk/res/android}'; P='{http://schemas.android.com/apk/res-auto}'
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main(parent,root,output):
    here=Path(__file__).resolve().parent
    manifest=json.loads((here/'manifest.json').read_text())
    changed=set(manifest['parentFiles'])-{'app/build.gradle'}
    added=set(manifest['fileOverrides'])-set(manifest['parentFiles'])
    old={p.relative_to(parent).as_posix():p for p in (parent/'app/src').rglob('*') if p.is_file()}
    new={p.relative_to(root).as_posix():p for p in (root/'app/src').rglob('*') if p.is_file()}
    assert new.keys()-old.keys()==added
    assert not old.keys()-new.keys()
    for name,path in old.items():
        if name not in changed: assert digest(path)==digest(new[name]), name
    for name,expected in manifest['fileOverrides'].items():assert digest(root/name)==expected,name
    # Existing route, class, values and defaults remain; only display selector text/options change.
    def nodes(path):
        found={}
        def walk(n,route):
            key=n.get(A+'key');route=route+([key] if key else [])
            if key:
                assert key not in found,key
                found[key]=(route,n.tag,n.attrib)
            for child in n:walk(child,route)
        walk(ET.parse(path).getroot(),[]);return found
    xml='app/src/main/res/xml/preferences_m9.xml';before=nodes(parent/xml);after=nodes(root/xml)
    assert after.keys()-before.keys()=={'pref_m9_highlight_warning','pref_m9_shadow_warning'}
    special={'@string/pref_show_afdata_key','m9_menu_histogram_info'}
    for key,record in before.items():
        if key not in special: assert record==after[key],key
        else:
            assert record[:2]==after[key][:2],key
            assert record[2].get(A+'defaultValue')==after[key][2].get(A+'defaultValue'),key
    assert after['pref_m9_highlight_warning'][2][A+'defaultValue']=='0'
    assert after['pref_m9_shadow_warning'][2][A+'defaultValue']=='-1'
    j='app/src/main/java/com/particlesdevs/photoncamera/'
    prefs=(root/(j+'settings/PreferenceKeys.java')).read_text()
    for key in ['HIGHLIGHT_KEY','SHADOW_KEY']:
        assert 'COMMON_KEYS.add(com.particlesdevs.photoncamera.m9.M9DisplayAids.'+key+');' in prefs
        assert 'com.particlesdevs.photoncamera.m9.M9DisplayAids.'+key+'.equals(key)' in prefs
    controller=(root/(j+'ui/camera/M9DisplayAidsController.java')).read_text()
    for text in ['PixelCopy.request(source,new Rect(','gate.accepts(ticket)','Arrays.equals(bounds,rect())','gate.finish()','preferences.unregisterOnSharedPreferenceChangeListener(this)','source.getLocationInWindow','frame.getLocationInWindow','gate.isBusy()']:
        assert text in controller,text
    fragment=(root/(j+'ui/camera/CameraFragment.java')).read_text()
    for text in ['m9DisplayAids.start()','m9DisplayAids.stop()','m9DisplayAids.close()','m9DisplayAids.hudMode()']:
        assert text in fragment,text
    overlay=ET.parse(root/'app/src/main/res/layout/layout_main_viewfinder.xml').getroot()
    aid=next(n for n in overlay.iter() if n.get(A+'id')=='@+id/m9_display_aids_overlay')
    assert aid.get(A+'clickable')=='false' and aid.get(A+'focusable')=='false'
    for side in ['Top','Bottom','Start','End']:
        assert aid.get(P+'layout_constraint'+side+'_to'+side+'Of')=='@id/viewfinder_frame'
    top=ET.parse(root/'app/src/main/res/layout/layout_main_topbar.xml').getroot()
    button=next(n for n in top.iter() if n.get(A+'id')=='@+id/m9_display_aids_button')
    assert button.get(P+'layout_constraintStart_toEndOf')=='@id/grid_toggle_button'
    assert button.get(A+'contentDescription')=='@string/m9_display_title'
    view=(root/(j+'ui/camera/views/viewfinder/M9DisplayAidsView.java')).read_text()
    assert 'int normalized=(value%360+360)%360;' in view
    report=dict(status='passed',unchangedExistingAppSourceFiles=len(old)-len(changed),
        changedExistingAppSourceFiles=sorted(changed),addedAppSourceFiles=sorted(added),
        savedPhotoProcessingCapturePlanningShadersAssetsAndNativeSourceUnchanged=True,
        shootingProfileImplementationUnchanged=True,existingPhotographicMenuRoutesAndDefaultsPreserved=True,
        globalWarningsExcludedFromPerLensSnapshots=True,displayOverlayNoninteractive=True,
        previewSamplingCroppedToVisibleFrame=True,lifecycleAndSingleReadbackGuardPresent=True,
        negativeAndPositiveLandscapeRotationsHandled=True,phoneUiValidationPending=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main(*map(lambda p:Path(p).resolve(),sys.argv[1:]))
