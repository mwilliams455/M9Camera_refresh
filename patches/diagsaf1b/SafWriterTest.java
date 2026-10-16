package com.particlesdevs.photoncamera.util;

import android.content.ContentResolver;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import java.io.*;
import java.util.*;

public class SafWriterTest {
    static int checks;
    static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    interface Action { void run() throws Exception; }
    static void fails(Action action)throws Exception{try{action.run();throw new AssertionError("Expected failure");}catch(IOException expected){checks++;}}
    static final class Doc { final String id,name,mime; byte[] bytes = new byte[0];
        Doc(String id,String name,String mime){this.id=id;this.name=name;this.mime=mime;}}
    static final class Provider extends ContentResolver {
        final LinkedHashMap<String,Doc> docs=new LinkedHashMap<>();
        int queries,created,opened,closed,resolved; boolean nullCursor,loading,denied,brokenCursor,nullOpen,nullCreate,missingColumn;
        Uri lastOpened; String mode,lastRelative; Uri parent=new Uri("opaque-parent-id",null,false);
        Uri parent(String path){resolved++;lastRelative=path;return parent;}
        Doc add(String name,String mime){Doc d=new Doc("opaque ID :%/"+docs.size(),name,mime);docs.put(d.id,d);return d;}
        @Override public Cursor query(Uri uri,String[] cols,String sel,String[] args,String sort){
            queries++;check(uri.children,"query uses child document URI");
            check(Arrays.equals(cols,new String[]{"id","name","mime"}),"one projected query gets names and IDs together");
            if(denied)throw new SecurityException("revoked");if(nullCursor)return null;
            List<Doc> list=new ArrayList<>(docs.values());
            return new Cursor(){int i=-1;boolean didClose;
                public Bundle getExtras(){Bundle b=new Bundle();b.loading=loading;return b;}
                public int getColumnIndexOrThrow(String key){if(missingColumn)throw new IllegalArgumentException("column");return Arrays.asList(cols).indexOf(key);}
                public boolean moveToNext(){if(brokenCursor)throw new IllegalStateException("provider died");return ++i<list.size();}
                public String getString(int col){Doc d=list.get(i);return col==0?d.id:col==1?d.name:d.mime;}
                public void close(){check(!didClose,"cursor closes once");didClose=true;closed++;}
            };
        }
        @Override public Uri create(Uri parent,String mime,String name){created++;if(nullCreate)return null;Doc d=add(name,mime);return new Uri(d.id,parent,false);}
        @Override public OutputStream openOutputStream(Uri uri,String mode)throws FileNotFoundException {
            opened++;lastOpened=uri;this.mode=mode;if(nullOpen)return null;
            Doc d=docs.get(uri.id);if(d==null)throw new FileNotFoundException();
            check("wt".equals(mode),"explicit truncate mode");
            return new ByteArrayOutputStream(){@Override public void close(){d.bytes=toByteArray();}};
        }
        DiagnosticSafWriter1B writer(){return new DiagnosticSafWriter1B(this,new File("/storage/root"),this::parent);}
    }
    static void write(DiagnosticSafWriter1B writer,String path,String payload)throws Exception {
        try(OutputStream o=writer.open(path,"application/json")){o.write(payload.getBytes(java.nio.charset.StandardCharsets.UTF_8));}
    }
    public static void main(String[] args)throws Exception {
        Provider p=new Provider();for(int i=0;i<3203;i++)p.add("old_"+i+".json","application/json");
        DiagnosticSafWriter1B w=p.writer();write(w,"/storage/root/DCIM/PhotonCamera/fresh.json","large old value");
        check(p.queries==1 && p.created==1 && p.resolved==1,"3203-file folder needs one child query, one creation, one parent resolution");
        Doc fresh=p.docs.get(p.lastOpened.id);check(p.lastOpened.tree==p.parent,"opaque child ID uses granted tree");
        write(w,"/storage/root/DCIM/PhotonCamera/fresh.json","x");
        check(p.queries==2 && p.created==1 && p.resolved==1,"rewrite reuses parent but refreshes filename lookup, no delete or recreate");
        check(Arrays.equals(fresh.bytes,new byte[]{'x'}),"short replacement has no trailing bytes");
        check(((Number)w.snapshot().values.get("directoryCacheHits")).longValue()==1,"cache hit recorded");
        check(p.closed==2,"both query cursors closed");
        p.docs.remove(fresh.id);write(w,"/storage/root/DCIM/PhotonCamera/fresh.json","recreated");
        check(p.created==2,"external deletion is observed by next lookup");
        for(int i=0;i<6;i++)write(w,"/storage/root/folder"+i+"/capture.json","ok");
        check(((Number)w.snapshot().values.get("cachedDirectories")).intValue()==4,"directory cache is bounded");
        int before=p.queries;fails(()->w.open("/storage/root_other/file.json","application/json"));
        fails(()->w.open("/storage/root/../escape.json","application/json"));
        fails(()->w.open("relative/file.json","application/json"));
        check(p.queries==before,"outside-root and relative paths never reach provider");
        for(String fault:List.of("nullCursor","loading","denied","brokenCursor","nullOpen","nullCreate","missingColumn")) {
            Provider f=new Provider();DiagnosticSafWriter1B fw=f.writer();
            Provider.class.getDeclaredField(fault).setBoolean(f,true);
            fails(()->write(fw,"/storage/root/DCIM/report.json","data"));
            check(((Number)fw.snapshot().values.get("cachedDirectories")).intValue()==0,"failed provider invalidates parent cache: "+fault);
            if(!fault.equals("nullOpen") && !fault.equals("nullCreate"))check(f.created==0,"failed or incomplete query never creates a duplicate: "+fault);
            Provider.class.getDeclaredField(fault).setBoolean(f,false);
            write(fw,"/storage/root/DCIM/report.json","retry");
            check(f.resolved==2,"retry resolves grants again: "+fault);
            check(new String(f.docs.get(f.lastOpened.id).bytes,java.nio.charset.StandardCharsets.UTF_8).equals("retry"),"retry bytes complete: "+fault);
        }
        Provider dir=new Provider();dir.add("report.json",DocumentsContract.Document.MIME_TYPE_DIR);
        fails(()->write(dir.writer(),"/storage/root/DCIM/report.json","never"));
        check(dir.created==0 && dir.opened==0,"directory collision never deletes or overwrites anything");
        Provider missing=new Provider();missing.parent=null;fails(()->write(missing.writer(),"/storage/root/DCIM/report.json","never"));
        check(missing.queries==0,"missing grant never queries children");
        System.out.println("{\"status\":\"PASS\",\"assertions\":"+checks+",\"largeDirectoryEntries\":3203,\"largeDirectoryQueriesPerOpen\":1,\"failureScenarios\":7}");
    }
}
