package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;
import java.util.*;

/** Host probe uses the production policy; input/output contain metadata only. */
public final class ColorTagProbe {
    public static void main(String[] args) throws Exception {
        List<String> lines=Files.readAllLines(Paths.get(args[0]));
        String[] refs=lines.get(0).trim().split("\\s+");
        float[][] m=new float[7][];
        for(int k=0;k<7;k++) {
            String[] fields=lines.get(k+1).trim().split("\\s+");
            if(fields[0].equals("null")) continue;
            m[k]=new float[fields.length];
            for(int j=0;j<fields.length;j++) m[k][j]=Float.parseFloat(fields[j]);
        }
        M9DngColorMetadata metadata=M9DngColorMetadata.create(Integer.valueOf(refs[0]),
                refs[1].equals("null")?null:Integer.valueOf(refs[1]),m[0],m[1],m[2],m[3],m[4],m[5],m[6]);
        List<String> output=new ArrayList<>();
        for(Map.Entry<Integer,double[]> tag:metadata.tags().entrySet()) {
            String line=tag.getKey()+" "+tag.getValue().length;
            for(double value:tag.getValue()) line+=" "+Double.toString(value);
            output.add(line);
        }
        Files.write(Paths.get(args[1]),output);
    }
}
