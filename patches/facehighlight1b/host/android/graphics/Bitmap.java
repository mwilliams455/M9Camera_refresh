package android.graphics;
/** Host-only, solid-colour frame. Excluded from both the Android class build and the APK. */
public class Bitmap {
    private int rgb;
    public Bitmap(int rgb) { this.rgb = rgb; }
    public int getWidth() { return 100; }
    public int getHeight() { return 100; }
    public int getPixel(int x, int y) { return rgb; }
    public boolean isRecycled() { return false; }
}
