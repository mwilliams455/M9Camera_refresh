import java.util.*;
import org.json.*;

// Read-only Camera2 accessors; do not emulate the photographic calculations.
class LensShadingMap {
    final float[] gains;
    final int width,height;
    int reads;
    LensShadingMap(float[] gains,int width,int height) { this.gains=gains.clone();this.width=width;this.height=height; }
    int getColumnCount(){return width;}
    int getRowCount(){return height;}
    int getGainFactorCount(){return gains.length;}
    void copyGainFactors(float[] output,int offset){reads++;System.arraycopy(gains,0,output,offset,gains.length);}
}

public class Parity {
    static int cases,rejections;
    static long pixels;
    static volatile Object sink;
    static final double[] ALPHAS={0.0,0.125,1.0/3.0,0.7,1.0};
    static final int[][] MAPS={{1,1},{1,7},{9,1},{2,2},{17,13},{33,25}};

    static LensShadingMap map(int width,int height,int pattern) {
        float[] gains=new float[width*height*4];Random random=new Random(913+pattern);
        for(int y=0;y<height;y++)for(int x=0;x<width;x++)for(int c=0;c<4;c++) {
            double dx=(x-width/2.0)/Math.max(1,width),dy=(y-height/2.0)/Math.max(1,height);
            gains[(y*width+x)*4+c]=pattern==0?1f:pattern==1?2.25f:pattern==2?
                    (float)(1+(dx*dx+dy*dy)*(c+1)*3):pattern==3?
                    (float)(0.125+random.nextDouble()*15.875):(x<width/2?0.5f:8f)+(c*0.03125f);
        }
        return new LensShadingMap(gains,width,height);
    }
    static short[] raw(int width,int height,int pattern) {
        short[] raw=new short[width*height];Random random=new Random(125+pattern);
        for(int i=0;i<raw.length;i++)raw[i]=(short)(pattern==0?0:pattern==1?65535:pattern==2?
                (i*65535L/Math.max(1,raw.length-1)):pattern==3?random.nextInt(65536):(i%3==0?32767:i%3==1?32768:1));
        return raw;
    }
    static String run(boolean before,int renderer,int kind,short[] raw,int w,int h,LensShadingMap map,double alpha,int cfa,int ox,int oy) {
        if(renderer==0)return before?BeforeM9.run(kind,raw,w,h,map,alpha,cfa,ox,oy):AfterM9.run(kind,raw,w,h,map,alpha,cfa,ox,oy);
        return before?BeforeMonochrom.run(kind,raw,w,h,map,alpha,cfa,ox,oy):AfterMonochrom.run(kind,raw,w,h,map,alpha,cfa,ox,oy);
    }
    static void compare(int renderer,int kind,int w,int h,int pattern,LensShadingMap map,double alpha,int cfa,int ox,int oy) {
        short[] before=raw(w,h,pattern),after=before.clone();float[] original=map.gains.clone();
        map.reads=0;
        String bs=run(true,renderer,kind,before,w,h,map,alpha,cfa,ox,oy);
        String as=run(false,renderer,kind,after,w,h,map,alpha,cfa,ox,oy);
        if(!Arrays.equals(before,after)||!bs.equals(as)||!Arrays.equals(original,map.gains)||map.reads!=2)
            throw new AssertionError("case="+cases+" renderer="+renderer+" helper="+kind+" size="+w+"x"+h+" alpha="+alpha);
        cases++;pixels+=before.length;
    }
    static void reject(int renderer,int kind,LensShadingMap map,double alpha,int cfa) {
        short[] b=raw(17,13,3),a=b.clone();String bs="",as="";
        try {run(true,renderer,kind,b,17,13,map,alpha,cfa,0,0);}catch(RuntimeException e){bs=e.getClass().getName()+":"+e.getMessage();}
        try {run(false,renderer,kind,a,17,13,map,alpha,cfa,0,0);}catch(RuntimeException e){as=e.getClass().getName()+":"+e.getMessage();}
        if(bs.isEmpty()||!bs.equals(as)||!Arrays.equals(b,a))throw new AssertionError("rejection changed: "+bs+" / "+as);
        rejections++;
    }
    static double median(double[] values){double[] a=values.clone();Arrays.sort(a);return a[a.length/2];}
    static double timed(boolean before,int renderer,int kind,short[] original,LensShadingMap map) {
        short[] frame=original.clone(); // Input copy excluded; coordinate allocation remains timed.
        long start=System.nanoTime();
        sink=run(before,renderer,kind,frame,4096,3072,map,0.37,kind>=2?3:0,kind>=2?1:0,kind>=2?1:0);
        double elapsed=(System.nanoTime()-start)/1e6;
        sink=frame;
        return elapsed;
    }
    static JSONObject benchmark(int renderer,int kind) throws Exception {
        short[] frame=raw(4096,3072,3);LensShadingMap map=map(17,13,2);
        for(int i=0;i<5;i++){timed(true,renderer,kind,frame,map);timed(false,renderer,kind,frame,map);}
        double[] before=new double[9],after=new double[9];
        for(int i=0;i<9;i++)if((i&1)==0){before[i]=timed(true,renderer,kind,frame,map);after[i]=timed(false,renderer,kind,frame,map);}
            else{after[i]=timed(false,renderer,kind,frame,map);before[i]=timed(true,renderer,kind,frame,map);}
        return new JSONObject().put("renderer",renderer==0?"M9":"Monochrom").put("helper",kind)
                .put("parentMs",before).put("candidateMs",after).put("parentMedianMs",median(before)).put("candidateMedianMs",median(after))
                .put("medianSavedMs",median(before)-median(after)).put("stageReductionPercent",100*(1-median(after)/median(before)));
    }
    public static void main(String[] args) throws Exception {
        for(int renderer=0;renderer<2;renderer++) {
            // Degenerate axes, odd dimensions, all input values and map edge shapes.
            for(int kind=0;kind<4;kind++)for(int[] size:new int[][]{{1,1},{1,17},{19,1},{2,2},{3,5},{97,65}})
                for(int[] grid:MAPS)for(int pattern=0;pattern<5;pattern++)
                    for(double alpha:((kind&1)==1?ALPHAS:new double[]{1.0}))
                        compare(renderer,kind,size[0],size[1],pattern,map(grid[0],grid[1],pattern),alpha,kind%4,pattern%2,(pattern/2)%2);
            // All CFA patterns and sensor-origin parities, including nonzero/negative offsets.
            for(int kind:new int[]{2,3})for(int cfa=0;cfa<4;cfa++)for(int ox:new int[]{0,1,10,-3})for(int oy:new int[]{0,1,6,-5})
                compare(renderer,kind,129,67,3,map(17,13,3),0.3/1.731,cfa,ox,oy);
            // Every uint16 code, full-resolution random frames and a second 12 MP geometry.
            for(int kind=0;kind<4;kind++) {
                compare(renderer,kind,65536,1,2,map(33,1,4),0.37,3,1,1);
                compare(renderer,kind,4096,3072,3,map(17,13,2),0.37,3,1,1);
                compare(renderer,kind,4000,3000,4,map(33,25,3),1.0,1,10,7);
                reject(renderer,kind,null,1.0,0);
                reject(renderer,kind,new LensShadingMap(new float[0],0,1),1.0,0);
                reject(renderer,kind,new LensShadingMap(new float[3],1,1),1.0,0);
                for(float invalid:new float[]{Float.NaN,Float.POSITIVE_INFINITY,0,-1})
                    reject(renderer,kind,new LensShadingMap(new float[]{1,invalid,1,1},1,1),1.0,0);
                if((kind&1)==1)for(double alpha:new double[]{Double.NaN,Double.POSITIVE_INFINITY,-0.01,1.01})
                    reject(renderer,kind,map(1,1,0),alpha,0);
                if(kind>=2)reject(renderer,kind,map(1,1,0),1.0,5);
            }
        }
        JSONArray timings=new JSONArray();timings.put(benchmark(0,1)).put(benchmark(1,0)).put(benchmark(0,3)).put(benchmark(1,2));
        JSONObject report=new JSONObject().put("status","PASS").put("parityCases",cases).put("rejectionCases",rejections)
                .put("rawSamplesCompared",pixels).put("rawSamplesAndStatsBitExact",true).put("sourceMapsUnmodified",true)
                .put("mapCopyCountUnchanged",true).put("hostJava",System.getProperty("java.version"))
                .put("dimensions","4096x3072").put("warmups",5).put("pairedRounds",9).put("benchmarks",timings)
                .put("additionalCoordinateArrayPayloadBytesAtWidth4096",4096L*16)
                .put("scope","Actual before/after Java shading helpers; read-only Camera2 adapter. Shading-stage host benchmark, not whole-JPEG or phone timing.")
                .put("phoneValidationPending",true);
        System.out.println(report.toString(2));
    }
}
