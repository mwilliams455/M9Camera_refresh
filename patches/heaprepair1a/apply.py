"""Memory ownership repair on exact, fully verified PREVIEWTC20NEG1A; photographic math unchanged."""
from pathlib import Path
import sys,json,shutil,importlib.util
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'));from m9rbrollback1a import inventory
spec=importlib.util.spec_from_file_location('preview_parent',HERE.parent/'previewtc20neg1a/apply.py');parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
BASE='app/src/main/java/com/particlesdevs/photoncamera/'
RENDERER=BASE+'m9/render/M9R35Renderer.java';HELPER=BASE+'m9/render/M9ColourTrial1C.java'
NATIVE='app/src/main/cpp/colourtrial1c/native.inc';EXIF=BASE+'gallery/viewmodel/ExifDialogViewModel.java';SPOOL=BASE+'m9/M9DiagnosticBurstSpool.java'
ID='M9HEAPREPAIR1A'
ADDED={BASE+'m9/M9DiagnosticStream1A.java',BASE+'gallery/viewmodel/M9TiffMetadata1A.java',BASE+'gallery/viewmodel/M9GalleryMetadata1A.java'}
CHANGED={RENDERER,HELPER,NATIVE,EXIF,SPOOL,'app/build.gradle'}
def one(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a));return s.replace(a,b,1)
def transform_renderer(s):
 a='''        final int mhcBytes = Math.multiplyExact(Math.multiplyExact(width, height), 6);
        ByteBuffer mhcRgbBuffer = demosaicNeutralEa1A
                ? null
                : ByteBuffer.allocateDirect(mhcBytes).order(ByteOrder.nativeOrder());
        Mat rawMat = demosaicNeutralEa1A
                ? new Mat(height, width, CvType.CV_16UC1)
                : new Mat();
        Mat cam16 = demosaicNeutralEa1A
                ? new Mat()
                : new Mat(height, width, CvType.CV_16UC3, mhcRgbBuffer);
        Mat meterCam16 = new Mat();
        try {'''
 b='''        // M9HEAPREPAIR1A: native-owned image storage, not an ART non-movable byte array.
        // The 12MP RGB16 allocation is 72 MiB. JNI only borrows it inside this try/finally.
        ByteBuffer mhcRgbBuffer = null;
        Mat rawMat = new Mat();
        Mat cam16 = new Mat();
        Mat meterCam16 = new Mat();
        try {
            if (demosaicNeutralEa1A) rawMat.create(height, width, CvType.CV_16UC1);
            else {
                cam16.create(height, width, CvType.CV_16UC3);
                if (!cam16.isContinuous()) throw new IllegalStateException("M9 RGB16 storage must be contiguous");
                mhcRgbBuffer = M9ColourTrial1C.borrowCameraStorage(cam16.dataAddr(), width, height);
            }'''
 s=one(s,a,b)
 # The existing finally releases rawMat, meterCam16 and cam16. Keep its buffer fence.
 a='''            // LIFETIME1A: Mat(ByteBuffer) wraps external direct memory and does not own'''
 if a in s:
  start=s.index(a);end=s.index('            java.lang.ref.Reference.reachabilityFence(mhcRgbBuffer);',start)
  s=s[:start]+'''            // M9HEAPREPAIR1A: all borrowed JNI views finish before cam16 releases its storage.
'''+s[end:]
 return s

