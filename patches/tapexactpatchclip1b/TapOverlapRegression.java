package com.particlesdevs.photoncamera.m9.preview;

import java.lang.reflect.Method;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Random;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
import com.particlesdevs.photoncamera.m9.preview.M9TapMeter1A.PatchStats;

/** Synthetic only. Executes the real tap guard and real no-tap controller. */
public final class TapOverlapRegression {
    private static int checks;
    private static Method guard;
    private static int[] fill(int n) {
        int[] a=new int[24]; Arrays.fill(a,n); return a;
    }
    private static Stats stats(double clip,double bright,int a,int b,boolean regionalWhite,boolean oldHighlight) {
        double[] c=new double[24],w=new double[24];
        if(a>=0)c[a]=.12;
        if(b>=0)c[b]=.12;
        if(regionalWhite){w[a]=.60;w[b]=.60;}
        return new Stats(35,.5,bright,clip,25,5,215,.6,.1,.02,.001,.02,
                fill(110),fill(45),fill(oldHighlight?225:210),w,c);
    }
    private static String stop(Stats base,Stats next,PatchStats p0,PatchStats previous,
                               PatchStats patch,int mask,boolean brightBackground) throws Exception {
        return (String)guard.invoke(null,base,next,p0,previous,patch,mask,brightBackground);
    }
    private static void eq(String got,String expected,String label) {
        if(!expected.equals(got))throw new AssertionError(label+": "+got+" != "+expected);
        checks++;
    }
    private static void guardTests(boolean repaired) throws Exception {
        guard=M9AutoExposure2D.class.getDeclaredMethod("tapStop",Stats.class,Stats.class,
                PatchStats.class,PatchStats.class,PatchStats.class,int.class,boolean.class);
        guard.setAccessible(true);
        Stats base=stats(.005,.03,-1,-1,false,false);
        PatchStats p0=new PatchStats(10,3,28,0,0);
        PatchStats prev=new PatchStats(20,8,40,0,0);
        PatchStats next=new PatchStats(24,10,46,0,0);
        for(int f=0;f<24;f++) {
            int other=(f+1)%24,mask=(1<<f)|(1<<other);
            Stats v=stats(.01,.04,f,other,false,false);
            eq(stop(base,v,p0,prev,next,mask,true),repaired?"none":"regional_channel_clip_growth",
                    "two overlapping coarse fields, exact patch unclipped "+f);
            eq(stop(base,v,p0,prev,next,0,true),"none","non-subject fields defer "+f);
        }
        Stats v=stats(.01,.04,2,3,false,false);int mask=(1<<2)|(1<<3);
        eq(stop(base,v,p0,prev,new PatchStats(24,10,46,0,.125),mask,true),
                "tap_patch_channel_clip_growth","direct selected patch remains protected");
        eq(stop(base,stats(.09,.04,2,3,false,false),p0,prev,next,mask,true),
                "global_channel_clip_growth","global clip remains protected");
        eq(stop(base,stats(.01,.24,2,3,false,false),p0,prev,next,mask,true),
                "global_nearwhite_growth","global near-white remains protected");
        eq(stop(base,stats(.01,.04,2,3,true,false),p0,prev,next,mask,true),
                "regional_nearwhite_growth","broad regional near-white remains protected");
        eq(stop(base,v,p0,prev,next,mask,false),"regional_channel_clip_growth","weak background does not defer");
        eq(stop(base,v,p0,prev,prev,mask,true),"regional_channel_clip_growth","no useful progress does not defer");
        eq(stop(base,v,p0,new PatchStats(60,24,80,0,0),new PatchStats(64,26,86,0,0),mask,true),
                "regional_channel_clip_growth","already-reached target does not defer");
        eq(stop(stats(.005,.03,-1,-1,false,true),v,p0,prev,prev,mask,false),
                "none","existing highlight grandfather rule unchanged");
        eq(stop(new Stats(35,.5,.03,.005),v,p0,prev,next,mask,true),
                "invalid_field_map","invalid map fails closed");
        eq(stop(base,v,p0,prev,new PatchStats(20,10,40,0,0),mask,true),
                repaired?"none":"regional_channel_clip_growth","quartile-only progress");
        eq(stop(base,v,p0,prev,new PatchStats(20,8,45,0,0),mask,true),
                repaired?"none":"regional_channel_clip_growth","upper-tail-only progress unchanged");
        System.out.println("OVERLAP_GUARD_ASSERTIONS "+checks+" repaired="+repaired);
    }
    private static void noTapParity() throws Exception {
        Random random=new Random(9262517L);
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        long now=1_000_000_000L;int decisions=0;
        for(int scene=0;scene<96;scene++) {
            M9AutoExposure2D.reset();
            int median=8+random.nextInt(140),center=5+random.nextInt(125);
            for(int frame=0;frame<12;frame++) {
                Stats[] bracket=new Stats[11];
                for(int step=0;step<11;step++) {
                    int m=Math.min(255,median+step*9),cm=Math.min(255,center+step*8);
                    double c=Math.min(.9,step*.009),b=Math.min(.9,step*.018);
                    bracket[step]=new Stats(m,.35,b,c,cm,Math.max(0,cm-22),230,
                            .45,.20,b/2,c/2,c,fill(m),fill(Math.max(0,m-24)),fill(210),new double[24],new double[24]);
                }
                now+=100_000_000L;
                M9AutoExposure2D.publish(new Sample("synthetic_camera","PHOTO",now,now,now,1,bracket));
                Decision d=M9AutoExposure2D.decide("synthetic_camera","PHOTO",now+1,1,0,0,0,0,true);
                String line=scene+":"+frame+":"+Double.toHexString(d.appliedEv)+":"+d.reason+":"
                        +M9AutoExposure2D.bodyLockMaskForDiagnostics()+"\n";
                digest.update(line.getBytes(StandardCharsets.UTF_8));decisions++;
            }
        }
        StringBuilder hex=new StringBuilder();for(byte x:digest.digest())hex.append(String.format("%02x",x&255));
        System.out.println("NO_TAP_PARITY "+decisions+" "+hex);
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=1||!(args[0].equals("true")||args[0].equals("false")))
            throw new IllegalArgumentException("expected repaired=true/false");
        guardTests(Boolean.parseBoolean(args[0]));noTapParity();
    }
}
