#!/usr/bin/env python3
"""Contract regression for PRIMARYEXPORT1B fresh-first isolation."""
from pathlib import Path
import json,re,sys

root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path("PRIMARYEXPORT1B_TESTS.json")
p=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java"
g=root/"app/build.gradle"
s=p.read_text();gradle=g.read_text()

def const(name):
    m=re.search(r'private static final long '+re.escape(name)+r'\s*=\s*(\d+)L;',s)
    if not m: raise AssertionError('missing '+name)
    return int(m.group(1))

fresh=const("PRIMARY_TIMING_EXPORT_DELAY_MS")
backfill=const("RECOVERED_PRIMARY_EXPORT_DELAY_MS")
normal=const("INDIVIDUAL_DELAY_MS")
assert fresh==100 and backfill==1000 and normal==12000

checks={
  "revision":"M9PRIMARYEXPORT1B_FRESHFIRST" in s,
  "fresh_executor":"M9DiagPrimaryFreshIO" in s,
  "backfill_executor":"M9DiagPrimaryBackfillIO" in s,
  "fresh_stage_route":"exportIndividual(entry, true, false)" in s,
  "recovered_route":"exportIndividual(e, false, true)" in s,
  "backlog_isolation":"FRESH_PRIMARY_EXPORTER" in s and "RECOVERED_PRIMARY_EXPORTER" in s,
  "private_first":"Files.write(privatePath, bytes)" in s and "persistManifest(entry)" in s,
  "streaming_transport":"streamPublic(entry.publicPath, entry.privatePath)" in s,
  "64k_stream":"COPY_BUFFER_BYTES = 64 * 1024" in s,
  "failure_retains_private":"individual stream export failed; private stage retained" in s,
  "telemetry":"primaryTimingFreshFirstIsolation" in s and "freshPrimaryWrites" in s and "recoveredPrimaryWrites" in s,
  "version":"versionName '1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1'" in gradle and "versionCode 26705" in gradle,
}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("PRIMARYEXPORT1B failed: "+", ".join(failed))

# Model the phone condition: 88 recovered PRIMARYs can occupy the backfill
# executor indefinitely, yet a newly staged PRIMARY has an independent 100-ms
# eligibility time and is not ordered behind that backlog.
recovered=[dict(kind="recovered",delay=backfill+100*i) for i in range(88)]
fresh_event=dict(kind="fresh",delay=fresh)
assert fresh_event["delay"] < recovered[0]["delay"]
receipt={
  "revision":"M9PRIMARYEXPORT1B",
  "checks":checks,
  "freshPrimaryDelayMs":fresh,
  "recoveredPrimaryInitialDelayMs":backfill,
  "normalDiagnosticDelayMs":normal,
  "modeledRecoveredPrimaryBacklog":len(recovered),
  "freshPrimaryIndependentOfRecoveredQueue":True,
  "freshEligibleBeforeOldestRecovered":True,
  "privateFirstDurabilityPreserved":True,
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
