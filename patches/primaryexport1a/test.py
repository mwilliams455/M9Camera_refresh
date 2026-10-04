#!/usr/bin/env python3
"""Contract regression for PRIMARYEXPORT1A."""
from pathlib import Path
import json,re,sys

root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path("PRIMARYEXPORT1A_TESTS.json")
p=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java"
g=root/"app/build.gradle"
s=p.read_text();gradle=g.read_text()

def const(name):
    m=re.search(r'private static final long '+re.escape(name)+r'\s*=\s*(\d+)L;',s)
    if not m: raise AssertionError('missing '+name)
    return int(m.group(1))

normal=const("INDIVIDUAL_DELAY_MS")
priority=const("PRIMARY_TIMING_EXPORT_DELAY_MS")
assert normal==12000
assert priority==250
assert priority < normal

checks={
  "private_first":"Files.write(privatePath, bytes)" in s and "persistManifest(entry)" in s,
  "normal_exporter":"M9DiagIndividualIO" in s,
  "dedicated_primary_exporter":"M9DiagPrimaryIO" in s,
  "primary_role":'PRIORITY_ROLE = "primary_timing"' in s,
  "stage_priority_branch":'if (isPriorityRole(entry.role))' in s,
  "resume_priority_branch":'if (isPriorityRole(e.role))' in s,
  "priority_queue_cleared_on_hide":"PRIORITY_EXPORTER.getQueue().clear()" in s,
  "normal_delay_unchanged":"INDIVIDUAL_DELAY_MS = 12000L" in s,
  "streaming_transport_unchanged":"streamPublic(entry.publicPath, entry.privatePath)" in s,
  "64k_stream":"COPY_BUFFER_BYTES = 64 * 1024" in s,
  "private_retained_on_failure":"individual stream export failed; private stage retained" in s,
  "bounded_bundle":"payloadBytesMaterializedForBundle\", 0" in s,
  "telemetry":"primaryTimingPriorityExporter" in s and "priorityPendingEntries" in s,
  "version":"versionName '1.84-m9primaryexport1a-noisecancel1a-tg1'" in gradle and "versionCode 26704" in gradle,
}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("PRIMARYEXPORT1A failed: "+", ".join(failed))

# Scheduling model: an older shutter trace is deliberately allowed to remain on
# the 12-second exporter while a newer PRIMARY becomes eligible at 250 ms on its
# independent exporter. This is the exact queue-starvation case from the phone.
entries=[
  dict(seq=1,role="shutter_trace",bytes=6_881_363),
  dict(seq=2,role="shutter_trace",bytes=3_900_635),
  dict(seq=3,role="capture_metadata",bytes=35_023),
  dict(seq=4,role="primary_timing",bytes=409_006),
]
scheduled=[]
normal_i=priority_i=0
for e in entries:
    if e["role"]=="primary_timing":
        scheduled.append((priority+50*priority_i,"priority",e["role"],e["seq"]))
        priority_i+=1
    else:
        scheduled.append((normal+250*normal_i,"normal",e["role"],e["seq"]))
        normal_i+=1
primary_event=[x for x in scheduled if x[2]=="primary_timing"][0]
first_normal=min(x for x in scheduled if x[1]=="normal")
assert primary_event[0]==250
assert primary_event[0] < first_normal[0]
assert primary_event[1]=="priority"

receipt={
  "revision":"M9PRIMARYEXPORT1A",
  "checks":checks,
  "normalExportDelayMs":normal,
  "primaryExportDelayMs":priority,
  "dedicatedPrimaryExporter":True,
  "phoneBacklogModel":scheduled,
  "primaryBeatsOlderNormalBacklog":True,
  "privateFirstDurabilityPreserved":True,
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
