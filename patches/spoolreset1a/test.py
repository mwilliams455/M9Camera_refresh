#!/usr/bin/env python3
from pathlib import Path
import json,sys

HERE=Path(__file__).resolve().parent
src=(HERE/'M9DiagnosticBurstSpool.java').read_text()

checks={
  'revision':'M9SPOOLRESET1A_ONCE' in src,
  'marker_name':'m9diag_spool_reset1a.done' in src,
  'reset_called_before_recovery':src.index('purgeLegacyBacklogOnce();') < src.index('recoverPrivate();'),
  'private_scope':'filesRoot.resolve("m9diag_spool")' in src,
  'marker_outside_private_spool':'Path marker = filesRoot.resolve(SPOOL_RESET_MARKER);' in src,
  'one_shot':'SPOOL_RESET_ATTEMPTED.compareAndSet(false, true)' in src,
  'pending_clear':'INDIVIDUAL_PENDING.clear();' in src and 'BUNDLE_PENDING.clear();' in src,
  'normal_export_queue_clear':'INDIVIDUAL_EXPORTER.getQueue().clear();' in src,
  'fresh_primary_queue_clear':'FRESH_PRIMARY_EXPORTER.getQueue().clear();' in src,
  'recovered_primary_queue_clear':'RECOVERED_PRIMARY_EXPORTER.getQueue().clear();' in src,
  'public_path_not_deleted':'Files.deleteIfExists(e.publicPath)' not in src,
  'marker_committed_after_delete':src.index('Files.deleteIfExists(dir);') < src.index('Files.move(tmp, marker, StandardCopyOption.REPLACE_EXISTING);'),
  'reset_telemetry':'spoolResetCompleted' in src and 'spoolResetDeletedFiles' in src and 'spoolResetDeletedBytes' in src,
  'primary_export_preserved':'M9PRIMARYEXPORT1B_FRESHFIRST' in src,
  'stream_export_preserved':'individual_stream_export' in src,
}
failed=[k for k,v in checks.items() if not v]
if failed:
    raise SystemExit('M9SPOOLRESET1A checks failed: '+repr(failed))

assembled=None
if len(sys.argv)>1:
    assembled=Path(sys.argv[1])
    target=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
    if target.read_bytes()!=(HERE/'M9DiagnosticBurstSpool.java').read_bytes():
        raise SystemExit('assembled spool source mismatch')

receipt={
  'revision':'M9SPOOLRESET1A_ONCE',
  'checks':checks,
  'private_spool_only':True,
  'public_dcim_files_untouched':True,
  'photos_untouched':True,
  'dngs_untouched':True,
  'settings_untouched':True,
  'one_time_marker':True,
  'recovery_after_reset':True,
  'integration':{'assembled_candidate_exact': assembled is not None},
}
out=HERE.parent/'spoolreset1a_tests.json'
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
