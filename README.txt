M9Cam v0.7ZR PRIMARY2.5 PERF3I EXPOSUREAUDIT1A

Diagnostic-only derivative of the recovered/device-validated v0.7ZQ PERF3I branch.

Exposure investigation goal:
- Audit why reported/captured ISO can appear higher than expected.
- Separate Photon shutter-priority allocation from FB1 backlight assistance and the M9 motion cap.
- Preserve dense-shadow / backlight evidence before changing any exposure policy.
- Tie diagnostics to the actual step-0 primary capture so GenerateExpoPair(-1, ...) preflight calls cannot overwrite the exposure record.

New _M9.json section:
- m9ExposureAudit
- preview Camera2 AE ISO/shutter and energy
- Photon-only normalized/system-equivalent allocation
- FB1 requested/applied EV plus feedback-only counterfactual
- M9 motion cap and captureMotionScore
- final normalized allocation
- denormalized allocator request written to CaptureRequest.Builder
- observed Camera2 request/result parity
- derived ISO/EV deltas including motionIsoPenaltyStopsVsFeedbackOnly and camera2RequestVsAllocatorEnergyEv

No photographic or exposure tuning in this branch:
- PERF3I BITMAPDIRECT1A unchanged.
- CVDIRECT1A and ORIENTFUSE8A unchanged.
- 12 MP JPEG quality 95 unchanged.
- Frozen R3.8 H25/TG1, Cobalt calibration, M9 bridge, TC20, SAT3 M06/M07, curve02 and exact BT.601 4:2:2 unchanged.
- FB1 thresholds and maximum correction unchanged.
- M9 motion thresholds/caps unchanged.
- Photon exposure arithmetic unchanged.

First device test:
1. bright outdoor/static scene;
2. normal indoor/static scene;
3. genuinely backlit indoor subject.

For each capture retain the JPEG, _M9.json and _M9_PRIMARY.json. Note the ISO shown in the camera UI before capture if practical.
