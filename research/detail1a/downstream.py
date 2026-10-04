"""Host replay of the frozen GL2G downstream colour and metering kernels.

Java numerical methods and the C++ pixel kernel are extracted, not translated.
Only Camera2/JNI plumbing is replaced. DNG metadata and host OpenCV/JPEG remain
explicit offline boundaries; this is not Android capture/encoding parity.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import struct
import subprocess
import numpy as np
import cv2
import tifffile
from native import function, PREAMBLE
from inputs import rational

CONVERTER_SHA = 'b1e0cd5262022991edcf164ae44412c1348129a53157245debe18745ab917245'

JAVA_STUBS = r'''
static class Rational {
    int n,d; Rational(int n,int d){this.n=n;this.d=d;}
    float floatValue(){return (float)n/(float)d;}
}
static class ColorSpaceTransform {
    Rational[] a; ColorSpaceTransform(Rational[] a){this.a=a;}
    void copyElements(Rational[] b,int offset){System.arraycopy(a,0,b,offset,9);}
}
static class Key<T>{}
static class CameraCharacteristics {
    static Key<Integer> SENSOR_REFERENCE_ILLUMINANT1=new Key<>();
    static Key<Byte> SENSOR_REFERENCE_ILLUMINANT2=new Key<>();
    static Key<ColorSpaceTransform> SENSOR_CALIBRATION_TRANSFORM1=new Key<>(),
        SENSOR_CALIBRATION_TRANSFORM2=new Key<>(), SENSOR_COLOR_TRANSFORM1=new Key<>(),
        SENSOR_COLOR_TRANSFORM2=new Key<>(), SENSOR_FORWARD_MATRIX1=new Key<>(),
        SENSOR_FORWARD_MATRIX2=new Key<>();
    Map<Key<?>,Object> m=new HashMap<>();
    <T> void put(Key<T> k,T v){m.put(k,v);}
    @SuppressWarnings("unchecked") <T> T get(Key<T> k){return (T)m.get(k);}
}
static class CaptureResult {
    static Key<Rational[]> SENSOR_NEUTRAL_COLOR_POINT=new Key<>(); Rational[] a;
    @SuppressWarnings("unchecked") <T> T get(Key<T> k){return (T)a;}
}
static class Log {static void d(String t,String m){} static void w(String t,String m){}}
static Rational[] readR(DataInputStream in,int n)throws Exception {
    Rational[] a=new Rational[n];for(int i=0;i<n;i++)a[i]=new Rational(in.readInt(),in.readInt());return a;
}
static void write(DataOutputStream out,double[] a)throws Exception {for(double v:a)out.writeDouble(v);}
'''

JAVA_MAIN = r'''
public static void main(String[] args)throws Exception {
    DataInputStream in=new DataInputStream(System.in);
    DataOutputStream out=new DataOutputStream(System.out);
    if(args[0].equals("context")) {
        CameraCharacteristics c=new CameraCharacteristics();
        c.put(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1,in.readInt());
        c.put(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT2,(byte)in.readInt());
        c.put(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1,new ColorSpaceTransform(readR(in,9)));
        c.put(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2,new ColorSpaceTransform(readR(in,9)));
        c.put(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1,new ColorSpaceTransform(readR(in,9)));
        c.put(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2,new ColorSpaceTransform(readR(in,9)));
        c.put(CameraCharacteristics.SENSOR_FORWARD_MATRIX1,new ColorSpaceTransform(readR(in,9)));
        c.put(CameraCharacteristics.SENSOR_FORWARD_MATRIX2,new ColorSpaceTransform(readR(in,9)));
        CaptureResult r=new CaptureResult();r.a=readR(in,3);
        NativeProspectiveSource s=buildNativeProspectiveSource(c,r);ColorContext q=s.ctx;
        write(out,q.cw);write(out,q.camToPp);write(out,q.ppToM9);
        write(out,q.adapt50To65);write(out,PP_TO_XYZ);write(out,XYZ2SRGB);
        write(out,new double[]{s.interpolationFactor,q.cct,q.wA,s.sceneX,s.sceneY,
            1.0-TG_NEG_CB_COMPRESSION*tungstenGuardWeight(q.cct),
            1.0-TG_NEG_CR_COMPRESSION*tungstenGuardWeight(q.cct)});
        write(out,nativeProspectiveDouble(s.sensorToXyzD50));
    } else if(args[0].equals("tail")) {
        int wl=in.readInt();float[] black=new float[4];for(int i=0;i<4;i++)black[i]=in.readFloat();
        long total=in.readLong(),clipped=in.readLong();long[][] counts=new long[4][wl];
        for(int p=0;p<4;p++)for(int i=0;i<wl;i++)counts[p][i]=in.readLong();
        RawTail t=rawTail(counts,black,wl,total,clipped);
        write(out,new double[]{t.tailValue,t.clipFraction,t.uq25,t.uq50,t.uq99,t.uq995,
            t.uq998,t.q,t.adaptiveUq,t.curvature,t.isolated?1:0});
    } else if(args[0].equals("gain")) {
        double[] stats=new double[13];for(int i=0;i<3;i++)stats[i]=in.readDouble();
        RawTail tail=new RawTail();tail.tailValue=in.readDouble();
        Meter meter=tc20MeterFromNativeStats(stats,tail);
        boolean meterParitySelfMeter=true;
        double meterParityRenderBaseGain=meter.gain;
        // The exact GL2G tone-bound block is inserted here. Neutral exposure intent,
        // zero edge-placement EV and disabled shaded guard are explicit replay inputs.
        /*TONE_BLOCK*/
        write(out,new double[]{meter.median,meter.p98,meter.validCount,meter.baseGain,
            meter.guardGain,meter.gain,toneBoundOriginalTc20Ev1A,
            toneBoundAppliedTc20Ev1A,effectiveRenderGain});
    } else if(args[0].equals("weights")) {
        int meterW=in.readInt(),meterH=in.readInt();
        /*WEIGHT_BLOCK*/
        write(out,rowW);write(out,colW);
    } else throw new IllegalArgumentException(args[0]);
    out.flush();
}
'''

CPP_WRAPPER = r'''
extern "C" void* context(const double* a,const uint8_t* curve) {
    auto* q=new ColorContext();int p=0;
    for(auto* v:{&q->cw})for(double& x:*v)x=a[p++];
    for(auto* v:{&q->camToPp,&q->ppToM9,&q->adapt50To65,&q->ppToXyz,&q->xyz2Srgb})
        for(double& x:*v)x=a[p++];
    q->hsm={0,1,1,0,1,1,0,1,1,0,1,1};q->hueDivisions=2;q->satDivisions=2;
    q->skyChromaMode1A=9;std::copy(curve,curve+2048,q->curve.begin());return q;
}
extern "C" void destroy(void* q){delete static_cast<ColorContext*>(q);}
extern "C" void meter(void* q,const jshort* a,int w,int h,const double* rw,const double* cw,double* stats) {
    int64_t timing[8]{};meterTc20WeightedSelectScalar(*static_cast<ColorContext*>(q),a,w*h,w,h,rw,cw,stats,timing);
}
extern "C" void render(void* q,const jshort* a,int w,int h,jint* out,double gain,double cb,double cr,int workers) {
    std::vector<std::thread> threads;workers=std::min(workers,h);
    for(int t=0;t<workers;t++){
        int y0=h*t/workers,y1=h*(t+1)/workers;
        threads.emplace_back([=](){int64_t stats[3]{};
            renderStripScalar(*static_cast<ColorContext*>(q),a+y0*w*3,(y1-y0)*w,w,out+y0*w,gain,cb,cr,stats);});
    }
    for(auto& t:threads)t.join();
}
'''

class Downstream:
    def __init__(self, repo, assembled, build):
        self.build=build.resolve();self.build.mkdir(parents=True,exist_ok=True)
        manifest=json.loads((repo/'patches/m9cam-m9livegl2g-manifest.json').read_text())
        native=assembled/'app/src/main/cpp/m9color_jni.cpp'
        renderer=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
        curve=assembled/'app/src/main/assets/m9/m9_curve02_firmware.bin'
        converter=assembled/'app/src/main/java/com/particlesdevs/photoncamera/processing/render/Converter.java'
        self.hashes={}
        for p in [native,renderer,curve,converter]:
            rel=str(p.relative_to(assembled));h=hashlib.sha256(p.read_bytes()).hexdigest()
            assert h==(CONVERTER_SHA if p==converter else manifest['frozen'][rel]),rel
            self.hashes[rel]=h
        j=renderer.read_text();c=converter.read_text();s=native.read_text()
        # Keep all Converter math unchanged. Replace only Android imports, logging,
        # transform accessor (unused by this path) and illuminant lookup plumbing.
        c=c[c.index('    public static void calculateCameraToXYZD50Transform'):]
        c=c[:c.rfind('}')]
        c=c.replace(function(c,'    public static void convertColorspaceTransform'),'')
        converter_header='''static class Converter {
static final float[] D50_XYZ={0.9642f,1,0.8249f};
static final String TAG="Converter";static final boolean DEBUG=false;
static final int NO_ILLUMINANT=-1;
static class Illuminants {int get(int i,int d){return i==21?6504:i==17?2856:d;}}
static final Illuminants sStandardIlluminates=new Illuminants();
'''
        constants=j[j.index('    private static final double METER_TARGET'):j.index('    // TARGETINPUTADAPTER1A:')]
        # UNIT16 is unused by extracted native path, and references an unrelated helper.
        constants=constants.replace('private static final double[] UNIT16 = buildUnit16();','')
        markers=[
            'private static final class ColorContext','private static final class NativeProspectiveSource',
            'private static NativeProspectiveSource buildNativeProspectiveSource',
            'private static float[] nativeProspectiveTransform','private static boolean nativeProspectiveValid3x3',
            'private static double[] nativeProspectiveDouble','private static final class TailBin',
            'private static final class RawTail','private static RawTail rawTail',
            'private static double quantileBins','private static double valueAtRank',
            'private static final class Meter','private static Meter tc20MeterFromNativeStats',
            'private static double tungstenGuardWeight','private static double toneLog2Positive1A',
            'private static double[] normalizedPpToXyz','private static double cctFromXy',
            'private static double weightA','private static double[] xyToXyz','private static double[] bradford',
            'private static double[] interp9','private static double[] matMul3','private static double[] matVec3',
            'private static double[] inverse3','private static double clamp(double']
        # Select the unique tone block in the renderer; no numerical edits.
        start=j.index('            final double toneBoundLimitEv1A = 0.5;',j.index('final double meterParityRenderBaseGain'))
        end=j.index('\n\n',j.index('final double effectiveRenderGain =',start))
        tone=j[start:end]
        start=j.index('                double[] rowW = new double[meterH];',j.index('final boolean meterParitySelfMeter'))
        end=j.index('                meterWeightElapsedMs =',start)
        weights=j[start:end]
        main=JAVA_MAIN.replace('/*TONE_BLOCK*/',tone).replace('/*WEIGHT_BLOCK*/',weights)
        code='import java.util.*;import java.io.*;\npublic class Replay {\n'+JAVA_STUBS+constants+converter_header+c+'}\n'+'\n'.join(function(j,m) for m in markers)+main+'}\n'
        jp=self.build/'Replay.java';jp.write_text(code)
        subprocess.run(['java','com.sun.tools.javac.Main','-d',str(self.build),str(jp)],check=True,capture_output=True)
        cp=self.build/'colour.cpp';cp.write_text(PREAMBLE+s[s.index('constexpr int RAW_MAX'):s.index('// NORMNATIVE1A:')]+CPP_WRAPPER)
        so=self.build/'colour.so'
        subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-fPIC','-shared','-pthread',str(cp),'-o',str(so)],check=True,capture_output=True)
        self.lib=C.CDLL(str(so));self.curve=np.frombuffer(curve.read_bytes(),np.uint8).copy()
        self.lib.context.argtypes=[C.c_void_p,C.c_void_p];self.lib.context.restype=C.c_void_p
        self.lib.destroy.argtypes=[C.c_void_p]
        self.lib.meter.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_void_p,C.c_void_p]
        self.lib.render.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_double,C.c_double,C.c_double,C.c_int]
        self.q=None;self.weights={}

    def java(self,mode,data):
        r=subprocess.run(['java','-cp',str(self.build),'Replay',mode],input=data,check=True,capture_output=True)
        return np.frombuffer(r.stdout,'>f8').astype(np.float64)

    def configure(self,path):
        with tifffile.TiffFile(path) as tf:
            t=tf.pages[0].tags;ref=[int(t[k].value) for k in ['CalibrationIlluminant1','CalibrationIlluminant2']]
            assert set(ref)=={21,17},'Replay illuminants are restricted to D65/Standard A'
            data=struct.pack('>2i',*ref)
            for name in ['CameraCalibration1','CameraCalibration2','ColorMatrix1','ColorMatrix2','ForwardMatrix1','ForwardMatrix2','AsShotNeutral']:
                assert t[name].dtype in (5,10)
                data+=struct.pack('>'+str(len(t[name].value))+'i',*t[name].value)
        a=self.java('context',data);assert a.size==64 and np.all(np.isfinite(a))
        if self.q:self.lib.destroy(self.q)
        ctx=np.ascontiguousarray(a[:48]);self.q=self.lib.context(ctx.ctypes.data,self.curve.ctypes.data)
        self.cb,self.cr=map(float,a[53:55])
        return dict(cw=a[:3].tolist(),cam_to_pp=a[3:12].tolist(),pp_to_m9=a[12:21].tolist(),
                    adapt50_to65=a[21:30].tolist(),pp_to_xyz=a[30:39].tolist(),xyz_to_srgb=a[39:48].tolist(),
                    interpolation_factor=float(a[48]),cct=float(a[49]),weight_a=float(a[50]),
                    scene_xy=a[51:53].tolist(),tg_cb=self.cb,tg_cr=self.cr,sensor_to_xyz_d50=a[55:].tolist())

    def tail(self,path):
        with tifffile.TiffFile(path) as tf:
            p=tf.pages[0];raw=p.asarray();t=p.tags;wl=int(rational(t['WhiteLevel'])[0]);bl=rational(t['BlackLevel'])
            hist=np.stack([np.bincount(raw[y::2,x::2].ravel(),minlength=65536)[:wl] for y,x in [(0,0),(0,1),(1,0),(1,1)]])
            data=struct.pack('>i4f2q',wl,*bl,raw.size,int(np.count_nonzero(raw>=wl)))+hist.astype('>i8').tobytes()
        a=self.java('tail',data)
        return dict(zip(['tail_value','clip_fraction','uq25','uq50','uq99','uq995','uq998','q','adaptive_uq','curvature','isolated'],map(float,a)))

    def meter(self,cam,tail):
        h,w=cam.shape[:2];scale=min(1.,1600/max(h,w));mw,mh=round(w*scale),round(h*scale)
        sample=cv2.resize(cam,(mw,mh),interpolation=cv2.INTER_AREA) if scale<1 else cam.copy()
        if (mw,mh) not in self.weights:
            self.weights[mw,mh]=self.java('weights',struct.pack('>2i',mw,mh))
        weights=self.weights[mw,mh];rw=np.ascontiguousarray(weights[:mh]);cw=np.ascontiguousarray(weights[mh:]);stats=np.zeros(3)
        self.lib.meter(self.q,sample.ctypes.data,mw,mh,rw.ctypes.data,cw.ctypes.data,stats.ctypes.data)
        a=self.java('gain',struct.pack('>4d',*stats,tail['tail_value']))
        return dict(zip(['median','p98','valid_count','base_gain','guard_gain','tc20_gain','tc20_ev','bounded_ev','render_gain'],map(float,a)))

    def render(self,cam,gain,workers=8):
        cam=np.ascontiguousarray(cam);h,w=cam.shape[:2];argb=np.empty((h,w),np.uint32)
        self.lib.render(self.q,cam.ctypes.data,w,h,argb.ctypes.data,gain,self.cb,self.cr,workers)
        return np.stack([(argb>>16)&255,(argb>>8)&255,argb&255],axis=-1).astype(np.uint8)

    @staticmethod
    def restore(cam,scale):
        # CV_16UC3 convertTo uses saturation and nearest-integer rounding. This
        # OpenCV operation keeps the same double scale and output depth.
        return cv2.addWeighted(cam,scale,cam,0.,0.)
