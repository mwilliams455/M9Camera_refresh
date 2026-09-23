package com.particlesdevs.photoncamera.m9.preview;

import java.util.LinkedHashMap;

/** Bounded exact joins. Ambiguous or unknown timestamps must never select the latest capture. */
public final class M9TraceLedger1A {
    public static final class Entry {
        public final String id, camera;
        public final long shutterNs;
        public volatile long logicalNs=-1, physicalNs=-1, completedNs=-1;
        public volatile String filename;
        public volatile boolean closed;
        Entry(String id,String camera,long ns){this.id=id;this.camera=camera;shutterNs=ns;}
    }
    private final int capacity;
    private final LinkedHashMap<String,Entry> entries=new LinkedHashMap<>();
    public M9TraceLedger1A(int capacity){this.capacity=capacity;}
    public synchronized Entry begin(String id,String camera,long ns) {
        if(id==null||id.isEmpty()||camera==null||ns<=0||entries.containsKey(id))return null;
        if(entries.size()>=capacity) {
            String victim=null;
            for(Entry e:entries.values())if(e.closed){victim=e.id;break;}
            if(victim==null)return null;
            entries.remove(victim);
        }
        Entry e=new Entry(id,camera,ns);entries.put(id,e);return e;
    }
    public synchronized Entry get(String id){return entries.get(id);}
    public synchronized Entry complete(String id,long logical,long physical,long now) {
        Entry e=entries.get(id);if(e==null)return null;
        e.logicalNs=logical;e.physicalNs=physical;e.completedNs=now;return e;
    }
    public synchronized Entry bySensor(long timestamp) {
        if(timestamp<=0)return null;
        Entry found=null;
        for(Entry e:entries.values())if(e.logicalNs==timestamp||e.physicalNs==timestamp) {
            if(found!=null)return null;found=e;
        }
        return found;
    }
    public synchronized Entry byFilename(String filename) {
        if(filename==null)return null;
        Entry found=null;
        for(Entry e:entries.values())if(filename.equals(e.filename)) {
            if(found!=null)return null;found=e;
        }
        return found;
    }
    public synchronized void bindFilename(Entry e,String filename){if(entries.get(e.id)==e)e.filename=filename;}
    public synchronized void close(String id){Entry e=entries.get(id);if(e!=null)e.closed=true;}
    public synchronized boolean sampling(long now) {
        for(Entry e:entries.values())if(!e.closed && now>=e.shutterNs &&
            (e.completedNs<0?now-e.shutterNs<60000000000L:now-e.completedNs<6500000000L))return true;
        return false;
    }
}
