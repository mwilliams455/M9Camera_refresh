import com.particlesdevs.photoncamera.m9.preview.M9PreviewMath2A;
public class MathTest {
    static int n;
    static void check(boolean v,String m){n++;if(!v)throw new AssertionError(m);}
    public static void main(String[] args) {
        for(int count:new int[]{16,32,64}) {
            float[] c=M9PreviewMath2A.srgbCurve(count);
            check(M9PreviewMath2A.validCurve(c),"valid controlled curve");
            byte[] bytes=M9PreviewMath2A.inverseTexture(new float[][]{c,c,c});
            for(int i=0;i<1024;i++) {
                int q=((bytes[4*i]&255)<<8)|(bytes[4096+4*i]&255);
                check(Math.abs(q/65535.0-M9PreviewMath2A.invertCurve(c,i/1023.0))<1.0/65535,"inverse transport precision");
            }
        }
        for(float[] c:new float[][]{null,{0,0,1,Float.NaN},{0,0,.5f,.5f,1,.5f},{0,0,.5f,.7f,.4f,.8f,1,1},{0,0,1,2}})
            check(!M9PreviewMath2A.validCurve(c),"reject noninvertible curve");
        double[] matrix={1.8,-.55,-.25,-.18,1.35,-.17,.05,-.65,1.6};
        double[] inverse=M9PreviewMath2A.inverse(matrix);
        for(int y=0;y<3;y++)for(int x=0;x<3;x++) {
            double sum=0;for(int k=0;k<3;k++)sum+=matrix[y*3+k]*inverse[k*3+x];
            check(Math.abs(sum-(x==y?1:0))<1e-12,"camera transform inversion");
            check(M9PreviewMath2A.columnMajor(matrix)[x*3+y]==(float)matrix[y*3+x],"GL matrix layout");
        }
        try{M9PreviewMath2A.inverse(new double[9]);throw new AssertionError("singular accepted");}catch(IllegalArgumentException expected){n++;}
        // Exposure remains a scalar sensor-energy change BEFORE the fixed target response.
        double[] sensor={.12,.18,.09},wb={2.1,1,1.4};
        for(double boost:new double[]{1,1.5,2})for(double ev:new double[]{.5,1,2}) {
            double[] oes=new double[3];for(int y=0;y<3;y++)for(int x=0;x<3;x++)oes[y]+=matrix[3*y+x]*wb[x]*boost*sensor[x];
            for(int y=0;y<3;y++){double v=0;for(int x=0;x<3;x++)v+=inverse[3*y+x]*oes[x];v=v/wb[y]/boost*ev;check(Math.abs(v-sensor[y]*ev)<1e-12,"WB boost and exposure order");}
        }
        System.out.println("GL2A math PASS: "+n+" assertions");
    }
}
