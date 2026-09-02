#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, struct
from pathlib import Path
import numpy as np
import cv2
import tifffile
from PIL import Image, ImageDraw

METER_TARGET = 0.107
METER_TARGET_RENORM = METER_TARGET * (8192.0 / 10000.0)
METER_ALLOW = 0.02
METER_CW = 0.75
RAW_MAX = 16383
LUT_MAX = 2047

# R3.8-H25/TG1 candidate. R3.6 CCT correction is retained.
# TG1 is appended after the exact M9/BT.601 stage and changes no upstream stage.
# The only intended colour-path change is the corrected McCamy CCT denominator:
#     n = (x - 0.3320) / (y - 0.1858)
# R3.5 accidentally used the opposite denominator sign, sending warm chromaticities
# toward high CCT and therefore toward the D65 side of dual-illuminant interpolation.
TC_HEADROOM_TARGET = 0.95
TC_ALPHA = 0.20
TC_TAIL_CURVATURE_THRESHOLD = 0.25
TG_START_K = 4500.0
TG_FULL_K = 3200.0
TG_NEG_CB_COMPRESSION = 0.25
TG_NEG_CR_COMPRESSION = 0.16

MATRIX_BANK = {
    2: (
        np.array([[13659,-4457,-1004],[-2244,13469,-3033],[-199,-6014,14398]],dtype=np.int64),
        np.array([[14811,-5604,-1004],[-2455,13688,-3033],[393,-6588,14398]],dtype=np.int64),
    ),
    3: (
        np.array([[16754,-7632,-922],[-3124,14774,-3458],[-567,-9579,18330]],dtype=np.int64),
        np.array([[18160,-9034,-922],[-3422,15080,-3458],[137,-10264,18330]],dtype=np.int64),
    ),
    4: (
        np.array([[19850,-10808,-840],[-4004,16080,-3884],[-936,-13144,22262]],dtype=np.int64),
        np.array([[21509,-12464,-840],[-4389,16473,-3884],[-117,-13940,22262]],dtype=np.int64),
    ),
}

M9_CM_A = np.array([[.8560,-.2034,-.0066],[-.4240,1.3600,.2920],[-.0740,.2470,.8980]],dtype=np.float64)
M9_CM_D65 = np.array([[.6260,-.1019,-.0470],[-.3730,1.1450,.1930],[-.1409,.2950,.6210]],dtype=np.float64)
D50_XY=np.array([.34567,.35850],dtype=np.float64)
D65_XY=np.array([.31271,.32902],dtype=np.float64)
BRADFORD=np.array([[.8951,.2664,-.1614],[-.7502,1.7135,.0367],[.0389,-.0685,1.0296]],dtype=np.float64)
BRADFORD_INV=np.linalg.inv(BRADFORD)
XYZ2SRGB=np.array([[3.2404542,-1.5371385,-.4985314],[-.9692660,1.8760108,.0415560],[.0556434,-.2040259,1.0572252]],dtype=np.float64)
PCS_XYZ=np.array([D50_XY[0]/D50_XY[1],1.0,(1-D50_XY.sum())/D50_XY[1]],dtype=np.float64)
PP_TO_XYZ_RAW=np.array([[.7977,.1352,.0313],[.2880,.7119,.0001],[0.,0.,.8249]],dtype=np.float64)
PP_TO_XYZ=np.diag(PCS_XYZ/(PP_TO_XYZ_RAW@np.ones(3)))@PP_TO_XYZ_RAW
XYZ_TO_PP=np.linalg.inv(PP_TO_XYZ)

HSM_H=0.25
HSM_S=0.85
HSM_V=1.00

def ratios(v):
    v=tuple(v);return np.array([v[i]/v[i+1] for i in range(0,len(v),2)],dtype=np.float64)

def tag_numeric(tag):
    """Decode TIFF numerics while preserving literal SHORT/LONG arrays."""
    if int(tag.dtype) in (5,10):  # TIFF RATIONAL / SRATIONAL
        return ratios(tag.value)
    return np.asarray(tag.value if isinstance(tag.value,(tuple,list)) else [tag.value],dtype=np.float64)

