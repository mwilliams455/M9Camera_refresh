from pathlib import Path
import sys,json,shutil,importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('parent1d',HERE.parent/'colourtrial1d/apply.py');parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
BASE=parent.BASE;APP=parent.APP;LOG=parent.LOG
LIFE=BASE+'util/log/ActivityLifecycleMonitor.java';SPOOL=BASE+'m9/M9DiagnosticBurstSpool.java';JOURNAL=BASE+'util/M9LocalLog1E.java'
ID='M9COLOURTRIAL1E';CHANGED={APP,LOG,LIFE,SPOOL,'app/build.gradle'}
def verify(root):
 p=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text());now=parent.inventory(root)
 assert now==p['after'],'source drift'
 assert {k for k in p['before'] if now[k]!=p['before'][k]}==CHANGED
 assert set(now)-set(p['before'])=={JOURNAL}
 for source,dest in [('Log.java',LOG),('M9LocalLog1E.java',JOURNAL),('M9DiagnosticBurstSpool.java',SPOOL)]:assert (HERE/source).read_bytes()==(root/dest).read_bytes()
 assert all(now[k]==v for k,v in p['before'].items() if k not in CHANGED)
 return {'revision':ID,'version':'1.67-m9colourtrial1e-tg1','versionCode':26687,'changed':sorted(CHANGED),'render_native_preview_assets_JPEG_DNG_unchanged':True,'device_validation_pending':True}
def main(root):
 receipt=root/(ID+'_SOURCE_PROOF.json')
 if receipt.exists():print(json.dumps(verify(root),indent=2));return
 parent.verify(root);before=parent.inventory(root);replace=parent.replace
 a=replace((root/APP).read_text(),'        sPhotonCamera = this;','        sPhotonCamera = this;\n        Log.initPrivate(this);')
 l=(root/LIFE).read_text();l=replace(l,'    private static final String TAG = "ActivityMonitor";','    private static final String TAG = "ActivityMonitor";\n    private int startedActivities;')
 l=replace(l,'    public void onActivityStarted(@NonNull Activity activity) {','''    public void onActivityStarted(@NonNull Activity activity) {
        if (++startedActivities == 1) {
            Log.setAppVisible(true);
            com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool.setAppVisible(true);
        }''')
 l=replace(l,'    public void onActivityStopped(@NonNull Activity activity) {','''    public void onActivityStopped(@NonNull Activity activity) {
        startedActivities = Math.max(0, startedActivities - 1);
        if (startedActivities == 0) {
            Log.setAppVisible(false);
            com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool.setAppVisible(false);
        }''')
 g=replace((root/'app/build.gradle').read_text(),'versionCode 26686','versionCode 26687');g=replace(g,"versionName '1.66-m9colourtrial1d-tg1'","versionName '1.67-m9colourtrial1e-tg1'")
 (root/APP).write_text(a);(root/LIFE).write_text(l);(root/'app/build.gradle').write_text(g)
 for source,dest in [('Log.java',LOG),('M9LocalLog1E.java',JOURNAL),('M9DiagnosticBurstSpool.java',SPOOL)]:shutil.copyfile(HERE/source,root/dest)
 receipt.write_text(json.dumps({'revision':ID,'before':before,'after':parent.inventory(root)},indent=2)+'\n');print(json.dumps(verify(root),indent=2))
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
