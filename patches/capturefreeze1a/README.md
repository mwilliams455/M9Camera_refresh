# M9Cam 2.26 CAPTUREFREEZE1A

Child of accepted 2.25 SETTINGSSTATUS1A (`e39bc07d608eddf1023b5a715ab9c98ffd706b85`).

## Problem and fix

The deferred JPEG and DNG workers constructed `Parameters` from live camera identity,
selected sensor configuration, and global camera characteristics. Switching lenses after
RAW enqueue could make an older photo use the new lens's black level and colour calibration.
The baseline host test reproduces that behavior in the real Parameters/Converter classes.

Freeze the parameter inputs at RAW enqueue, then enter that snapshot on both workers
and on synchronous DNG fallback. Each Parameters instance gets its own sensor-array copy.
Scopes restore prior state even after an exception. A failed snapshot reports a save
failure and leaves RAW ownership with DefaultSaver.

This protects lens/settings changes after RAW enqueue. It does not claim capture-session
switches before RAW delivery, Android process death, or forced-stop recovery are solved.

## Scope

Four source changes: app version, M9PrimaryRenderQueue, Parameters input selection,
and the new M9CaptureParameters snapshot. Render equations, renderer source, native
binaries, M9 assets, exposure policy, sRGB, Save modes, saturation, UI and rearm timing
are unchanged. No stacking, HDR, device-specific gate or new RAW copy.

## Verification

- Real Parameters/Converter regression: reproduced parent contamination; same-lens
  values unchanged; switched settings/lens frozen; mutable arrays isolated; concurrent
  jobs, nested fallback and exception cleanup checked.
- Production queue: retained 11 Save-mode and 19 status cases, plus five overlap/failure
  scenarios. The new scenarios cover mixed lens/rotation/output metadata, actual queue
  saturation, synchronous DNG fallback, recovery and snapshot failure ownership.
- Retained source, RAW transport, storage, profile, saturation and Android build gates.
- Packaging reuses all 23 accepted native binaries and checks the existing signing certificate.

## Phone acceptance

Keep 2.25 as the accepted fallback until this test passes. Use JPEG + DNG, then take
six photos as quickly as the shutter allows, alternating main/ultrawide/tele after
each capture rearms. Rotate for a few shots. During saving, return Home or lock the
screen, then reopen. Check six JPEGs and six DNGs, no duplicates, correct orientation
and lens appearance, and no stuck save counter. Repeat briefly with JPEG-only and RAW-only.
This is a handset acceptance test; host adapters cannot reproduce vendor Camera2 behavior.