def tag_scalar(tag):
    v=tag_numeric(tag)
    if v.size != 1:raise ValueError(f'Expected scalar tag, got {v.size} values for {tag.name}')
    return float(v[0])
def xy_to_xyz(xy):
    x,y=xy;return np.array([x/y,1.,(1-x-y)/y],dtype=np.float64)
def bradford(src_xy,dst_xy):
    s=BRADFORD@xy_to_xyz(src_xy);d=BRADFORD@xy_to_xyz(dst_xy);return BRADFORD_INV@np.diag(d/s)@BRADFORD
def cct_from_xy(xy):
    x,y=xy;n=(x-.3320)/(y-.1858);return float(np.clip(-449*n**3+3525*n**2-6823.3*n+5520.33,2000,12000))
def weight_A(T):
    m=1e6/T;return float(np.clip((m-1e6/6500)/(1e6/2850-1e6/6500),0,1))
def tungsten_guard_weight(T):
    x=float(np.clip((TG_START_K-T)/(TG_START_K-TG_FULL_K),0,1))
    return x*x*(3-2*x)
def interp(A,D,wA):return wA*A+(1-wA)*D

class CobaltDCP:
    def __init__(self,path):
        with tifffile.TiffFile(path) as tf:
            t=tf.pages[0].tags
            self.CM_A=ratios(t['ColorMatrix1'].value).reshape(3,3);self.CM_D=ratios(t['ColorMatrix2'].value).reshape(3,3)
            self.FM_A=ratios(t['ForwardMatrix1'].value).reshape(3,3);self.FM_D=ratios(t['ForwardMatrix2'].value).reshape(3,3)
            self.hd,self.sd,self.vd=map(int,t['ProfileHueSatMapDims'].value)
            self.HSM_A=np.asarray(t['ProfileHueSatMapData1'].value,dtype=np.float64).reshape(self.vd,self.hd,self.sd,3)[0]
            self.HSM_D=np.asarray(t['ProfileHueSatMapData2'].value,dtype=np.float64).reshape(self.vd,self.hd,self.sd,3)[0]
        self.FM_A=self._normalize_fm(self.FM_A);self.FM_D=self._normalize_fm(self.FM_D)
    @staticmethod
    def _normalize_fm(M):return np.diag(PCS_XYZ/(M@np.ones(3)))@M
    def neutral_to_xy(self,neutral):
        xy=D50_XY.copy()
        for _ in range(30):
            wA=weight_A(cct_from_xy(xy));CM=interp(self.CM_A,self.CM_D,wA);xyz=np.linalg.solve(CM,neutral);xyz/=xyz.sum();q=xyz[:2]
            if np.abs(q-xy).sum()<1e-8:return q
            xy=q
        return xy
    @staticmethod
    def _rgb_to_hsv6(rgb):
        r,g,b=np.moveaxis(rgb,-1,0);v=np.maximum(r,np.maximum(g,b));mn=np.minimum(r,np.minimum(g,b));gap=v-mn
        h=np.zeros_like(v);s=np.zeros_like(v);m=gap>1e-12;mr=m&(r==v);mg=m&(~mr)&(g==v);mb=m&(~mr)&(~mg)
        h[mr]=(g[mr]-b[mr])/gap[mr];h[mr&(h<0)]+=6;h[mg]=2+(b[mg]-r[mg])/gap[mg];h[mb]=4+(r[mb]-g[mb])/gap[mb];s[m]=gap[m]/np.maximum(v[m],1e-12)
        return h,s,v
    @staticmethod
    def _hsv6_to_rgb(h,s,v):
        h=np.mod(h,6);i=np.floor(h).astype(np.int16);f=h-i;p=v*(1-s);q=v*(1-s*f);tt=v*(1-s*(1-f));r=np.empty_like(v);g=np.empty_like(v);b=np.empty_like(v)
        vals=[(v,tt,p),(q,v,p),(p,v,tt),(p,q,v),(tt,p,v),(v,p,q)]
        for n,(rr,gg,bb) in enumerate(vals):
            m=i==n;r[m]=rr[m];g[m]=gg[m];b[m]=bb[m]
        return np.stack([r,g,b],-1)
    def apply_hsm(self,pp,hsm):
        x=np.clip(pp,0,1);h,s,v=self._rgb_to_hsv6(x);hp=h*(self.hd/6.0);sp=s*(self.sd-1);h0=np.floor(hp).astype(np.int16);s0=np.minimum(np.floor(sp).astype(np.int16),self.sd-2);h1=h0+1
        wrap=h0>=self.hd-1;h0=np.where(wrap,self.hd-1,h0);h1=np.where(wrap,0,h1);hf=hp-h0;sf=sp-s0
        e00=hsm[h0,s0];e01=hsm[h1,s0];e10=hsm[h0,s0+1];e11=hsm[h1,s0+1]
        d=((1-sf)[...,None]*((1-hf)[...,None]*e00+hf[...,None]*e01)+sf[...,None]*((1-hf)[...,None]*e10+hf[...,None]*e11))
        hue_shift=HSM_H*d[...,0]
        sat_scale=1.0+HSM_S*(d[...,1]-1.0)
        val_scale=1.0+HSM_V*(d[...,2]-1.0)
        return self._hsv6_to_rgb(np.mod(h+hue_shift*(6.0/360.0),6),np.minimum(s*sat_scale,1),np.clip(v*val_scale,0,1))
    def to_xyz50(self,cam,xy,wA):
        CM=interp(self.CM_A,self.CM_D,wA);FM=interp(self.FM_A,self.FM_D,wA);cw=CM@xy_to_xyz(xy);cw=cw/np.max(cw);cw=np.clip(cw,.001,1)
        pp=np.clip(np.minimum(cam,cw[None,None,:])@(XYZ_TO_PP@FM@np.diag(1/cw)).T,0,1);pp=self.apply_hsm(pp,interp(self.HSM_A,self.HSM_D,wA));return pp@PP_TO_XYZ.T

