package com.particlesdevs.photoncamera.m9.preview;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public class ReferenceGapRepro {
 public static void main(String[] args){
  long now=5000000000L;Stats[] stats=SubjectHeadroomTest.scene(0);
  M9AutoExposure2D.reset();
  for(int i=0;i<8;i++){now+=250000000L;M9AutoExposure2D.publish(new Sample("T","PHOTO",now,now,now,1,stats));M9AutoExposure2D.decide("T","PHOTO",now+1,1,0,0,0,0,true);}
  for(int i=0;i<6;i++){
   now+=250000000L;M9AutoExposure2D.publish(new Sample("T","PHOTO",now,now,now,1,stats));
   Decision a=M9AutoExposure2D.decide("T","PHOTO",now+1,1,0,0,0,0,true);
   Decision b=M9AutoExposure2D.decide("T","PHOTO",now+50000000L,Math.pow(2,.3),0,0,0,0,true);
   System.out.println("valid correction="+a.appliedEv+"; +0.30EV reference change="+b.appliedEv+"; "+b.reason);
  }
 }
}