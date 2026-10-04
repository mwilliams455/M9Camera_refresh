import com.particlesdevs.photoncamera.m9.preview.*;
import org.json.*;
import java.nio.file.*;
import java.util.*;

public class SpatialPreviewTest {
    static int count;
    static void check(boolean v,String name){count++;if(!v)throw new AssertionError(name);}
    static void near(double a,double b,String name){check(Math.abs(a-b)<1e-5,name+": "+a+" vs "+b);}
    static byte[] tiles(int... codes){byte[] f=new byte[96*72];for(int y=0;y<72;y++)for(int x=0;x<96;x++)f[y*96+x]=(byte)codes[(y/24)*3+x/32];return f;}
    static float[] stats18;
    static float[] input(byte[] frame){float[] out=new float[20];System.arraycopy(stats18,0,out,0,18);check(new M9PreviewSpatialStats1V().fill(frame,96,72,out,18),"spatial production summary");return out;}
    static JSONObject model(float[] s){float[] out=new float[4];boolean accepted=true;for(int i=0;i<120;i++)accepted &= M9LiveToneModel1F.fill(s,out);check(accepted,"model accepted throughout settling");return M9LiveToneModel1F.snapshotDiagnostics1P();}
    static double strength(JSONObject j){return j.getDouble("spatialPairStrength1V");}
    public static void main(String[] args)throws Exception{
        JSONObject fixture=new JSONObject(Files.readString(Path.of(args[0])));JSONArray stats=fixture.getJSONArray("stats18");stats18=new float[18];for(int i=0;i<18;i++)stats18[i]=(float)stats.getDouble(i);
        JSONArray medians=fixture.getJSONArray("tileMedians");int[] codes=new int[9];for(int i=0;i<9;i++)codes[i]=medians.getInt(i);
        byte[] frame=tiles(codes),copy=frame.clone();float[] measured=input(frame);
        near(measured[18],39,"recorded low region");near(measured[19],224,"recorded high region");check(Arrays.equals(frame,copy),"input image unchanged");
        JSONObject old=model(stats18),now=model(measured);
        near(old.getDouble("gl1qPairCurveStrengthRaw"),.1387322375,"old global classifier replay");near(strength(now),1,"bright-dominated backlight activates existing curve");near(now.getDouble("gl1qPairCurveStrengthRaw"),1,"final gate reaches shader uniform");
        near(old.getDouble("rawGainEv"),now.getDouble("rawGainEv"),"scene gain unchanged");near(old.getDouble("rawGamma"),now.getDouble("rawGamma"),"scene gamma unchanged");
        // Tile-order permutations cover quarter rotations/reflections of equal-area 3x3 cells.
        int[][] transforms={{6,3,0,7,4,1,8,5,2},{8,7,6,5,4,3,2,1,0},{2,5,8,1,4,7,0,3,6},{2,1,0,5,4,3,8,7,6}};
        for(int[] t:transforms){int[] c=new int[9];for(int i=0;i<9;i++)c[i]=codes[t[i]];float[] s=input(tiles(c));near(s[18],39,"rotation low");near(s[19],224,"rotation high");near(strength(model(s)),1,"rotation gate");}
        int[][] controls={{100,100,100,100,100,100,100,100,100},{20,20,20,20,20,20,20,20,255},{10,190,190,190,190,190,190,190,190},{180,190,200,190,200,220,170,180,190},{10,15,20,15,20,25,10,15,20}};
        for(int[] c:controls){JSONObject j=model(input(tiles(c)));near(strength(j),0,"ordinary/single bright/single dark/high key/low key adds no correction");near(j.getDouble("gl1qPairCurveStrengthRaw"),old.getDouble("gl1qPairCurveStrengthRaw"),"old behavior retained without spatial evidence");}
        float[] unsupported=measured.clone();unsupported[6]=0;unsupported[7]=0;near(strength(model(unsupported)),0,"bright support required");
        for(double ev:new double[]{-2,-.25,.25,2}){float[] s=measured.clone();s[8]=(float)Math.pow(2,ev);s[9]=(float)ev;s[10]=ev>0?240:50;s[16]=ev>0?.8f:0;JSONObject j=model(s);near(strength(j),1,"EV cannot change spatial classifier");near(j.getDouble("rawGainEv"),now.getDouble("rawGainEv"),"EV cannot change gain");}
        M9PreviewSpatialStats1V helper=new M9PreviewSpatialStats1V();float[] dest={4,5,6,7};check(!helper.fill(null,96,72,dest,1),"null frame rejected");check(Float.isNaN(dest[1])&&Float.isNaN(dest[2]),"invalid clears stale regions");near(dest[0],4,"output prefix preserved");near(dest[3],7,"output suffix preserved");
        check(!helper.fill(new byte[3],96,72,dest,1),"short buffer rejected");check(!helper.fill(frame,Integer.MAX_VALUE,Integer.MAX_VALUE,dest,1),"overflow geometry rejected");check(!helper.fill(frame,96,72,dest,4),"bad offset rejected");
        byte[] odd=new byte[11*17];Arrays.fill(odd,(byte)123);check(helper.fill(odd,11,17,dest,1),"odd dimensions handled");near(dest[1],123,"odd low");near(dest[2],123,"odd high");
        float[] missing=measured.clone();missing[18]=Float.NaN;near(strength(model(missing)),0,"missing spatial feed falls back");near(strength(model(stats18)),0,"legacy caller falls back");
        // Compile and run the actual analyzer transport method, including its call to the helper.
        AnalyzerProbe.seed(frame,stats18);float[] transported=new float[20];check(AnalyzerProbe.fillLiveToneStats1R(1,transported),"actual analyzer transport");near(transported[18],39,"analyzer low");near(transported[19],224,"analyzer high");
        AnalyzerProbe.seed(null,stats18);check(!AnalyzerProbe.fillLiveToneStats1R(1,transported),"analyzer rejects missing frame");check(Float.isNaN(transported[18])&&Float.isNaN(transported[19]),"analyzer clears stale spatial data");
        System.out.println("M9LIVEGL1V HOST PASS: "+count+" assertions; production regional summary, analyzer transport and tone classifier; no device parity claim");
    }
}
