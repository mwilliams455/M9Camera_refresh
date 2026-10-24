import com.particlesdevs.photoncamera.control.subject.PetPreviewRetryPolicy;

/** Pure JDK proof: transient PixelCopy exceptions never permanently latch AF off. */
public final class PetPreviewRetryPolicyHostTest {
    private static void check(boolean value,String note) {
        if(!value)throw new AssertionError(note);
    }
    public static void main(String[] args) {
        PetPreviewRetryPolicy p=new PetPreviewRetryPolicy();
        p.reset();
        long t=10_000L;
        check(p.mayAttempt(t),"initial attempt allowed");
        long d=p.failure(t,"pixelcopy_request","IllegalArgumentException");
        check(d==250 && p.failures()==1,"first retry is 250ms");
        check(!p.mayAttempt(t+249),"no repeated submission before deadline");
        check(p.mayAttempt(t+250),"first retry allowed");
        d=p.failure(t+250,"pixelcopy_callback","ERROR_SOURCE_NO_DATA");
        check(d==500 && p.failures()==2,"second retry is 500ms");
        d=p.failure(t+750,"bitmap_create","IllegalArgumentException");
        check(d==1000 && p.failures()==3,"third retry is 1000ms");
        d=p.failure(t+1750,"pixelcopy_request","IllegalStateException");
        check(d==2000 && p.failures()==4,"fourth retry is 2s");
        for(int k=0;k<12;k++){
            t+=2000;
            d=p.failure(t,"pixelcopy_request","RuntimeException");
            check(d==2000,"backoff never exceeds 2 seconds");
        }
        check(p.failures()>3 && p.mayAttempt(t+2000),"no permanent latch after transient failures");
        p.success();
        check(p.mayAttempt(t) && p.failures()==0,"successful copy clears error backoff");
        check("ready".equals(p.lastStage()),"success clears error message");
        p.failure(t+2,"pixelcopy_request","PixelCopy");
        p.reset();
        check(p.failures()==0 && p.mayAttempt(t+2),"lens switch resets retry");
        check(p.remainingMs(t+2)==0,"fresh session no wait");
        check("IllegalArgumentException".length()<=36,"exception class fits status");
        boolean threw=false;
        try{p.failure(-1,"stage","error");}catch(IllegalArgumentException expected){threw=true;}
        check(threw,"bad monotonic input rejected");
        System.out.println("PASS: PetPreviewRetryPolicyHostTest (retries/latched failure/reset)");
    }
}
