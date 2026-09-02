public class NormNative1aParityTest {
    static long mix(long h, long v) {
        h ^= v;
        return h * 1099511628211L;
    }
    public static void main(String[] args) {
        int width=257, height=193, pixels=width*height, wl=1023;
        float[] black={64.0f,65.0f,63.0f,64.0f};
        long[][] hist=new long[4][wl];
        long clipped=0;
        short[] out=new short[pixels];
        for (int y=0;y<height;y++) {
            int row=y*width, py=y&1;
            for (int x=0;x<width;x++) {
                int i=row+x;
                int plane=py*2+(x&1);
                int rv=(i*73 + y*19 + x*7 + (i>>>3)) % 1300;
                if (rv>=wl) clipped++; else hist[plane][rv]++;
                float bl=black[plane];
                float v=(rv-bl)/Math.max(1.0f, wl-bl);
                if (v<0.0f) v=0.0f;
                if (v>1.0f) v=1.0f;
                int nv=(int)Math.floor(v*65535.0f+0.5f);
                out[i]=(short)(nv & 0xffff);
            }
        }
        long h=1469598103934665603L;
        for (short q:out) h=mix(h, q & 0xffffL);
        h=mix(h,clipped);
        for (int p=0;p<4;p++) for(int r=0;r<wl;r++) h=mix(h,hist[p][r]);
        System.out.printf("normnative1a java checksum=%016x clipped=%d pixels=%d%n",h,clipped,pixels);
    }
}
