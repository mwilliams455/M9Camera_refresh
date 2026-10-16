# M9Cam 2.92 NUMERICCLEANUP1A

Parent: verified 2.91 NOISEGUARD1A. On 2026-10-16 Malcolm reported "About the same" with a normal indoor photo. This is a provisional visual pass for the sample, not all-lens or all-mode validation. He authorized finishing the remaining warnings, verifying a build, and consolidating the tested 2.89–2.92 series into main.

This cleanup makes three existing Java narrowing conversions explicit. SmartNR's two double products are narrowed to float only after multiplication, exactly as before. The debug overlay computes descent minus ascent in float, adds y in float, then truncates the complete sum to int. Parentheses retain the original evaluation order. SmartNR has no production instantiation in this source tree; its shared shader assets are retained unchanged.

Only SmartNR.java, SurfaceViewOverViewfinder.java and app/build.gradle change. No guards, defaults, rounding rules, render parameters or new processing behavior are introduced. The M9/Monochrom image renderer, exposure and capture code, tests, native sources and assets are unchanged.

Verification:
- A host probe extracts the three actual old and new expressions and compiles them with their original double/float/int types. The complete compiled probe class bytes must match, proving the casts preserve the compiled operations and evaluation order. This is not an Android simulation.
- Exact reconstruction, complete scoped fingerprints and reverse restoration are required.
- Android CI retains the existing 266-test installer gate and 269-test broader regression gate; full-source CodeQL verifies whether the three findings clear.
- Packaging preserves all 27 native libraries and 285 assets byte for byte from the signed 2.91 APK, checks the accepted certificate, compiled resources and 16 KiB ZIP alignment.

Reconstruct: `python3 patches/numericcleanup1a/assemble.py DEST --parent VERIFIED_291` (or omit parent to reconstruct the pinned chain). Verify: `verify_source.py VERIFIED_291 DEST`. Arithmetic parity: `host_probe.py DEST VERIFIED_291`.

Android, scan, signed-installer and merge results are recorded separately after they complete. Phone testing of 2.92 remains distinct from the 2.91 feedback.
