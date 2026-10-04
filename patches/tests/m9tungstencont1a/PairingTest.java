import com.particlesdevs.photoncamera.m9.preview.*;

public class PairingTest {
    static int n;
    static void check(boolean v,String m){n++;if(!v)throw new AssertionError(m);}
    static M9PreviewFrameState1W s(long ts){return new M9PreviewFrameState1W(ts);}

    public static void main(String[] args){
        M9PreviewStatePairer1A p=new M9PreviewStatePairer1A();

        p.offer(s(1_000_000_000L));
        check(p.hasStateAfter(0L),"startup metadata permits first consume");
        check(p.select(1_000_000_000L,10_000_000_000L).resultTimestampNs==1_000_000_000L,"exact");
        check(!p.hasStateAfter(1_000_000_000L),"matched state cannot unlock next texture");

        p.offer(s(2_003_000_000L));
        check(p.hasStateAfter(1_000_000_000L),"newer metadata unlocks next texture");
        check(p.select(2_000_000_000L,11_000_000_000L).resultTimestampNs==2_003_000_000L,"nearest within 5ms");
        check(!p.hasStateAfter(2_000_000_000L),"nearest matched state consumed once");

        p.offer(s(3_016_000_000L));
        check(p.hasStateAfter(2_000_000_000L),"future result unlocks pending texture");
        M9PreviewFrameState1W held=p.select(3_000_000_000L,12_000_000_000L);
        check(held.resultTimestampNs==2_003_000_000L,"unexpected mismatch holds last matched state instead of blank");
        check(p.snapshot().getString("decision").equals("hold_last_matched_unmatched_texture"),"hold decision reported");

        check(p.hasStateAfter(3_000_000_000L),"unmatched future state remains available for next texture");
        check(p.select(3_016_000_000L,12_016_000_000L).resultTimestampNs==3_016_000_000L,"next texture recovers exact pairing");
        check(!p.hasStateAfter(3_016_000_000L),"recovered match cannot be reused");

        check(p.snapshot().getLong("matchedDraws")==3,"match counter");
        check(p.snapshot().getLong("heldDraws")==1,"hold counter");
        p.reset();
        check(p.snapshot().getString("decision").equals("reset"),"reset diagnostics");
        System.out.println("M9PREVIEWPAIR1B pairing PASS: "+n+" assertions");
    }
}
