"""Memory/lifetime repair and durable exit evidence on exact COLOURTRIAL1C."""
from pathlib import Path
import sys,json,shutil
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'));from m9rbrollback1a import inventory
sys.path.insert(0,str(HERE.parent/'colourtrial1c'));from apply import verify as parent_verify,replace,RENDERER,BASE
ID='M9COLOURTRIAL1D';CPP='app/src/main/cpp/colourtrial1c/'
APP=BASE+'app/PhotonCamera.java';LOG=BASE+'util/Log.java';HELPER=BASE+'m9/render/M9ColourTrial1C.java'
CRASH=BASE+'m9/render/M9RenderCrash1D.java'
CHANGED={RENDERER,APP,LOG,HELPER,CPP+'reconstruct.cpp',CPP+'native.inc','app/build.gradle'}
def transform(s):
 a='''        Path jpgPath = null;
        Path pngPath = null;
        Bitmap bitmap = null;
        try {'''
 s=replace(s,a,a.replace('        try {','''        if (primaryRoute && !m9LiveWysiwyg1ALiveRoute) M9RenderCrash1D.begin(dngPath);
        try {'''))
 s=replace(s,'            RenderCore out = renderNativeSourceProduction1P(', '            M9RenderCrash1D.stage("raw_normalize");\n            RenderCore out = renderNativeSourceProduction1P(')
 s=replace(s,'                colourTrial1CJson = M9ColourTrial1C.apply(', '                M9RenderCrash1D.stage("raw_noise_amaze");\n                colourTrial1CJson = M9ColourTrial1C.apply(')
 a='nativeShading.representationScale, nativeCaptureResult, NATIVE_COLOR_WORKERS);'
 s=replace(s,a,a+'\n                M9RenderCrash1D.stage("camera_matrix_meter");')
 s=replace(s,'M9ColourTrial1C.prepareFrame(', 'M9ColourTrial1C.prepareFrameInPlace(')
 s=replace(s,'            final long colourTrialPrepareStart = System.nanoTime();','''            M9RenderCrash1D.stage("preSAT_chroma_in_place");
            final long colourTrialPrepareStart = System.nanoTime();''')
 s=replace(s,'            // Retained Java ByteBuffer is passed to every synchronous JNI call.','''            // Borrow the owning cam16 storage after its final meter/audit read.
            // All renders finish before cam16.release(); no whole-frame Q14 allocation.''')
 start=s.index('final ByteBuffer colourTrialQ14');a='            for (int y0 = 0; y0 < height; y0 += NATIVE_COLOR_BLOCK_ROWS) {'
 pos=s.index(a,start);s=s[:pos]+'            M9RenderCrash1D.stage("SAT_curve_bitmap");\n'+s[pos:]
 a='            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.beforeEncode(jpgPath, bitmap, captureResult);'
 s=replace(s,a,'            M9RenderCrash1D.stage("pre_encode_trace");\n'+a)
 s=replace(s,'            long jpegStartedNs = System.nanoTime();','            M9RenderCrash1D.stage("jpeg_encode_write");\n            long jpegStartedNs = System.nanoTime();')
 s=replace(s,'            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.payloadWritten(jpgPath);','            M9RenderCrash1D.stage("jpeg_payload_written");\n            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.payloadWritten(jpgPath);')
 a='            return new Result(true, jpgPath, SAVE_PARITY_PNG ? pngPath : null, null, diag, exif);'
 s=replace(s,a,'            M9RenderCrash1D.stage("render_complete");\n'+a)
 a='''        } catch (Throwable t) {
            if (bitmap != null && !bitmap.isRecycled()) bitmap.recycle();'''
 s=replace(s,a,a.replace('            if (bitmap','            M9RenderCrash1D.failure(t);\n            if (bitmap'))
 a='''            return new Result(false, jpgPath, pngPath, t.toString(), failureDiag, null);
        }'''
 s=replace(s,a,a+' finally { M9RenderCrash1D.end(); }')
 s=replace(s,'                d.put("colourTrial1C", colourTrial1CJson);','''                colourTrial1CJson.put("memoryRevision", "M9COLOURTRIAL1D");
                colourTrial1CJson.put("amazeDestinationBandRows", 256);
                colourTrial1CJson.put("chromaPreparationInPlace", true);
                d.put("colourTrial1C", colourTrial1CJson);''')
 return s

def verify(root):
 p=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text());now=inventory(root)
 assert now==p['after'],'source drift'
 assert {k for k in p['before'] if now[k]!=p['before'][k]}==CHANGED
 assert set(now)-set(p['before'])=={CRASH}
 for f in ['reconstruct.cpp','native.inc']:assert (root/(CPP+f)).read_bytes()==(HERE/f).read_bytes()
 for f in ['M9ColourTrial1C.java','M9RenderCrash1D.java']:assert (root/(BASE+'m9/render/'+f)).read_bytes()==(HERE/f).read_bytes()
 assert all(now[k]==v for k,v in p['before'].items() if k not in CHANGED)
 return {'revision':ID,'changed':sorted(CHANGED),'added':[CRASH],'photographic_kernels_and_assets_unchanged':True,'version':'1.66-m9colourtrial1d-tg1','code':26686,'crash_cause_not_yet_proven':True,'device_validation_pending':True}
def main(root):
 receipt=root/(ID+'_SOURCE_PROOF.json')
 if receipt.exists():print(json.dumps(verify(root),indent=2));return
 parent_verify(root);before=inventory(root)
 r=transform((root/RENDERER).read_text())
 a=replace((root/APP).read_text(),'        sPhotonCamera = this;','        sPhotonCamera = this;\n        com.particlesdevs.photoncamera.m9.render.M9RenderCrash1D.install(this);')
 l=replace((root/LOG).read_text(),'            logContext = context.getApplicationContext();','            logContext = context.getApplicationContext();\n            com.particlesdevs.photoncamera.m9.render.M9RenderCrash1D.storageReady();')
 g=replace((root/'app/build.gradle').read_text(),'versionCode 26685','versionCode 26686');g=replace(g,"versionName '1.65-m9colourtrial1c-tg1'","versionName '1.66-m9colourtrial1d-tg1'")
 for path,body in [(RENDERER,r),(APP,a),(LOG,l),('app/build.gradle',g)]: (root/path).write_text(body)
 for f in ['reconstruct.cpp','native.inc']:shutil.copyfile(HERE/f,root/(CPP+f))
 for f in ['M9ColourTrial1C.java','M9RenderCrash1D.java']:shutil.copyfile(HERE/f,root/(BASE+'m9/render/'+f))
 receipt.write_text(json.dumps({'revision':ID,'before':before,'after':inventory(root)},indent=2)+'\n')
 print(json.dumps(verify(root),indent=2))
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
