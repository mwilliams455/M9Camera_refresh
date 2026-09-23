package com.particlesdevs.photoncamera.util;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.function.BooleanSupplier;

/** Private log journal with bounded, foreground-only publication. No Android IPC here. */
public final class M9LocalLog1E {
    public interface Sink { boolean append(String filename,byte[] bytes)throws Exception; }
    public static final int MAX_EXPORT_BYTES=256*1024;
    private final File dir;
    private final SimpleDateFormat day=new SimpleDateFormat("yyyy-MM-dd",Locale.US);
    private final SimpleDateFormat time=new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS",Locale.US);
    private BufferedWriter writer;
    private String current;
    public M9LocalLog1E(File dir)throws IOException {this.dir=dir;if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("private log directory unavailable");}
    public synchronized void append(long timestamp,String level,String tag,String message)throws IOException {
        String name="log-"+day.format(new Date(timestamp))+".txt";
        if(!name.equals(current)){close();current=name;writer=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(dir,name),true),StandardCharsets.UTF_8),8192);}
        if(writer==null)writer=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(dir,name),true),StandardCharsets.UTF_8),8192);
        writer.write(time.format(new Date(timestamp))+" "+level+"/"+tag+": "+message+"\n");
    }
    public synchronized void flush()throws IOException {if(writer!=null)writer.flush();}
    public synchronized void close()throws IOException {if(writer!=null){try{writer.close();}finally{writer=null;}}}
    private long offset(File file){try{return Long.parseLong(new String(Files.readAllBytes(new File(dir,file.getName()+".offset").toPath()),StandardCharsets.US_ASCII).trim());}catch(Exception e){return 0;}}
    private void checkpoint(File file,long offset)throws IOException {
        Path target=new File(dir,file.getName()+".offset").toPath(),temp=new File(dir,file.getName()+".offset.tmp").toPath();
        try(FileOutputStream out=new FileOutputStream(temp.toFile())){out.write(Long.toString(offset).getBytes(StandardCharsets.US_ASCII));out.getFD().sync();}
        Files.move(temp,target,StandardCopyOption.REPLACE_EXISTING);
    }
    // One publisher calls this. Appending remains available while the provider is slow.
    public boolean exportOne(BooleanSupplier visible,Sink sink)throws Exception {
        if(!visible.getAsBoolean())return false;
        File selected=null;long start=0;byte[] chunk=null;
        synchronized(this){
            flush();File[] files=dir.listFiles((d,n)->n.matches("log-\\d{4}-\\d{2}-\\d{2}\\.txt"));
            if(files==null)return false;Arrays.sort(files,Comparator.comparing(File::getName));
            for(File file:files){long pos=offset(file);if(pos<0||pos>file.length())pos=0;
                if(pos==file.length())continue;int n=(int)Math.min(MAX_EXPORT_BYTES,file.length()-pos);chunk=new byte[n];
                try(RandomAccessFile input=new RandomAccessFile(file,"r")){input.seek(pos);input.readFully(chunk);}selected=file;start=pos;break;}
        }
        if(selected==null||!visible.getAsBoolean())return false;
        if(!sink.append(selected.getName(),chunk))return false;
        synchronized(this){checkpoint(selected,start+chunk.length);}
        // If killed after a provider append but before checkpoint, at most one chunk
        // can be repeated. Never truncate the public log or discard the private copy.
        return true;
    }
    public synchronized void cleanup(long now){
        File[] files=dir.listFiles((d,n)->n.matches("log-\\d{4}-\\d{2}-\\d{2}\\.txt"));if(files==null)return;
        for(File f:files)if(!f.getName().equals(current)&&now-f.lastModified()>10L*24*3600*1000&&offset(f)==f.length()){
            if(f.delete())new File(dir,f.getName()+".offset").delete();
        }
    }
}
