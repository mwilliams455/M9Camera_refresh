#!/usr/bin/env python3
"""Source/contract regression for PRIMARYRECOVERY1A."""
from pathlib import Path
import hashlib,json,sys

root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path("PRIMARYRECOVERY1A_TESTS.json")
writer=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java"
spool=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java"
queue=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java"
gradle=root/"app/build.gradle"

w=writer.read_text();s=spool.read_text();q=queue.read_text();g=gradle.read_text()

checks={
  "recovery_revision":"M9PRIMARYRECOVERY1A" in w,
  "normal_async_writer_preserved":"Executors.newSingleThreadExecutor(TIMING_THREAD_FACTORY)" in w,
  "normal_public_saf_write_preserved":"SimpleStorageHelper.openOutputStreamByAbsPath(frozen.timingPath.toString())" in w,
  "exact_frozen_bytes_staged":"M9DiagnosticBurstSpool.stage(\n                    frozen.timingPath, frozen.bytes, RECOVERY_ROLE)" in w,
  "persist_failure_fallback":'stageRecovery(frozen, "public_persist_failure", t)' in w,
  "schedule_failure_fallback":'stageRecovery(frozen, "schedule_failure", t)' in w,
  "compat_role":'RECOVERY_ROLE = "primary_timing"' in w,
  "recovery_authority":'primaryTimingRecoveryAuthority", "exact_frozen_PRIMARY_bytes"' in w,
  "spool_durable_private_stage":"Files.write(privatePath, bytes)" in s,
  "spool_manifest_persist":"persistManifest(entry)" in s,
  "spool_restart_recovery":"recoverPrivate()" in s,
  "spool_eventual_export":"INDIVIDUAL_EXPORTER.schedule(() -> exportIndividual(entry)" in s,
  "render_queue_unchanged_contract":"M9PrimaryTimingWriter.freezeAndWriteAsync(" in q,
  "version":"versionName '1.84-m9primaryrecovery1a-noisecancel1a-tg1'" in g and "versionCode 26704" in g,
}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit("PRIMARYRECOVERY1A checks failed: "+", ".join(failed))

# The fallback must be exceptional only: no eager spool stage may occur before the
# public write attempt in persistFrozen.
persist=w.index("private static void persistFrozen")
public_write=w.index("SimpleStorageHelper.openOutputStreamByAbsPath",persist)
fallback=w.index('stageRecovery(frozen, "public_persist_failure", t)',public_write)
assert persist < public_write < fallback

# Two and only two production recovery triggers: scheduling failure and public
# persistence failure. Queue rejection flows through persistFrozen and therefore
# inherits the same public-write fallback without a third special path.
assert w.count("stageRecovery(frozen,") == 2

receipt={
  "revision":"M9PRIMARYRECOVERY1A",
  "checks":checks,
  "recoveryTriggerCount":w.count("stageRecovery(frozen,"),
  "normalPublicWriteFirst":True,
  "payloadAuthority":"exact_frozen_PRIMARY_bytes",
  "spoolRole":"primary_timing",
  "spoolPrivateStageBeforeEventualPublicExport":True,
  "renderQueueCallContractPreserved":True,
  "writerSha256":hashlib.sha256(writer.read_bytes()).hexdigest(),
  "spoolSha256":hashlib.sha256(spool.read_bytes()).hexdigest(),
  "queueSha256":hashlib.sha256(queue.read_bytes()).hexdigest(),
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
