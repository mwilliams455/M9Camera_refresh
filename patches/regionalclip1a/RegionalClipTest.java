package com.particlesdevs.photoncamera.m9.preview;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

public final class RegionalClipTest {
 static int checks;
 static void yes(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
 public static void main(String[] args)throws Exception{
  RegionalFixture f=new RegionalFixture(args[0]);long n=300_000_000_000L;
  M9RegionalClipQualification1A q=new M9RegionalClipQualification1A();
  int sum=0;for(int field=0;field<24;field++){
   int count=0;for(int y=0;y<M9AutoExposure2D.HEIGHT;y++)for(int x=0;x<M9AutoExposure2D.WIDTH;x++)
    if(y*4/M9AutoExposure2D.HEIGHT*6+x*6/M9AutoExposure2D.WIDTH==field)count++;
   yes(count==M9RegionalClipQualification1A.fieldSamples(field),"actual probe geometry "+field);sum+=count;
  }yes(sum==768,"all probe pixels counted once");
  yes(q.update(n,f.boundary(true),null)==.25,"new clip entry immediate");
  for(int i=0;i<50;i++)yes(q.update(n+=250000000L,f.boundary(false),null)==.25,"one-pixel release blocked");
  Stats[] grandfather=f.boundary(false);grandfather[0].fieldClipped[9]=2.0/36;
  grandfather[0].fieldQ90[10]=221;
  yes(q.update(n+=250000000L,grandfather,null)==.25,"baseline fraction and luma exemptions alone cannot release channel clipping");
  int[] copy=q.heldMasks();copy[2]=0;
  yes(Integer.bitCount(q.heldMasks()[2])==2,"diagnostic array owns a copy");
  yes(q.update(n,RegionalFixture.clear(f.boundary(false)),null)==.25,"duplicate cannot clear");
  yes(q.update(n-1,RegionalFixture.clear(f.boundary(false)),null)==.25,"out-of-order cannot clear");
  yes(q.update(n+=250000000L,RegionalFixture.clear(f.boundary(false)),null)==2.5,"real clipping clearance releases");
  yes(q.update(n+=250000000L,f.boundary(true),null)==.25,"new loss cuts again without delay");
  yes(q.update(n+=M9AutoExposure2D.MAX_AGE_NS+1,f.boundary(false),null)==2.5,"stale history cannot survive gap");
  q.update(n+=250000000L,f.boundary(true),null);q.reset();
  yes(q.update(n+=250000000L,f.boundary(false),null)==2.5,"explicit reset");
  Stats[] subject=SubjectHeadroomTest.scene(0);
  BodyCandidate body=M9AutoExposure2D.multifieldBodyCandidate(subject[0]);
  q.reset();yes(q.update(n+=250000000L,subject,null)==.5,"background initially protected without body");
  yes(q.update(n+=250000000L,subject,body)==1.75,"existing qualified body deferral releases background masks");
  q.reset();Stats[] protectedSubject=SubjectHeadroomTest.scene(1);
  yes(q.update(n+=250000000L,protectedSubject,M9AutoExposure2D.multifieldBodyCandidate(protectedSubject[0]))==.5,"subject fields remain protected under deferral");
  // Every entry must match the inherited rule at a clean boundary. Enumerate
  // quantized values around all three gates, including preexisting highlights.
  for(int qb:new int[]{219,220,221})for(int b=0;b<=3;b++)for(int c=0;c<=8;c++){
   Stats[] s=RegionalFixture.clear(f.boundary(false));
   for(int field:new int[]{9,10}){
    int pixels=M9RegionalClipQualification1A.fieldSamples(field);
    s[0].fieldQ90[field]=qb;s[0].fieldClipped[field]=b/(double)pixels;
    s[2].fieldClipped[field]=c/(double)pixels;
   }
   q.reset();double cap=q.update(n+=250000000L,s,null);
   boolean expected=M9AutoExposure2D.highlightRetentionUnsafe(s[0],s[2]);
   yes((cap<.5)==expected,"entry parity around quantized thresholds");
  }
  System.out.println("REGIONAL_CLIP_ASSERTIONS "+checks+" PASS");
 }
}
