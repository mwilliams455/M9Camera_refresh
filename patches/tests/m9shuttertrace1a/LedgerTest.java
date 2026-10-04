import com.particlesdevs.photoncamera.m9.preview.M9TraceLedger1A;
public class LedgerTest {
 static int n;static void check(boolean v,String s){n++;if(!v)throw new AssertionError(s);}
 public static void main(String[] a){
  M9TraceLedger1A l=new M9TraceLedger1A(2);
  M9TraceLedger1A.Entry first=l.begin("one","0-4",1000000000L),second=l.begin("two","0-4",2000000000L);
  check(first!=null&&second!=null,"successive captures independent");
  check(l.begin("three","0-4",3)==null,"active captures never evicted");
  check(l.begin("one","0-4",4)==null,"duplicate capture rejected");
  l.complete("two",200,201,3000000000L);l.complete("one",100,101,4000000000L);
  check(l.bySensor(100)==first&&l.bySensor(101)==first,"logical and physical joins");
  check(l.bySensor(200)==second&&l.bySensor(999)==null&&l.bySensor(-1)==null,"unknown timestamp not latest capture");
  l.bindFilename(first,"one.jpg");l.bindFilename(second,"two.jpg");
  check(l.byFilename("two.jpg")==second&&l.byFilename("missing.jpg")==null,"gallery exact filename");
  check(l.sampling(5000000000L),"sampling after completed shutter");
  check(!l.sampling(11000000000L),"sampling ends after completion window");
  l.complete("two",100,200,3);check(l.bySensor(100)==null,"ambiguous timestamp fails closed");
  l.bindFilename(second,"one.jpg");check(l.byFilename("one.jpg")==null,"ambiguous filename fails closed");
  l.close("one");check(l.begin("three","5",12000000000L)!=null&&l.get("one")==null,"bounded completed-capture eviction");
  check(l.bySensor(101)==null,"evicted capture cannot silently join");
  check(l.sampling(13000000000L),"long exposure waits for still completion");
  check(!l.sampling(73000000000L),"missing completion bounded by timeout");
  System.out.println("M9SHUTTERTRACE1A LEDGER PASS: "+n+" assertions");
 }
}
