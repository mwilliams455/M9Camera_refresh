package com.particlesdevs.photoncamera.processing.render;

import java.util.Arrays;
import java.util.Random;
import java.util.Scanner;

/** Existing-behavior probes, not Android or renderer integration tests. */
public class NumericProbe {
    static int checks;
    static void require(boolean result, String message) {
        if (!result) throw new AssertionError(message);
        checks++;
    }
    static String rows(float x) {
        return x+",0,0\n0,"+x+",0\n0,0,"+x+"\n";
    }
    static ColorCorrectionTransform matrices(String p1, String p2) {
        ColorCorrectionTransform c = new ColorCorrectionTransform();
        c.FillCCT(new Scanner("MATRIXES\n\n"+p1+"\n\n"+rows(1)+"\n"+p2+"\n\n"+rows(2)));
        return c;
    }
    static ColorCorrectionTransform cubes(String p1, String p2) {
        ColorCorrectionTransform c = new ColorCorrectionTransform();
        String a = rows(1)+"\n"+rows(1)+"\n"+rows(1);
        String b = rows(2)+"\n"+rows(2)+"\n"+rows(2);
        c.FillCCT(new Scanner("CUBES\nfirst\n"+p1+"\n\n"+a+"second\n"+p2+"\n\n"+b));
        return c;
    }
    static int nonfinite(float[] values) {
        int count=0;
        for(float f:values) if(!Float.isFinite(f)) count++;
        return count;
    }
    public static void main(String[] args) {
        ColorCorrectionTransform regular = matrices("1,1,1", "0.25,0.25,1");
        float[] normal = regular.combineMatrix(new float[]{0.5f,0.5f,1});
        require(nonfinite(normal)==0 && Math.abs(normal[0]-5f/3)<1e-6f, "ordinary matrix interpolation");
        System.out.println("matrix_normal first="+normal[0]+" nonfinite="+nonfinite(normal));

        float[] bad = matrices("1,1,1", "2,2,2").combineMatrix(new float[]{0.5f,0.5f,1});
        require(nonfinite(bad)==9, "equal ratios must reproduce nonfinite matrix coefficients");
        System.out.println("matrix_equal_reference_ratios nonfinite="+nonfinite(bad)+"/9");
        float[] zero = regular.combineMatrix(new float[]{0.5f,0.5f,0});
        require(nonfinite(zero)==9, "zero blue white-point component");
        System.out.println("matrix_zero_white_point_blue nonfinite="+nonfinite(zero)+"/9");

        ColorCorrectionTransform equalCube = cubes("1,1,1", "2,2,2");
        float[][] badCube = equalCube.cubes[0].Combine(equalCube.cubes[1], new float[]{0.5f,0.5f,1});
        int badCubeCount=0;
        for(float[] row:badCube) badCubeCount+=nonfinite(row);
        require(badCubeCount==27, "equal ratios must reproduce nonfinite cube coefficients");
        System.out.println("cube_equal_reference_ratios nonfinite="+badCubeCount+"/27");

        ColorCorrectionTransform goodCube = cubes("1,1,1", "0.25,0.25,1");
        float[] wp = {0.1f,0.2f,0.3f};
        float[] before = wp.clone();
        float[][] first = goodCube.cubes[0].Combine(goodCube.cubes[1],wp);
        require(!Arrays.equals(before,wp), "cube caller white point mutation");
        System.out.println("cube_input_mutation before="+Arrays.toString(before)+" after_one="+Arrays.toString(wp));
        float[][] last = first;
        for(int i=1;i<100;i++) last=goodCube.cubes[0].Combine(goodCube.cubes[1],wp);
        require(first[0][0]!=last[0][0], "repeated cube calls can change coefficients");
        System.out.println("cube_repeated_calls first="+first[0][0]+" after_100="+last[0][0]);

        Extracted p = new Extracted();
        for(double strength:new double[]{-6,0,4}) {
            p.runNoise(strength,0.001,0.00001);
            require(Float.isFinite(p.noiseS) && Float.isFinite(p.noiseO) && p.noiseS>0 && p.noiseO>0,"normal noise strength");
            System.out.println("noise_normal strength="+strength+" S="+p.noiseS+" O="+p.noiseO);
        }
        p.runNoise(Double.NaN,0.001,0.00001);
        require(Float.isNaN(p.noiseS) && Float.isNaN(p.noiseO), "minimum clamp does not reject NaN");
        System.out.println("noise_invalid_strength_NaN S="+p.noiseS+" O="+p.noiseO);
        p.runNoise(140,0.001,0.00001);
        require(Float.isInfinite(p.noiseS), "out-of-range persisted strength overflows float");
        System.out.println("noise_invalid_strength_140 S="+p.noiseS+" O="+p.noiseO);

        Extracted.Rect normalRect = new Extracted.Rect(0,0,4000,3000);
        p.scale(normalRect,6000.0/normalRect.bottom);
        require(normalRect.right==8000 && normalRect.bottom==6000, "ordinary 2x rectangle");
        Extracted.Rect invalidRect = new Extracted.Rect(0,0,4000,0);
        p.scale(invalidRect,6000.0/invalidRect.bottom);
        require(invalidRect.right==Integer.MAX_VALUE && invalidRect.bottom==0, "invalid rectangle saturates rather than throwing");
        System.out.println("rectangle_zero_bottom right="+invalidRect.right+" bottom="+invalidRect.bottom);

        Random random = new Random(288);
        boolean difference=false;
        for(int i=0;i<100000;i++) {
            float x=random.nextFloat()*3f;
            float d=random.nextFloat()*3f+0.001f;
            float original=x; original*=1.0/d;
            float floatOnly=x; floatOnly*=1.0f/d;
            if(Float.floatToRawIntBits(original)!=Float.floatToRawIntBits(floatOnly)) {
                System.out.println("float_literal_change_example x="+x+" denominator="+d+" original="+original+" float_only="+floatOnly);
                difference=true; break;
            }
        }
        require(difference, "float literal rewrite can change numeric results");
        System.out.println("PASS existing_behavior_checks="+checks);
    }
}
