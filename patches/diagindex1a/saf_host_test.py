"""Compile the actual Android SAF helper against a controllable provider API double."""
from pathlib import Path
import argparse, json, shutil, subprocess
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
here=Path(__file__).resolve().parent;work=a.output.resolve();src=work/'src';classes=work/'classes';classes.mkdir(parents=True,exist_ok=True)
stubs={
'android/net/Uri.java':'''package android.net;
public class Uri { public final String id; public final Uri tree; public final boolean children;
 public Uri(String id,Uri tree,boolean children){this.id=id;this.tree=tree;this.children=children;} }''',
'android/os/Bundle.java':'''package android.os; public class Bundle { public boolean loading;
public boolean getBoolean(String key,boolean fallback){return loading;} }''',
'android/database/Cursor.java':'''package android.database;
public interface Cursor extends AutoCloseable { android.os.Bundle getExtras(); int getColumnIndexOrThrow(String name); boolean moveToNext(); String getString(int column); void close(); }''',
'android/content/ContentResolver.java':'''package android.content;
public abstract class ContentResolver {
public abstract android.database.Cursor query(android.net.Uri uri,String[] cols,String sel,String[] args,String sort);
public abstract java.io.OutputStream openOutputStream(android.net.Uri uri,String mode)throws java.io.FileNotFoundException;
public abstract boolean delete(android.net.Uri uri)throws java.io.FileNotFoundException;
public abstract android.net.Uri create(android.net.Uri parent,String mime,String name)throws java.io.FileNotFoundException; }''',
'android/provider/DocumentsContract.java':'''package android.provider;
public class DocumentsContract {
public static final String EXTRA_LOADING="loading";
public static class Document { public static final String COLUMN_DOCUMENT_ID="id",COLUMN_DISPLAY_NAME="name",COLUMN_MIME_TYPE="mime",MIME_TYPE_DIR="dir"; }
public static String getDocumentId(android.net.Uri uri){return uri.id;}
public static android.net.Uri buildChildDocumentsUriUsingTree(android.net.Uri tree,String id){return new android.net.Uri(id,tree,true);}
public static android.net.Uri buildDocumentUriUsingTree(android.net.Uri tree,String id){return new android.net.Uri(id,tree,false);}
public static boolean deleteDocument(android.content.ContentResolver r,android.net.Uri u)throws java.io.FileNotFoundException{return r.delete(u);}
public static android.net.Uri createDocument(android.content.ContentResolver r,android.net.Uri p,String mime,String name)throws java.io.FileNotFoundException{return r.create(p,mime,name);} }''',
'org/json/JSONObject.java':'''package org.json; public class JSONObject {
public final java.util.Map<String,Object> values=new java.util.LinkedHashMap<>();
public JSONObject put(String key,Object value){values.put(key,value);return this;} }'''}
for n,s in stubs.items():
 t=src/n;t.parent.mkdir(parents=True,exist_ok=True);t.write_text(s)
name='com/particlesdevs/photoncamera/util/DiagnosticSafWriter1B.java';t=src/name;t.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(a.source/'app/src/main/java'/name,t)
shutil.copyfile(here/'SafWriterTest.java',src/'SafWriterTest.java')
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(classes)]+[str(f) for f in src.rglob('*.java')],check=True)
r=subprocess.run(['java','-cp',str(classes),'com.particlesdevs.photoncamera.util.SafWriterTest'],check=True,capture_output=True,text=True,timeout=30)
report=json.loads(r.stdout);report.update(androidProviderStubbed=True,productionClass='DiagnosticSafWriter1B.java',phonePerformanceUnproven=True)
(work/'SAF_HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