def read_dng(path,long_side=1600):
    with tifffile.TiffFile(path) as tf:
        pg=tf.pages[0];t=pg.tags;raw=pg.asarray().astype(np.float32);bl=tag_numeric(t['BlackLevel']).reshape(2,2);wl=tag_scalar(t['WhiteLevel']);norm=np.empty_like(raw,dtype=np.float32)
        for yy in range(2):
            for xx in range(2):norm[yy::2,xx::2]=(raw[yy::2,xx::2]-bl[yy,xx])/(wl-bl[yy,xx])
        norm=np.clip(norm,0,1)
        clipmask=(raw>=wl);unclipped=norm[~clipmask]
        clip_fraction=float(np.mean(clipmask))
        if unclipped.size:
            uq99=float(np.quantile(unclipped,.99));uq995=float(np.quantile(unclipped,.995));uq998=float(np.quantile(unclipped,.998))
            q=float(np.clip(.999-TC_ALPHA*clip_fraction,.95,.999));adaptive_uq=float(np.quantile(unclipped,q))
        else:
            uq99=uq995=uq998=adaptive_uq=1.0;q=.95
        d1=float(np.log(max(uq995,1e-9)/max(uq99,1e-9)));d2=float(np.log(max(uq998,1e-9)/max(uq995,1e-9)));curvature=float(d2-.6*d1);isolated=bool(curvature>TC_TAIL_CURVATURE_THRESHOLD);tail=float(uq995 if isolated else adaptive_uq)
        rawm={'raw_hard_clip_fraction':clip_fraction,'raw_uq99':uq99,'raw_uq99_5':uq995,'raw_uq99_8':uq998,'tc20_q':q,'tc20_adaptive_uq':adaptive_uq,'tc20_tail_curvature':curvature,'tc20_tail_isolated':isolated,'tc20_tail_value':tail}
        cam=cv2.cvtColor((norm*65535+.5).astype(np.uint16),cv2.COLOR_BayerRG2BGR_EA).astype(np.float32)/65535.0
        h,w=cam.shape[:2]
        if long_side and max(h,w)>long_side:
            sc=long_side/max(h,w);cam=cv2.resize(cam,(round(w*sc),round(h*sc)),interpolation=cv2.INTER_AREA)
        neutral=tag_numeric(t['AsShotNeutral']);orientation=int(t['Orientation'].value) if 'Orientation' in t else 1;baseline=0.0
        if 'BaselineExposure' in t:baseline=tag_scalar(t['BaselineExposure'])
        iso=int(t['ISOSpeedRatings'].value) if 'ISOSpeedRatings' in t else 0
    return cam,neutral,orientation,baseline,iso,rawm

