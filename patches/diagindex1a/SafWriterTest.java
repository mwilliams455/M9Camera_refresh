package com.particlesdevs.photoncamera.util;

import android.content.ContentResolver;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class SafWriterTest {
    static final AtomicInteger checks = new AtomicInteger();
    static void check(boolean ok,String message){checks.incrementAndGet();if(!ok)throw new AssertionError(message);}
    interface Action { void run() throws Exception; }
    static void fails(Action action)throws Exception{try{action.run();throw new AssertionError("Expected failure");}catch(IOException expected){checks.incrementAndGet();}}
    static final class Doc {
        final String id,parent,mime; String name; byte[] bytes=new byte[0];
        Doc(String id,String parent,String name,String mime){this.id=id;this.parent=parent;this.name=name;this.mime=mime;}
    }
    static final class Provider extends ContentResolver {
        final LinkedHashMap<String,Doc> docs=new LinkedHashMap<>();
        final Map<String,Doc> names=new HashMap<>(); final Map<String,Uri> parents=new HashMap<>();
        int nextId,childQueries,docQueries,created,opened,closed,resolved,deleted;
        boolean nullCursor,loading,denied,brokenCursor,nullOpen,nullCreate,missingColumn,nullValidation,denyDelete;
        boolean noParent; Uri lastOpened; String lastMode;
        volatile CountDownLatch entered,release;
        synchronized Uri parent(String relative){resolved++;return noParent?null:parents.computeIfAbsent(relative,k->new Uri("opaque-parent-"+parents.size(),null,false));}
        synchronized Doc add(Uri parent,String name,String mime){
            Doc d=new Doc("opaque ID :%/"+nextId++,parent.id,name,mime);docs.put(d.id,d);names.put(parent.id+"/"+name,d);return d;
        }
        synchronized Doc named(Uri parent,String name){return names.get(parent.id+"/"+name);}
        synchronized void remove(Doc d){docs.remove(d.id);names.remove(d.parent+"/"+d.name,d);}
        synchronized void rename(Doc d,String name){names.remove(d.parent+"/"+d.name,d);d.name=name;names.put(d.parent+"/"+name,d);}
        @Override public Cursor query(Uri uri,String[] cols,String sel,String[] args,String sort){
            List<String[]> list=new ArrayList<>();
            synchronized(this){
                if(uri.children)childQueries++;else docQueries++;
                if(denied)throw new SecurityException("revoked");
                if(nullCursor || (!uri.children && nullValidation))return null;
                check(Arrays.equals(cols,new String[]{"id","name","mime"}),"projected metadata columns");
                if(uri.children){for(Doc d:docs.values())if(d.parent.equals(uri.id))list.add(new String[]{d.id,d.name,d.mime});}
                else {Doc d=docs.get(uri.id);if(d!=null)list.add(new String[]{d.id,d.name,d.mime});}
            }
            CountDownLatch signal=entered,gate=release;
            if(uri.children && signal!=null && gate!=null){signal.countDown();try{if(!gate.await(5,TimeUnit.SECONDS))throw new AssertionError("latch timeout");}catch(InterruptedException e){throw new RuntimeException(e);}}
            return new Cursor(){int i=-1;boolean didClose;
                public Bundle getExtras(){Bundle b=new Bundle();b.loading=loading;return b;}
                public int getColumnIndexOrThrow(String key){if(missingColumn)throw new IllegalArgumentException("column");return Arrays.asList(cols).indexOf(key);}
                public boolean moveToNext(){if(brokenCursor)throw new IllegalStateException("provider died");return ++i<list.size();}
                public String getString(int col){return list.get(i)[col];}
                public void close(){check(!didClose,"cursor closes once");didClose=true;synchronized(Provider.this){closed++;}}
            };
        }
        @Override public synchronized Uri create(Uri parent,String mime,String name){
            created++;if(nullCreate)return null;String actual=name;int suffix=0;
            while(named(parent,actual)!=null)actual=name+" ("+(++suffix)+")";
            Doc d=add(parent,actual,mime);return new Uri(d.id,parent,false);
        }
        @Override public synchronized boolean delete(Uri uri){
            if(denyDelete)return false;Doc d=docs.get(uri.id);if(d==null)return false;
            check(d.bytes.length==0,"only an unwritten newly allocated collision file is removed");
            remove(d);deleted++;return true;
        }
        @Override public synchronized OutputStream openOutputStream(Uri uri,String mode)throws FileNotFoundException {
            opened++;lastOpened=uri;lastMode=mode;if(nullOpen)return null;
            Doc d=docs.get(uri.id);if(d==null)throw new FileNotFoundException();
            check("wt".equals(mode),"explicit truncate mode");
            return new ByteArrayOutputStream(){@Override public void close(){synchronized(Provider.this){d.bytes=toByteArray();}}};
        }
        DiagnosticSafWriter1B writer(){return new DiagnosticSafWriter1B(this,new File("/storage/root"),this::parent);}
    }
    static void write(DiagnosticSafWriter1B w,String path,String payload)throws Exception {
        try(OutputStream o=w.open(path,"application/json")){o.write(payload.getBytes(java.nio.charset.StandardCharsets.UTF_8));}
    }
    static long value(DiagnosticSafWriter1B w,String key){return ((Number)w.snapshot().values.get(key)).longValue();}
    static String bytes(Doc d){return new String(d.bytes,java.nio.charset.StandardCharsets.UTF_8);}
    public static void main(String[] args)throws Exception {
        Provider p=new Provider();Uri folder=p.parent("DCIM/PhotonCamera");
        for(int i=0;i<20000;i++)p.add(folder,"historical_"+i+".json","application/json");
        DiagnosticSafWriter1B w=p.writer();
        for(int i=0;i<3229;i++)write(w,"/storage/root/DCIM/PhotonCamera/backlog_"+i+".json","payload_"+i);
        check(p.childQueries==1,"3229 exports in 20000-file folder share one directory scan");
        check(p.docQueries==3229 && p.created==3229 && p.opened==3229,"each new export creates, validates and opens its own exact file");
        check(value(w,"lookupRowsVisited")==20000 && value(w,"cachedEntries")==23229,"index advances with successful creations without rescans");
        check(value(w,"indexOverflows")==0,"representative large directory fits bounded index");
        check(bytes(p.named(folder,"backlog_0.json")).equals("payload_0") && bytes(p.named(folder,"backlog_3228.json")).equals("payload_3228"),"backlog endpoint bytes match");
        Doc first=p.named(folder,"backlog_0.json");write(w,"/storage/root/DCIM/PhotonCamera/backlog_0.json","x");
        check(bytes(first).equals("x") && p.childQueries==1 && p.created==3229,"short rewrite reuses validated opaque handle and truncates");
        check(p.lastOpened.tree==folder,"returned child URI retains granted parent");
        p.rename(first,"archived.json");write(w,"/storage/root/DCIM/PhotonCamera/backlog_0.json","new");
        check(bytes(first).equals("x") && bytes(p.named(folder,"backlog_0.json")).equals("new"),"external rename cannot overwrite archived document");
        check(p.childQueries==2,"rename refreshes once");
        p.remove(p.named(folder,"backlog_0.json"));write(w,"/storage/root/DCIM/PhotonCamera/backlog_0.json","recreated");
        check(p.childQueries==3 && bytes(p.named(folder,"backlog_0.json")).equals("recreated"),"external deletion is refreshed and recreated");
        Doc external=p.add(folder,"external.json","application/json");external.bytes="old".getBytes();
        write(w,"/storage/root/DCIM/PhotonCamera/external.json","wanted");
        check(bytes(external).equals("wanted") && p.deleted==1 && p.childQueries==4,"stale absence collision removes only our empty allocation and reuses exact existing name");
        check(p.named(folder,"external.json (1)")==null && value(w,"createCollisions")==1,"no duplicate collision report remains");
        int before=p.childQueries+p.docQueries;
        fails(()->w.open("/storage/root_other/file.json","application/json"));fails(()->w.open("/storage/root/../escape.json","application/json"));fails(()->w.open("relative/file.json","application/json"));
        check(p.childQueries+p.docQueries==before,"outside-root paths never reach provider");
        for(int i=0;i<6;i++)write(w,"/storage/root/folder"+i+"/capture.json","ok");
        check(value(w,"cachedDirectories")==4,"directory cache bounded");

        for(String fault:List.of("nullCursor","loading","denied","brokenCursor","nullOpen","nullCreate","missingColumn","nullValidation")) {
            Provider f=new Provider();DiagnosticSafWriter1B fw=f.writer();Provider.class.getDeclaredField(fault).setBoolean(f,true);
            fails(()->write(fw,"/storage/root/DCIM/report.json","data"));
            check(value(fw,"cachedDirectories")==0,"provider failure invalidates cache: "+fault);
            if(!Set.of("nullOpen","nullCreate","nullValidation").contains(fault))check(f.created==0,"failed index does not imply absence: "+fault);
            Provider.class.getDeclaredField(fault).setBoolean(f,false);write(fw,"/storage/root/DCIM/report.json","retry");
            check(f.resolved==2 && bytes(f.docs.get(f.lastOpened.id)).equals("retry"),"retry resolves grant and writes full payload: "+fault);
        }
        Provider overflow=new Provider();Uri of=overflow.parent("DCIM");
        for(int i=0;i<8;i++)overflow.add(of,"existing_"+i+".json","application/json");
        DiagnosticSafWriter1B ow=new DiagnosticSafWriter1B(overflow,new File("/storage/root"),overflow::parent,2,10000);
        write(ow,"/storage/root/DCIM/existing_7.json","same");
        check(value(ow,"cachedEntries")==2 && value(ow,"indexOverflows")==1 && value(ow,"uncachedLookups")==1,"entry cap falls back to exact query");
        check(overflow.created==0 && bytes(overflow.named(of,"existing_7.json")).equals("same"),"overflow cannot treat uncached existing file as absent");
        DiagnosticSafWriter1B cw=new DiagnosticSafWriter1B(overflow,new File("/storage/root"),overflow::parent,100,1);
        write(cw,"/storage/root/DCIM/existing_6.json","chars");check(value(cw,"cachedCharacters")<=1 && overflow.created==0,"character cap also retains correct existing-file lookup");

        Provider dir=new Provider();Uri df=dir.parent("DCIM");dir.add(df,"report.json",DocumentsContract.Document.MIME_TYPE_DIR);
        fails(()->write(dir.writer(),"/storage/root/DCIM/report.json","never"));check(dir.created==0 && dir.opened==0 && dir.deleted==0,"directory collision remains untouched");
        Provider duplicate=new Provider();Uri dup=duplicate.parent("DCIM");duplicate.add(dup,"same.json","application/json");duplicate.add(dup,"same.json","application/json");
        fails(()->write(duplicate.writer(),"/storage/root/DCIM/same.json","never"));check(duplicate.opened==0 && duplicate.deleted==0,"ambiguous provider names cannot be overwritten");
        Provider missing=new Provider();missing.noParent=true;fails(()->write(missing.writer(),"/storage/root/DCIM/report.json","never"));check(missing.childQueries==0,"no grant does not query children");
        Provider cleanup=new Provider();Uri cf=cleanup.parent("DCIM");DiagnosticSafWriter1B cl=cleanup.writer();write(cl,"/storage/root/DCIM/seed.json","seed");Doc keep=cleanup.add(cf,"collision.json","application/json");keep.bytes="preserve".getBytes();cleanup.denyDelete=true;
        fails(()->write(cl,"/storage/root/DCIM/collision.json","must retry"));check(bytes(keep).equals("preserve") && value(cl,"openFailures")==1,"failed cleanup does not consume payload or overwrite existing report");

        Provider concurrent=new Provider();DiagnosticSafWriter1B co=concurrent.writer();concurrent.entered=new CountDownLatch(1);concurrent.release=new CountDownLatch(1);
        ExecutorService pool=Executors.newFixedThreadPool(6);
        try {
            Future<?> cold=pool.submit(()->{try{write(co,"/storage/root/DCIM/first.json","first");}catch(Exception e){throw new RuntimeException(e);}});
            check(concurrent.entered.await(2,TimeUnit.SECONDS),"cold scan is held");
            Future<?> snapshot=pool.submit(co::snapshot);snapshot.get(1,TimeUnit.SECONDS);check(!cold.isDone(),"capture snapshot does not wait for directory scan");
            List<Future<?>> futures=new ArrayList<>();
            for(int i=0;i<12;i++){final int n=i;futures.add(pool.submit(()->{try{write(co,"/storage/root/DCIM/concurrent_"+n+".json","bytes"+n);}catch(Exception e){throw new RuntimeException(e);}}));}
            concurrent.release.countDown();cold.get(3,TimeUnit.SECONDS);for(Future<?> f:futures)f.get(3,TimeUnit.SECONDS);
            check(concurrent.childQueries==1 && concurrent.opened==13,"concurrent exporters coalesce cold scan and all complete");
        } finally {concurrent.release.countDown();pool.shutdownNow();}
        System.out.println("{\"status\":\"PASS\",\"assertions\":"+checks.get()+",\"largeDirectoryEntries\":20000,\"queuedExports\":3229,\"directoryScansForQueuedExports\":1,\"failureScenarios\":8,\"concurrencyAndSnapshotIsolation\":true}");
    }
}
