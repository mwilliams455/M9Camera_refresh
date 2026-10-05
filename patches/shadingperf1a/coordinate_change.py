"""The complete reversible SHADINGPERF1A source transformation."""
HELPER = '''    // SHADINGPERF1A: the horizontal map geometry is identical on every row.
    // Frame-local coordinates preserve the original double arithmetic; live map
    // gains, CFA selection, interpolation, headroom and rounding stay unchanged.
    private static final class ShadingXCoordinates {
        final int[] lower;
        final int[] upper;
        final double[] fraction;

        ShadingXCoordinates(int width, int mapWidth, double xScale) {
            lower = new int[width];
            upper = new int[width];
            fraction = new double[width];
            for (int x = 0; x < width; x++) {
                double gx = x * xScale;
                int x0 = (int)Math.floor(gx);
                lower[x] = x0;
                upper[x] = Math.min(mapWidth - 1, x0 + 1);
                fraction[x] = gx - x0;
            }
        }
    }

'''
SIGNATURE = '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A('
COMPACT_OLD = 'double gx=x*xScale;int x0=(int)Math.floor(gx),x1=Math.min(mapW-1,x0+1);double fx=gx-x0;'
COMPACT_NEW = 'int x0=shadingX.lower[x],x1=shadingX.upper[x];double fx=shadingX.fraction[x];'
EXPANDED_OLD = '''                double gx = x * xScale;
                int x0 = (int)Math.floor(gx);
                int x1 = Math.min(mapW - 1, x0 + 1);
                double fx = gx - x0;'''
EXPANDED_NEW = '''                int x0 = shadingX.lower[x];
                int x1 = shadingX.upper[x];
                double fx = shadingX.fraction[x];'''
INIT = '        final ShadingXCoordinates shadingX = new ShadingXCoordinates(width, mapW, xScale);\n'

def transform(text):
    start = text.index(SIGNATURE)
    before, tail = text[:start], text[start:]
    assert tail.count(COMPACT_OLD) == 3
    assert tail.count(EXPANDED_OLD) == 1
    tail = tail.replace(COMPACT_OLD, COMPACT_NEW).replace(EXPANDED_OLD, EXPANDED_NEW)
    marker = '        for(int y=0;y<height;y++)'
    assert tail.count(marker) == 3
    tail = tail.replace(marker, INIT + marker)
    marker = '        for (int y = 0; y < height; y++) {'
    assert tail.count(marker) == 1
    tail = tail.replace(marker, INIT + marker)
    return before + HELPER + tail

def reverse(text):
    assert text.count(HELPER) == 1 and text.count(INIT) == 4
    text = text.replace(HELPER, '').replace(INIT, '')
    return text.replace(COMPACT_NEW, COMPACT_OLD).replace(EXPANDED_NEW, EXPANDED_OLD)

if __name__ == '__main__':
    from pathlib import Path
    import sys
    root = Path(sys.argv[1])
    for mode in ['m9', 'monochrom']:
        path = root / ('app/src/main/java/com/particlesdevs/photoncamera/' + mode + '/render/M9R35Renderer.java')
        original = path.read_text()
        changed = transform(original)
        assert reverse(changed) == original
        path.write_text(changed)