def orient_image(im,o):
    if o==3:return im.rotate(180,expand=True)
    if o==6:return im.rotate(-90,expand=True)
    if o==8:return im.rotate(90,expand=True)
    return im

def meter_components(y,target=METER_TARGET_RENORM,allow=METER_ALLOW,cw=METER_CW,gmin=.5,gmax=16.0):
    h,w=y.shape;yy,xx=np.mgrid[0:h,0:w];r=np.sqrt(((yy-h/2)/(h/2))**2+((xx-w/2)/(w/2))**2);wg=np.exp(-(r**2)/(2*cw**2)).ravel();yf=y.ravel();m=yf>1e-5
    if not m.any():return 1.0,1.0,0.0
    o=np.argsort(yf[m]);ys=yf[m][o];ws=wg[m][o];cu=np.cumsum(ws);med=float(ys[np.searchsorted(cu,cu[-1]*.5)]);base=float(np.clip(target/max(med,1e-6),gmin,gmax));th=float(np.quantile(yf,1.0-allow));legacy=base if th<=1e-6 else min(base,1.0/th)
    return base,float(np.clip(legacy,gmin,gmax)),th

def tc20_meter(y,rawm,baseline_ev=0.0):
    """Accepted global exposure meter from R3.4.

    The weighted-median scene-density request is preserved.  Highlight
    protection is measured from recoverable RAW samples only.  Already-white
    samples are discounted through q = .999 - .20*clip_fraction.  If the
    P99.8 tail is statistically isolated from the broader P99..P99.5 tail,
    P99.5 is used instead so a tiny highlight cluster cannot dominate global
    exposure.  The guard never forces gain below 1x.
    """
    base_pre,legacy_pre,p98=meter_components(y);scale=2**baseline_ev;base=base_pre*scale;legacy=legacy_pre*scale;tail=max(float(rawm['tc20_tail_value']),1e-9);guard=max(1.0,TC_HEADROOM_TARGET/tail);gain=float(min(base,guard))
    return gain,{'base_median_gain':float(base),'legacy_r31_gain':float(legacy),'legacy_p98_proxy':float(p98),'tc20_guard_gain':float(guard),**rawm}

def exact_fpga_422(rgb8,cct):
    h,w,_=rgb8.shape;w2=w-(w%2);R=rgb8[:,:w2,0].astype(np.int64);G=rgb8[:,:w2,1].astype(np.int64);B=rgb8[:,:w2,2].astype(np.int64)
    Y=(4899*R+9617*G+1868*B)>>14;Rs=R[:,0::2]+R[:,1::2];Gs=G[:,0::2]+G[:,1::2];Bs=B[:,0::2]+B[:,1::2]
    CbS=((((-2765*Rs+1)>>1)-((5427*Gs)>>1)+((8192*Bs)>>1)))>>14;CrS=((((8192*Rs)>>1)-((6860*Gs)>>1)-((1332*Bs)>>1)))>>14
    Cb=(CbS+128)&0xff;Cr=(CrS+128)&0xff;cb=np.repeat(Cb,2,axis=1).astype(np.float64)-128.;cr=np.repeat(Cr,2,axis=1).astype(np.float64)-128.
    tg=tungsten_guard_weight(cct)
    cb=np.where(cb<0,cb*(1.0-TG_NEG_CB_COMPRESSION*tg),cb)
    cr=np.where(cr<0,cr*(1.0-TG_NEG_CR_COMPRESSION*tg),cr)
    out=np.stack([Y+1.402*cr,Y-.344136*cb-.714136*cr,Y+1.772*cb],-1)/255.0
    if w2!=w:out=np.concatenate([out,rgb8[:,w2:,:].astype(np.float64)/255.0],axis=1)
    return np.clip(out,0,1)

