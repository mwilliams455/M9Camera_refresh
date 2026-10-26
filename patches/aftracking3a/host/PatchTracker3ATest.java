import com.particlesdevs.photoncamera.control.tracking.PatchTracker;
import java.util.Random;
public final class PatchTracker3ATest {
    static int checks;
    static void ok(boolean cond,String msg){checks++;if(!cond)throw new AssertionError(msg);}
    static final int W=192,H=144,S=21,HALF=10;
    static final int[] texture = new int[S*S];
    static {Random r=new Random(73);for(int i=0;i<texture.length;i++)texture[i]=25+r.nextInt(205);}
    static int rgb(int v){return 0xff000000|(v<<16)|(v<<8)|v;}
    static int[] frame(int cx,int cy,float scale,boolean show){
        int[] a=new int[W*H];
        Random n=new Random(23);
        for(int i=0;i<a.length;i++) a[i]=rgb(90+n.nextInt(22));
        if(show)paint(a,cx,cy,scale,texture);
        return a;
    }
    static void paint(int[] a,int cx,int cy,float scale,int[] img){
        int radius=Math.round(HALF*scale);
        for(int dy=-radius;dy<=radius;dy++)for(int dx=-radius;dx<=radius;dx++){
            int x=cx+dx,y=cy+dy;int tx=Math.round(dx/scale),ty=Math.round(dy/scale);
            if(x<0||x>=W||y<0||y>=H||Math.abs(tx)>HALF||Math.abs(ty)>HALF)continue;
            a[y*W+x]=rgb(img[(ty+HALF)*S+tx+HALF]);
        }
    }
    static void testTranslationAndScale(){
        PatchTracker t=new PatchTracker();
        PatchTracker.Result a=t.select(frame(82,65,1,true),W,H,82f/W,65f/H,1000);
        ok(a.tracking,"selection acquires original");
        PatchTracker.Result b=t.update(frame(91,69,1,true),W,H,1100);
        ok(b.tracking,"translation follows");
        ok(Math.abs(b.x*W-91.5)<3,"translation centre X");
        PatchTracker.Result c=t.update(frame(98,72,1.22f,true),W,H,1200);
        ok(c.tracking,"increasing size maintains tracking");
        ok(c.scale>1.0f,"size increases");
        PatchTracker.Result d=t.update(frame(105,74,1.22f,true),W,H,1300);
        ok(d.tracking,"updated scale persists");
        ok(d.halfWidth>a.halfWidth,"tracked box grows");
        PatchTracker.Result e=t.update(frame(110,75,1f,true),W,H,1400);
        ok(e.tracking,"moving away retains target");
        ok(e.scale<d.scale,"tracked box shrinks when subject recedes");
    }
    static void testOcclusionHoldRecovery(){
        PatchTracker t=new PatchTracker();
        ok(t.select(frame(80,65,1,true),W,H,80f/W,65f/H,1000).tracking,"acquired");
        PatchTracker.Result missing=t.update(frame(80,65,1,false),W,H,1100);
        ok(!missing.tracking && missing.holding,"first occlusion holds without AF");
        ok(t.update(frame(80,65,1,false),W,H,1200).holding,"continued occlusion holds");
        PatchTracker.Result appear=t.update(frame(83,68,1,true),W,H,1300);
        ok(!appear.tracking&&appear.holding,"one reappearance insufficient");
        PatchTracker.Result good=t.update(frame(84,68,1,true),W,H,1400);
        ok(good.tracking&&!good.holding,"two coherent samples recover");
        ok(Math.abs(good.x*W-84.5)<3,"recovered original nearby");
    }
    static void testPermanentLoss(){
        PatchTracker t=new PatchTracker();
        ok(t.select(frame(80,65,1,true),W,H,80f/W,65f/H,1000).tracking,"acquire permanent-loss target");
        for(long m=1100;m<=1700;m+=100){
            PatchTracker.Result r=t.update(frame(80,65,1,false),W,H,m);
            ok(!r.tracking&&r.holding,"occlusion hold bounded");
        }
        PatchTracker.Result expired=t.update(frame(80,65,1,false),W,H,1900);
        ok(!expired.tracking&&!expired.holding,"late occlusion requires new tap");
        ok(!t.update(frame(80,65,1,true),W,H,2000).tracking,"retired cannot auto reacquire");
    }
    static void testNoStealAndStale(){
        PatchTracker t=new PatchTracker();
        ok(t.select(frame(80,65,1,true),W,H,80f/W,65f/H,1000).tracking,"acquired stale test");
        int[] distractor=frame(150,65,1,true);
        ok(t.update(distractor,W,H,1100).holding,"far matching object not stolen");
        ok(!t.update(distractor,W,H,1200).tracking,"no far takeover during occlusion");
        PatchTracker.Result stale=t.update(frame(80,65,1,true),W,H,1199);
        ok(!stale.tracking,"old frame does not emit AF position");
        ok(t.update(frame(80,65,1,true),W,H,1300).holding,"return requires confirmation");
        ok(t.update(frame(80,65,1,true),W,H,1400).tracking,"consistent return recovered");
    }
    static void testTexturelessAndInvalid(){
        PatchTracker t=new PatchTracker();
        int[] plain = new int[W*H];java.util.Arrays.fill(plain,rgb(128));
        ok(!t.select(plain,W,H,.5f,.5f,1000).tracking,"textureless rejected");
        ok(!t.select(frame(80,65,1,true),W,H,Float.NaN,.5f,1000).tracking,"NaN rejected");
        ok(!t.update(frame(80,65,1,true),W,H,1100).tracking,"invalid selection never updates");
        ok(t.select(frame(80,65,1,true),W,H,80f/W,65f/H,1200).tracking,"new tap reset");
        ok(!t.update(frame(80,65,1,true),W,H,1901).tracking,"stale source frame expires");
    }
    public static void main(String[]args){
        testTranslationAndScale();testOcclusionHoldRecovery();testPermanentLoss();
        testNoStealAndStale();testTexturelessAndInvalid();
        System.out.println("PASS: "+checks+" M9 3.06 multiscale/occlusion checks");
    }
}
