package com.particlesdevs.photoncamera.m9.preview;

public final class BackgroundQualificationTest {
    static int checks;
    static void eq(double a,double b,String why) {checks++;if(Math.abs(a-b)>1e-9)throw new AssertionError(why+": "+a+" != "+b);}
    static void yes(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
    public static void main(String[] args) {
        M9BackgroundQualification1A q=new M9BackgroundQualification1A();
        long n=10_000_000_000L;
        eq(q.update(1.75,23,n,true),1.75,"initial allowance unchanged");
        for(int cycle=0;cycle<12;cycle++) {
            for(double cap:new double[]{1.5,1,1.25,1.75}) {
                n+=250_000_000L;
                eq(q.update(cap,23,n,true),1.75,"transient TV evidence cannot lower qualified cap");
                for(int i=0;i<10;i++)eq(q.update(cap,23,n,false),1.75,"duplicate callbacks are not confirmations");
            }
        }
        for(int i=0;i<3;i++){n+=250_000_000L;eq(q.update(1,23,n,true),1.75,"three probes cannot lower qualification");}
        eq(q.update(1,23,n+1_000_000_000L,false),1.75,"time with no new probe cannot confirm");
        n+=250_000_000L;eq(q.update(1,23,n,true),1,"sustained scene change accepted after 750ms");
        for(int i=0;i<4;i++){n+=10_000_000L;eq(q.update(2.5,23,n,true),1,"four rapid probes insufficient");}
        n+=750_000_000L;eq(q.update(2.5,23,n,true),2.5,"fresh settled increase accepted");
        n+=250_000_000L;q.update(1,23,n,true);
        n+=250_000_000L;q.update(1,23,n,true);
        q.breakWindow();
        n+=250_000_000L;eq(q.update(1,23,n,true),2.5,"reference gap breaks confirmation");
        n+=1_300_000_000L;eq(q.update(1,23,n,true),2.5,"long gap cannot finish old window");
        eq(q.update(1,99,n+1,true),1,"new body uses its own evidence");
        q.reset();eq(q.update(2,99,n+2,true),2,"reset does not retain allowance");
        long last=n+2;
        for(int i=0;i<10;i++)eq(q.update(1,99,last-i,true),2,"out of order samples never vote");
        for(int i=0;i<4;i++){n+=250_000_000L;q.update(i%2==0?1:1.25,99,n,true);}
        eq(q.capEv(),1.25,"adjacent bins accept least decrease all probes support");
        yes(q.confirmations()==0,"accepted window resets");
        System.out.println("BACKGROUND_QUALIFICATION_ASSERTIONS "+checks+" PASS");
    }
}