def m9_stage(post_wb_m9,gain,curve,sat,cct):
    Qe,Qo=MATRIX_BANK[sat];x=np.clip(np.rint(post_wb_m9*gain*RAW_MAX),0,RAW_MAX).astype(np.int64);flat=x.reshape(-1,3);mask=flat[:,0]>=flat[:,1];acc=np.empty_like(flat);acc[mask]=flat[mask]@Qe.T;acc[~mask]=flat[~mask]@Qo.T;idx=np.clip(acc>>16,0,LUT_MAX).astype(np.int32);rgb8=curve[idx].reshape(x.shape).astype(np.uint8);img=exact_fpga_422(rgb8,cct);return img,float(mask.mean()),float(np.mean((rgb8==0)|(rgb8==255)))

def sat_stats(img):
    a=np.asarray(img,dtype=np.float32)/255.0;mx=a.max(axis=-1);mn=a.min(axis=-1);s=np.divide(mx-mn,np.maximum(mx,1e-9),out=np.zeros_like(mx),where=mx>1e-9)
    return float(np.mean(s)),float(np.median(s)),float(np.quantile(s,.9)),float(np.mean((a<=1/255)|(a>=254/255)))

def make_contact(items,path,cols=3,W=430,H=360,T=34):
    rows=(len(items)+cols-1)//cols;sheet=Image.new('RGB',(W*cols,(H+T)*rows),'white');d=ImageDraw.Draw(sheet)
    for i,(label,p) in enumerate(items):
        im=Image.open(p).convert('RGB');im.thumbnail((W-10,H-8),Image.Resampling.LANCZOS);x=(i%cols)*W;y=(i//cols)*(H+T);d.text((x+6,y+6),label,fill='black');sheet.paste(im,(x+(W-im.width)//2,y+T))
    sheet.save(path,quality=94,subsampling=0)

def extract_curve02(fwpath):
    fw=Path(fwpath).read_bytes();_,_,d0=struct.unpack_from('<4sII',fw,0);off,size,_=struct.unpack_from('<II8s',fw,d0+16);luts=fw[off:off+size];_,_,d1=struct.unpack_from('<4sII',luts,0);off,size,_=struct.unpack_from('<II8s',luts,d1);proc=luts[off:off+size];_,_,d2=struct.unpack_from('<4sII',proc,0);off,size,_=struct.unpack_from('<II8s',proc,d2+16);pl=proc[off:off+size];return np.frombuffer(pl[3320+2*2048:3320+3*2048],dtype=np.uint8).copy()

def main():
    ap=argparse.ArgumentParser(description='M9 renderer v2.6 R3.8-H25/TG1 candidate — R3.6 CCT correction plus M9Modern tungsten guard.');ap.add_argument('dngdir',type=Path);ap.add_argument('--dcp',type=Path,required=True);ap.add_argument('--firmware',type=Path,required=True);ap.add_argument('--outdir',type=Path,default=Path('/mnt/data/M9Cam_R35_TC20_Frozen'));ap.add_argument('--long-side',type=int,default=1600);a=ap.parse_args()
    out=a.outdir;out.mkdir(parents=True,exist_ok=True);[ (out/f'SAT{s}').mkdir(exist_ok=True) for s in (2,3,4) ];(out/'contact_sheets').mkdir(exist_ok=True);(out/'metadata').mkdir(exist_ok=True)
    curve=extract_curve02(a.firmware);(out/'metadata'/'curve_02.bin').write_bytes(curve.tobytes());dcp=CobaltDCP(a.dcp);dngs=sorted(a.dngdir.glob('*.dng'));rows=[];master=[]
    for p in dngs:
        cam,neutral,orientation,baseline,iso,rawm=read_dng(p,a.long_side);xy=dcp.neutral_to_xy(neutral);T=cct_from_xy(xy);wA=weight_A(T);xyz50=dcp.to_xyz50(cam,xy,wA);xyz_scene=xyz50@bradford(D50_XY,xy).T;M9CM=interp(M9_CM_A,M9_CM_D65,wA);mcam=xyz_scene@M9CM.T;mwhite=M9CM@xy_to_xyz(xy);m9=np.maximum(mcam/np.maximum(mwhite[None,None,:],1e-8),0.0)
        xyz65=xyz50@bradford(D50_XY,D65_XY).T;prox=xyz65@XYZ2SRGB.T;ylin=np.maximum(.2126*prox[...,0]+.7152*prox[...,1]+.0722*prox[...,2],0);g,meter_meta=tc20_meter(ylin,rawm,baseline)
        frame=[]
        for sat in (2,3,4):
            img,occ,clip8=m9_stage(m9,g,curve,sat,T);pil=orient_image(Image.fromarray((img*255+.5).astype(np.uint8)),orientation);q=out/f'SAT{sat}'/f'{p.stem}_SAT{sat}.jpg';pil.save(q,quality=95,subsampling=0);meanS,medS,p90S,edgeclip=sat_stats(pil);frame.append((f'{p.stem[-6:]}  SAT{sat}',q));master.append((f'{p.stem[-6:]}  SAT{sat}',q));rows.append({'file':p.name,'sat':sat,'iso':iso,'gain':g,'legacy_r31_gain':meter_meta['legacy_r31_gain'],'base_median_gain':meter_meta['base_median_gain'],'raw_hard_clip_fraction':meter_meta['raw_hard_clip_fraction'],'tc20_tail_curvature':meter_meta['tc20_tail_curvature'],'tc20_tail_isolated':meter_meta['tc20_tail_isolated'],'tc20_tail_value':meter_meta['tc20_tail_value'],'tc20_guard_gain':meter_meta['tc20_guard_gain'],'cct':T,'A_weight':wA,'branch_even_occ':occ,'rgb8_clip_fraction':clip8,'preview_mean_sat':meanS,'preview_median_sat':medS,'preview_p90_sat':p90S,'preview_edge_clip_fraction':edgeclip})
        make_contact(frame,out/'contact_sheets'/f'{p.stem}_SAT234.jpg',cols=3);print('done',p.name,'TC20',round(g,3),'legacy',round(meter_meta['legacy_r31_gain'],3),'clip%',round(100*meter_meta['raw_hard_clip_fraction'],3),'CCT',round(T),flush=True)
    make_contact(master,out/'contact_sheets'/'MASTER_9FRAME_SAT234.jpg',cols=3,W=420,H=330,T=32)
    with (out/'metadata'/'sat234_stats.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    manifest={'renderer':'v2.6-R3.8-H25/TG1 candidate','parent_renderer':'v2.6-R3.7-TG1 candidate','meter':'TC20 accepted after full 12-frame regression','tc20':{'headroom_target':TC_HEADROOM_TARGET,'alpha':TC_ALPHA,'tail_curvature_threshold':TC_TAIL_CURVATURE_THRESHOLD,'isolated_tail_fallback':'recoverable P99.5','normal_tail':'adaptive recoverable quantile q=.999-alpha*raw_clip_fraction','gain_floor':1.0},'hsm_strength':[0.25,.85,1.0],'meter_target':METER_TARGET_RENORM,'saturation_pairs':{'2':'M04/M05','3':'M06/M07 preferred','4':'M08/M09'},'colour_tone_core_changes':'R3.8 changes only Xiaomi Cobalt HSM hue strength 1.00->0.25; HSM S/V, CCTFIX, TC20, SAT3, curve02, exact BT601 and TG1 unchanged','dng_count':len(dngs)};(out/'metadata'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('CREATED',out)
if __name__=='__main__':main()