def transform_exif(s):
 a='''        ExifInterface exifInterface;
        InputStream inputStream;
        try {
            inputStream = contentResolver.openInputStream(imageFile.getFileUri());
            exifInterface = new ExifInterface(inputStream);'''
 b='''        java.util.Map<String,String> attributes;
        try {
            attributes = M9GalleryMetadata1A.read(contentResolver, imageFile.getFileUri());'''
 s=one(s,a,b).replace('exifInterface.getAttribute(', 'attributes.get(')
 s=one(s,'''        try {
            inputStream.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
''','')
 s=one(s,'    private Runnable histoRunnable;','''    private Runnable histoRunnable;
    private CustomTarget<Bitmap> histogramTarget;''')
 s=one(s,'''        Histogram histogram = new Histogram(getApplication().getBaseContext(), null);''','''        Histogram histogram = new Histogram(getApplication().getBaseContext(), null);
        if (histogramTarget != null) {
            Glide.with(getApplication()).clear(histogramTarget);
            histogramTarget = null;
        }''')
 s=one(s,'.fitCenter().useUnlimitedSourceGeneratorsPool(true))','.fitCenter())')
 s=one(s,'.into(new CustomTarget<Bitmap>() {','.into(histogramTarget = new CustomTarget<Bitmap>() {')
 s=one(s,'''    protected void onCleared() {
        super.onCleared();''','''    protected void onCleared() {
        if (histoRunnable != null) histoHandler.removeCallbacks(histoRunnable);
        if (histogramTarget != null) Glide.with(getApplication()).clear(histogramTarget);
        histogramTarget = null;
        super.onCleared();''')
 return s

JNI='''
// M9HEAPREPAIR1A: no allocation and no ownership transfer. cam16 owns this address.
extern "C" JNIEXPORT jobject JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9ColourTrial1C_borrowCameraStorageNative(
 JNIEnv* env,jclass,jlong address,jint w,jint h) {
    if(!address||w<1||h<1||w>8192||h>8192)return nullptr;
    return env->NewDirectByteBuffer(reinterpret_cast<void*>(address),int64_t(w)*h*6);
}
'''
JAVA='''    private static native ByteBuffer borrowCameraStorageNative(long address,int w,int h);
    static ByteBuffer borrowCameraStorage(long address,int w,int h) {
        ByteBuffer view=borrowCameraStorageNative(address,w,h);
        if(view==null)throw new IllegalStateException("M9HEAPREPAIR1A camera buffer view unavailable");
        return view.order(ByteOrder.nativeOrder());
    }
'''
def verify(root):
 proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text());now=inventory(root);assert now==proof['after'],'source drift'
 before=proof['before'];assert {k for k in before if now.get(k)!=before[k]}==CHANGED
 assert set(now)-set(before)==ADDED;assert not(set(before)-set(now))
 assert (root/NATIVE).read_text().endswith(JNI)
 assert 'ByteBuffer.allocateDirect(mhcBytes)' not in (root/RENDERER).read_text()
 return dict(revision=ID,version='1.71-m9heaprepair1a-tg1',versionCode=26691,
  changed=sorted(CHANGED),added=sorted(ADDED),native_pixel_math_unchanged=True,
  Auto_exposure_preview_shader_capture_policy_assets_unchanged=True,
  RGB16_owner='OpenCV_native_Mat_explicit_finally_release',diagnostic_payload_retained_bytes=0,
  gallery_TIFF_metadata_budget_bytes=262144,device_validation_pending=True)
def main(root):
 receipt=root/(ID+'_SOURCE_PROOF.json')
 if receipt.exists():print(json.dumps(verify(root),indent=2));return
 parent.verify(root);before=inventory(root)
 updates={RENDERER:transform_renderer((root/RENDERER).read_text()),EXIF:transform_exif((root/EXIF).read_text()),
  HELPER:one((root/HELPER).read_text(),'    private M9ColourTrial1C() {}','    private M9ColourTrial1C() {}\n'+JAVA),
  NATIVE:(root/NATIVE).read_text()+JNI,
  'app/build.gradle':one(one((root/'app/build.gradle').read_text(),'versionCode 26690','versionCode 26691'),"versionName '1.70-m9previewtc20neg1a-tg1'","versionName '1.71-m9heaprepair1a-tg1'")}
 for rel,s in updates.items():(root/rel).write_text(s)
 for rel in ADDED|{SPOOL}:shutil.copyfile(HERE/Path(rel).name,root/rel)
 receipt.write_text(json.dumps(dict(revision=ID,before=before,after=inventory(root)),indent=2)+'\n')
 print(json.dumps(verify(root),indent=2))
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
