#!/usr/bin/env bash
# Compile the Android-independent policy tests against the assembled app.
set -euo pipefail
source_tree=$(realpath "$1")
classes=$(mktemp -d)
trap 'rm -rf "$classes"' EXIT
tests=(
  patches/focusanimaleye1a/host/AnimalEyeTargetPolicyHostTest.java
  patches/focusanimal1b/host/PetTargetPolicyHostTest.java
  patches/focusanimaleye1b/host/AnimalSimccDecoderHostTest.java
  patches/focusanimal1c/host/PetPreviewRetryPolicyHostTest.java
  patches/focussubject1a/host/HumanEyeAdmissionGateHostTest.java
  patches/autoeye1a/host/AutoEyeFocusPolicyHostTest.java
  patches/autoeye1a/host/ProfileEyeAdmissionGateHostTest.java
  patches/focuscontrol1a/host/FocusControlPolicyTest.java
  patches/aftracking2a/host/ArbitraryAfUpdateGateTest.java
  patches/aftracking3a/host/PatchTracker3ATest.java
  patches/aftracking3a/host/TrackingFrameDecision3ATest.java
  patches/aftracking3b/host/SubjectAnchorPolicyTest.java
  patches/aftracking5a/host/SubjectAppearanceDescriptorTest.java
  patches/aftracking5a/host/SubjectIdentityPolicyTest.java
  patches/aftracking4a/host/FocusMotionPredictorTest.java
  patches/aftracking4a/host/TrackingTogglePolicyTest.java
  patches/aftracking5a/host/TrackingIdentityToggleTest.java
  patches/focuscontrol1a/host/PhysicalSourceEvidence1ATest.java
  patches/focusoverlay1a/host/FocusTickGeometryHostTest.java
  patches/focusoverlay1b/host/EyeMarkerDisplayGeometryHostTest.java
  patches/trackingdefault1a/host/TrackingDefaultPolicyHostTest.java
  patches/trackingrecovery1a/host/SubjectRecoveryPolicyTest.java
)
javac -Xlint:all -sourcepath "$source_tree/app/src/main/java" -d "$classes" "${tests[@]}"
for suite in "${tests[@]}"; do
  java -ea -cp "$classes" "$(basename "$suite" .java)"
done
