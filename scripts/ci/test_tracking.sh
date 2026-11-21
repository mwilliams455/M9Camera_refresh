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
  patches/autosubject1a/host/AutomaticSubjectSelectionTest.java
)
if [[ -f "$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/SubjectFrame.java" ]]; then
  tests+=(patches/autosubject1b/host/SubjectFrameTest.java)
fi
if [[ -f "$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/PersonRecoveryInput.java" ]]; then
  tests+=(patches/autosubject1c/host/PersonRecoveryTest.java)
fi
selection="$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/AutomaticSubjectSelection.java"
if [[ -f "$selection" ]] && grep -Fq 'checkOtherPeople(' "$selection"; then
  tests+=(patches/autoreframe1a/host/PersonReframeTest.java)
fi
if [[ -f "$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/PetDetailInput.java" ]]; then
  tests+=(patches/petdetail1a/host/PetDetailInputTest.java)
fi
if [[ -f "$source_tree/app/src/test/java/com/particlesdevs/photoncamera/ui/camera/AutomaticSubjectAfRetryTest.java" ]]; then
  tests+=(patches/petcontinuity1a/host/PetContinuityTest.java)
fi
animal_policy="$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/AnimalEyeTargetPolicy.java"
if [[ -f "$animal_policy" ]] && grep -Fq 'supportsAnimal(' "$animal_policy"; then
  tests+=(patches/petacquisition1a/host/PetAcquisitionTest.java)
fi
if [[ -f "$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/SceneHeads.java" ]]; then
  tests+=(patches/headpair1a/host/SceneHeadsTest.java)
fi
if [[ -f "$source_tree/app/src/main/java/com/particlesdevs/photoncamera/control/subject/LargePetAcquisition.java" ]]; then
  tests+=(patches/widepet1a/host/LargePetAcquisitionTest.java)
fi
javac -Xlint:all -sourcepath "$source_tree/app/src/main/java" -d "$classes" "${tests[@]}"
for suite in "${tests[@]}"; do
  java -ea -cp "$classes" "$(basename "$suite" .java)"
done
