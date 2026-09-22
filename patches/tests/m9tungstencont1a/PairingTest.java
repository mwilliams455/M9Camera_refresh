import com.particlesdevs.photoncamera.m9.preview.*;

public class PairingTest {
    static int n;
    static void check(boolean v,String m){n++;if(!v)throw new AssertionError(m);}
    static M9PreviewFrameState1W s(long ts){return new M9PreviewFrameState1W(ts);}

    public static void main(String[] args){
        M9PreviewStatePairer1A p=new M9PreviewStatePairer1A();
        p.offer(s(1_000_000_000L));
        check(p.select(1_000_000_000L,10_000_000_000L).resultTimestampNs==1_000_000_000L,"exact");
        p.offer(s(2_003_000_000L));
        check(p.select(2_000_000_000L,11_000_000_000L).resultTimestampNs==2_003_000_000L,"nearest within 5ms");
        p.offer(s(3_016_000_000L));
        check(p.select(3_000_000_000L,12_000_000_000L)==null,"adjacent-frame state must not pair");
        check(p.select(3_000_000_000L,12_100_000_000L)==null,"still deferred before 120ms");
        check(p.select(3_000_000_000L,12_121_000_000L).resultTimestampNs==3_016_000_000L,"bounded timeout fallback");
        p.offer(s(4_000_000_000L));
        check(p.select(4_000_000_000L,13_000_000_000L).resultTimestampNs==4_000_000_000L,"recovers exact after timeout");
        check(p.snapshot().getLong("matchedDraws")>=3,"match counter");
        check(p.snapshot().getLong("deferredDraws")==2,"defer counter");
        check(p.snapshot().getLong("timeoutFallbacks")==1,"timeout counter");
        p.reset();
        check(p.snapshot().getString("decision").equals("reset"),"reset diagnostics");
        System.out.println("M9PREVIEWPAIR1A pairing PASS: "+n+" assertions");
    }
}
