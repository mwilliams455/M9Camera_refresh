package com.particlesdevs.photoncamera.m9;

import com.google.gson.Strictness;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Streaming validation skips values without constructing a diagnostic object graph. */
final class M9DiagnosticStream1A {
    static boolean isObject(InputStream in) {
        try {
            JsonReader reader=new JsonReader(new InputStreamReader(in,StandardCharsets.UTF_8));
            reader.setStrictness(Strictness.STRICT);
            if(reader.peek()!=JsonToken.BEGIN_OBJECT)return false;
            reader.skipValue();
            return reader.peek()==JsonToken.END_DOCUMENT;
        } catch(IOException | RuntimeException invalid) {return false;}
        // The caller owns the descriptor and rewinds it after validation.
    }
    static void copyUtf8(InputStream in,Writer out,boolean quote) throws IOException {
        Reader reader=new InputStreamReader(in,StandardCharsets.UTF_8);
        char[] block=new char[8192];int n;
        if(quote)out.write('"');
        while((n=reader.read(block))!=-1) {
            if(!quote){out.write(block,0,n);continue;}
            for(int i=0;i<n;i++) {
                char c=block[i];
                if(c=='"'||c=='\\'){out.write('\\');out.write(c);}
                else if(c<32){out.write("\\u00");out.write("0123456789abcdef".charAt(c>>4));out.write("0123456789abcdef".charAt(c&15));}
                else out.write(c);
            }
        }
        if(quote)out.write('"');
    }
}
