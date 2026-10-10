package com.particlesdevs.photoncamera.m9.preview;

import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

/** Exercise complete production decisions, including every rejection boundary. */
public final class BridgeTest {
    static int checks;
    static boolean candidate;
    static long now=5_000_000_000L;
    static String mode="PHOTO";
    static Stats[] safe=SubjectHeadroomTest.scene(0);
    static double high;
    static void eq(double a,double b,String label) {
        checks++; if(!Double.isFinite(a)||Math.abs(a-b)>1e-8)
            throw new AssertionError(label+": "+a+" != "+b);
    }
    static void yes(boolean b,String label) {checks++;if(!b)throw new AssertionError(label);}
    static Sample sample(String camera,String mode,long stamp,long texture,long result,double energy,Stats[] stats) {
        return new Sample(camera,mode,stamp,texture,result,energy,stats);
    }
    static void publish(Stats[] stats,double energy) {
        now+=250_000_000L;
        M9AutoExposure2D.publish(sample("T",mode,now,now,now,energy,stats));
    }
    static Decision decision(long elapsed,double energy,double legacy) {
        return M9AutoExposure2D.decide("T",mode,now+elapsed,energy,0,0,0,legacy,true);
    }
    static void start() {
        M9AutoExposure2D.reset();
        for(int i=0;i<8;i++){publish(safe,1);high=decision(1,1,0).appliedEv;}
        eq(high,1.75,"inherited stable subject target");
    }
    static void flicker() {
        start();
        for(int cycle=0;cycle<12;cycle++) {
            publish(safe,1);
            double before=decision(1,1,0).appliedEv;
            double energy=Math.pow(2,.30);
            Decision held=decision(50_000_000L,energy,0);
            if(candidate) {
                eq(before,high,"fresh target unchanged");
                eq(held.appliedEv,high-.30,"reference rise transports accepted energy");
                eq(energy*Math.pow(2,held.appliedEv),Math.pow(2,high),"no absolute exposure jump");
                yes(held.reason.equals("rendered_meter_reference_transition_hold"),"bridge is diagnosed explicitly");
            } else eq(held.appliedEv,0,"parent reproduces correction collapse");
            for(int j=0;j<10;j++)eq(decision(50_000_000L+j,energy,0).appliedEv,held.appliedEv,"callback repetition cannot drift");
        }
        start();
        double lower=Math.pow(2,-.30);
        eq(decision(50_000_000L,lower,0).appliedEv,candidate?high:0,"lower reference never increases held correction");
    }
    static void limits() {
        start();double energy=Math.pow(2,.3);
        eq(decision(500_000_000L,energy,0).appliedEv,candidate?high-.3:0,"bounded half-second bridge");
        eq(decision(500_000_001L,energy,0).appliedEv,0,"bridge expires even when calls continue");
        eq(decision(500_000_002L,energy,0).appliedEv,0,"expired bridge cannot rearm");
        start();
        for(int i=1;i<=6;i++)decision(i*70_000_000L,1,0);
        eq(decision(500_000_001L,energy,0).appliedEv,0,"duplicate valid reads cannot refresh anchor time");
        start();
        eq(decision(50_000_000L,Math.sqrt(2),0).appliedEv,candidate?high-.5:0,"half-stop reference boundary");
        start();eq(decision(50_000_000L,Math.pow(2,.50001),0).appliedEv,0,"larger rise falls back immediately");
        start();eq(decision(50_000_000L,Math.pow(2,-.50001),0).appliedEv,0,"larger fall falls back immediately");
        start();eq(decision(50_000_000L,energy,-.25).appliedEv,-.25,"new negative legacy decision is not delayed");
        start();decision(50_000_000L,energy,0);
        publish(SubjectHeadroomTest.scene(2),energy);
        eq(decision(1,energy,0).appliedEv,.5,"fresh highlight restriction remains immediate after bridge");
        start();decision(50_000_000L,energy,0);
        publish(safe,energy);
        yes(decision(1,energy,0).appliedEv>0,"fresh evidence resumes normal metering");
        // A small accepted lift cannot bridge a larger rise in reference energy.
        // Returning unity in that case is normal fallback, not an energy-capped hold.
        M9AutoExposure2D.reset();
        Stats[] ordinary=new Stats[11];
        for(int i=0;i<11;i++)ordinary[i]=new Stats(90+i*3,.05,.01,.001,
                100+i*3,70+i*3,140+i*3,.05,.01,.01,.001,.001);
        publish(ordinary,1);eq(decision(1,1,.1).appliedEv,.1,"small accepted correction");
        Decision exhausted=decision(50_000_000L,energy,0);
        eq(exhausted.appliedEv,0,"insufficient anchor energy falls back");
        yes(!exhausted.reason.equals("rendered_meter_reference_transition_hold"),"fallback is not falsely labelled a bounded hold");
        start();
        for(int i=0;i<40;i++) {
            double delta=i%2==0?.30:.45;
            Decision d=decision(20_000_000L+i*10_000_000L,Math.pow(2,delta),0);
            if(candidate) {
                eq(d.appliedEv,high-delta,"changing mismatch cannot ratchet the baseline");
                eq(Math.pow(2,delta+d.appliedEv),Math.pow(2,high),"every held output remains energy-capped");
            } else eq(d.appliedEv,0,"parent gap output");
        }
        eq(decision(450_000_000L,1,0).appliedEv,candidate?high:0,"same accepted sample can resume without a permanent baseline loss");
    }
    static void rejectedEvidence() {
        for(int which=0;which<10;which++) {
            start();
            String camera="T",sampleMode=mode;
            long stamp=now,texture=now,result=now;double sampleEnergy=1;
            Stats[] stats=safe.clone();
            switch(which) {
                case 0:camera="OTHER";break;
                case 1:sampleMode="OTHER";break;
                case 2:stamp=now+100_000_000L;break;
                case 3:stamp=now-M9AutoExposure2D.MAX_AGE_NS-1;break;
                case 4:texture=0;break;
                case 5:result=now-150_000_001L;break;
                case 6:sampleEnergy=Double.NaN;break;
                case 7:stats[0]=null;break;
                case 8:sampleEnergy=0;break;
                case 9:stamp=now-1;break;
            }
            M9AutoExposure2D.publish(sample(camera,sampleMode,stamp,texture,result,sampleEnergy,stats));
            eq(decision(50_000_000L,Math.pow(2,.3),0).appliedEv,0,"no bridge for invalid evidence "+which);
        }
        for(double energy:new double[]{0,-1,Double.NaN,Double.POSITIVE_INFINITY}) {
            start();eq(decision(50_000_000L,energy,0).appliedEv,0,"invalid current energy");
        }
    }
    static void controls() {
        for(int which=0;which<8;which++) {
            start();
            switch(which) {
                case 0:M9AutoExposure2D.reset();break;
                case 1:M9AutoExposure2D.invalidate("test");break;
                case 2:M9AutoExposure2D.decide("T",mode,now+1,1,-.7,0,0,0,true);break;
                case 3:M9AutoExposure2D.decide("T",mode,now+1,1,0,10_000_000L,0,0,true);break;
                case 4:M9AutoExposure2D.decide("T",mode,now+1,1,0,0,100,0,true);break;
                case 5:M9AutoExposure2D.decide("T",mode,now+1,1,0,0,0,0,false);break;
                case 6:M9AutoExposure2D.decide("OTHER",mode,now+1,1,0,0,0,0,true);break;
                case 7:M9AutoExposure2D.decide("T","OTHER",now+1,1,0,0,0,0,true);break;
            }
            eq(decision(50_000_000L,Math.pow(2,.3),0).appliedEv,0,"boundary clears bridge "+which);
        }
        start();
        M9TapMeter1A.configure("T",mode,now,320,240,new int[]{0,0,320,240},new float[]{1,0,0,1},false);
        yes(M9TapMeter1A.choose(160,120,now),"tap chosen");M9TapMeter1A.clear("epoch test");
        eq(decision(50_000_000L,Math.pow(2,.3),0).appliedEv,0,"tap epoch clears bridge");
    }
    public static void main(String[] args) {
        candidate=Boolean.parseBoolean(args[0]);
        for(String m:new String[]{"PHOTO","MOTION"}) {mode=m;flicker();limits();rejectedEvidence();controls();}
        System.out.println("BRIDGE_ASSERTIONS "+checks+" PASS");
    }
}
