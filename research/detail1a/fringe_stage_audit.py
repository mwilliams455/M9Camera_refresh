"""Trace the exact SAT2/curve/4:2:2 path and coherent-green research controls.

No diagnostic mode is switched: the live context stays on SAT2 (mode9).
The independent RGB controls are not recovered Leica demosaicing routines.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import distance_transform_cdt
from native import Native
from rb_domain import DomainProbe
from detail1h import dng_inputs,TiledDetail
from downstream import Downstream
from demosaic_control import Control
from coherent_green_probe import variants
from fringe_replay import pink_mask

TRACE_CPP=r'''
extern "C" void curve_frame(void* q,const uint16_t* cam,int count,double gain,uint8_t* out){
 auto& ctx=*static_cast<ColorContext*>(q);
 std::vector<std::thread> threads;
 for(int t=0;t<8;t++)threads.emplace_back([&,t](){
  for(int p=count*t/8;p<count*(t+1)/8;p++){
   double h[3],m[3];int rgb[3];cameraToM9(reinterpret_cast<const jshort*>(cam),3*p,ctx,h,m);
   m9CurvePixel(m,gain,ctx,rgb);for(int k=0;k<3;k++)out[3*p+k]=rgb[k];
  }
 });
 for(auto& t:threads)t.join();
}
extern "C" void point_trace(void* q,const uint16_t* cam,int count,double gain,double* out){
 auto& ctx=*static_cast<ColorContext*>(q);
 for(int p=0;p<count;p++){
  double h[3],m[3];int rgb[3];cameraToM9(reinterpret_cast<const jshort*>(cam),3*p,ctx,h,m);
  m9CurvePixel(m,gain,ctx,rgb);
  for(int k=0;k<3;k++){
   double raw=cam[3*p+k]/65535.;out[p*18+k]=raw/ctx.cw[k];
   out[p*18+3+k]=std::min(raw,ctx.cw[k])/ctx.cw[k];
   out[p*18+6+k]=h[k];out[p*18+9+k]=m[k];
   out[p*18+12+k]=std::min(m[k]*gain,1.);out[p*18+15+k]=rgb[k]/255.;
  }
 }
}
'''


class Trace:
    def __init__(self,colour,out):
        self.colour=colour
        cpp=out/'trace.cpp';cpp.write_text((colour.build/'colour.cpp').read_text()+TRACE_CPP)
        so=out/'trace.so'
        subprocess.run(['g++','-std=c++17','-O2','-fno-fast-math','-shared','-fPIC','-pthread',str(cpp),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so))
        self.lib.curve_frame.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_double,C.c_void_p]
        self.lib.point_trace.argtypes=self.lib.curve_frame.argtypes
        self.lib.curve_frame.restype=None;self.lib.point_trace.restype=None

    def frame(self,cam,gain):
        out=np.empty(cam.shape,np.uint8)
        self.lib.curve_frame(self.colour.q,cam.ctypes.data,cam.shape[0]*cam.shape[1],gain,out.ctypes.data)
        return out

    def points(self,cam,gain):
        cam=np.ascontiguousarray(cam);out=np.empty((len(cam),18),float)
        self.lib.point_trace(self.colour.q,cam.ctypes.data,len(cam),gain,out.ctypes.data)
        return out


def verify_pairs(curve,final,cb_gain,cr_gain):
    """Independent vectorized replay of the retained BT.601/TG1 pair arithmetic."""
    assert curve.shape[1]%2==0
    for y in range(0,len(curve),64):
        z=curve[y:y+64].astype(np.int64);s=z[:,0::2]+z[:,1::2]
        rs,gs,bs=[s[...,k] for k in range(3)]
        cb=(((-2765*rs+1)>>1)-((5427*gs)>>1)+((8192*bs)>>1))>>14
        cr=(((8192*rs)>>1)-((6860*gs)>>1)-((1332*bs)>>1))>>14
        cb=((cb+128)&255)-128;cr=((cr+128)&255)-128
        cb=np.where(cb<0,cb*cb_gain,cb);cr=np.where(cr<0,cr*cr_gain,cr)
        cb=np.repeat(cb,2,axis=1);cr=np.repeat(cr,2,axis=1)
        yy=(4899*z[...,0]+9617*z[...,1]+1868*z[...,2])>>14
        values=np.stack((yy+1.402*cr,yy-.344136*cb-.714136*cr,yy+1.772*cb),axis=-1)
        decoded=(np.clip(values/255,0,1)*255+.5).astype(np.uint8)
        assert np.array_equal(decoded,final[y:y+64])
    return int(final.size)


def comparison(out,photos):
    sheet=Image.new('RGB',(1224,1452),'#16191c');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    draw.text((12,12),'Coherent RGB control — same RAW, source colour, SAT2, tone curve and exposure',font=font,fill='white')
    draw.text((12,43),'Right: green reconstruction changes; original native Sharp correction retained. Research only.',font=small,fill='#ffc986')
    for col,(mode,title) in enumerate([('H','Current DETAIL1H'),('fixed_green','Previous fixed-green control'),('coherent_native_detail','Coherent RGB + native detail')]):
        draw.text((12+408*col,89),title,font=font,fill='white');rot=np.rot90(photos[mode],3)
        for row,(x,y) in enumerate([(1765,1908),(257,1345),(1447,1140)]):
            top=153+432*row;draw.text((12+408*col,top-25),f'384 px crop at ({x}, {y})',font=small,fill='#c2c8ce')
            sheet.paste(Image.fromarray(rot[y:y+384,x:x+384]),(12+408*col,top))
    sheet.save(out/'Coherent-green-comparison.png')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--assembled',type=Path,required=True)
    ap.add_argument('--header',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);repo=Path(__file__).resolve().parents[2]
    fixture=json.loads((Path(__file__).parent/'results/fringe_164710_capture.json').read_text())
    assert hashlib.sha256(a.raw.read_bytes()).hexdigest()==fixture['dng_sha256']
    norm,meta,_,sensor,gains=dng_inputs(a.raw);nr,_,nb=meta['neutral'];cfa=meta['cfa'];scale=meta['representation_scale']
    native=Native(repo,a.assembled,a.header,a.out/'native');probe=DomainProbe(a.out/'native');control=Control(a.out/'temporary')
    base=native.render(norm,nr,nb,cfa,candidate=False)
    hcam,hstats=TiledDetail(a.out/'native').apply(norm,sensor,base,cfa,nr,nb,meta['black'],meta['white'],fixture['detail1H']['rgbProfile'],gains,scale,guard=True)
    fields=dict(tiles='tiles',supported_rb_samples='supportedRbSamples',changed_carrier_samples='changedCarrierSamples',
        max_abs_correction='maxAbsCorrection',censored_samples='rawCensoredSamples',mean_confidence='meanConfidence',
        mean_residual_variance14='meanResidualVariance14',scratch_budget_bytes='scratchBudgetBytes')
    assert all(hstats[k]==fixture['detail1H'][v] for k,v in fields.items())
    colour=Downstream(repo,a.assembled,a.out/'colour');context=colour.configure(a.raw);trace=Trace(colour,a.out/'colour')
    far=distance_transform_cdt(sensor<meta['white'],metric='chessboard')>=8
    border=np.ones(norm.shape,bool);border[10:-10,10:-10]=False
    reports={};photos={};gain=fixture['actual_render_gain']
    def render(mode,cam):
        assert np.array_equal(cam[border],hcam[border]) and np.array_equal(cam[far],hcam[far])
        if mode=='fixed_green':assert np.array_equal(cam[...,1],hcam[...,1])
        restored=colour.restore(cam,scale);final=colour.render(restored,gain);before=trace.frame(restored,gain)
        checked=verify_pairs(before,final,colour.cb,colour.cr)
        pm=pink_mask(final);pm0=pink_mask(before);points=trace.points(restored[pm],gain)
        assert np.array_equal(np.rint(points[:,15:]*255).astype(np.uint8),before[pm])
        row=dict(final_pink=int(pm.sum()),curve_pink=int(pm0.sum()),both=int((pm&pm0).sum()),
            introduced_after_curve=int((pm&~pm0).sum()),removed_after_curve=int((~pm&pm0).sum()),
            native_green_changed_pixels=int(np.count_nonzero(cam[...,1]!=hcam[...,1])),
            border10_exact=True,H_exact_at_distance8_or_more=True,pair_decoder_rgb_samples_exact=checked,stages={})
        for k,name in enumerate(['camera_WB','camera_WB_capped','PP','M9','M9_gain_limit','curve']):
            z=points[:,3*k:3*k+3];d=np.minimum(z[:,0],z[:,2])-z[:,1]
            row['stages'][name]=dict(positive_fraction=float((d>0).mean()),above_002_fraction=float((d>.02).mean()),
                                   median=float(np.median(d)),p95=float(np.quantile(d,.95)))
        reports[mode]=row;photos[mode]=final
        Image.fromarray(np.rot90(final,3)).save(a.out/(mode+'.jpg'),quality=95,subsampling=2)
        print(mode,json.dumps({k:v for k,v in row.items() if k!='stages'}),flush=True)
    render('H',hcam)
    for mode,cam in variants(native,probe,control,norm,hcam,sensor,cfa,meta['neutral'],meta['white']):render(mode,cam)
    comparison(a.out,photos)
    result=dict(schema='m9.fringe_stage_audit.v1',raw_sha256=fixture['dng_sha256'],H_stats=hstats,H_phone_statistics_exact=len(fields),
        spatial_source_hashes=native.source_hashes,colour_source_hashes=colour.hashes,actual_render_gain=gain,
        context=context,variants=reports,stage_condition='Each stage statistic selects final pink-mask pixels for that same variant. Stage channel bases differ, so these are not common-unit error scores. M9_gain_limit is a float pre-rounding diagnostic. No per-stage hue correction is applied.',
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        coherent_script_sha256=hashlib.sha256(Path(__file__).with_name('coherent_green_probe.py').read_bytes()).hexdigest(),
        scope='Same-RAW offline controls only; coherent modes change green. No diagnostic context switch, SAT2 throughout. No new noise calibration, APK or accepted correction.',
        accepted=False,android_implementation_changed=False,auto_exposure_changed=False)
    (a.out/'report.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
