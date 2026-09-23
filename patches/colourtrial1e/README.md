# M9COLOURTRIAL1E — foreground diagnostic publication

This source-only trial follows 1D's memory repair and exit collector. It addresses two
concrete diagnostic-I/O problems: per-log-entry storage-provider resolution and
unconditional delayed public diagnostic exports. An Android cached-process Binder
resource kill is a process-lifecycle event; a completed renderer checkpoint must not
be described as a JPEG encoder failure. The exit record does not identify which
Binder caller caused a kill. This change requires device validation and does not
claim to resolve unrelated Java exceptions or establish why a provider died.

## Changes

* Initialize an app-private UTF-8 journal at Application startup. The logging caller
  queues bounded work without permission queries, directory lookups or SAF access.
* Publish at most one 256 KiB log chunk per five-second tick while an Activity is
  visible and camera storage is ready. The first foreground tick is after one second.
  Resolve the provider per batch and close the public stream in that batch.
* Pause diagnostic bundle/individual publication when the last Activity stops.
  Private staging continues; an already executing write may finish.
* Persist destination manifests with new private diagnostic payloads. Recover the
  newest pending payload per destination at the next process start/foreground.
  Legacy payloads without a manifest are left intact, not guessed or replayed.
* Preserve 1D's durable renderer checkpoint and Android exit-history collector.

The logger queue is limited to approximately 1 MiB of characters, with an explicit
private-log overflow count; individual entries are capped at 32,768 characters.
Only acknowledged logs older than ten days are cleaned up. If a process dies after
public append but before the local offset checkpoint, the last chunk may be repeated
on recovery. Private originals remain available. Failed diagnostic exports retry on
a later foreground transition; they do not retry continuously in the background.

No photographic pipeline, native kernel, assets, preview, JPEG/DNG writer or image
quality setting changes. `apply.py` checks the entire parent inventory and permits
only the five named files plus the new journal helper. APK version: 1.67, code 26687.

## Validation

`python3 patches/tests/colourtrial1e/run.py PhotonCamera` compiles the production
journal, logger, lifecycle monitor and diagnostic spool with counted Android fakes.
It executes exact UTF-8/restart/rollover comparisons, publication failure and retry,
visibility changes, concurrent append during a blocked export, queue bounds,
10,000 logging calls, descriptor closure, permission-error recursion prevention,
overlapping Activities with DEBUG=false, and fresh-process diagnostic recovery.
These are host behavioral tests, not an Android Binder/freezer simulation.

The dedicated workflow replays the pinned source chain, retains all parent native,
JNI, sanitizer, colour/Auto and GPU gates, runs the new I/O tests, and checks APK
signing/alignment, both ARM ABIs and packaged diagnostic markers. Device acceptance:
capture, let the render complete, background/reopen, check JPEG and diagnostic
availability, and inspect a newly collected exit report if termination recurs.

## Reference mechanisms

* [Android ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo)
  distinguishes excessive resource use, dependency death, Java and native crashes.
* [AOSP CachedAppOptimizer](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/am/CachedAppOptimizer.java)
  records the cached-process excessive-Binder kill reason.
* [AOSP ContentResolver](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/content/ContentResolver.java)
  releases provider ownership with ParcelFileDescriptorInner resources.

No private device report or photographic evidence is included in this repository.
