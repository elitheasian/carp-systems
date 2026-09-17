# 0005: Edge deployment formats and mobile framework

**Status:** Proposed, needs a team decision before M5

## Context

The same models must run on iOS, Android and Raspberry Pi, in real time, with unreliable network
at the ponds.

## Proposal

- **Canonical export: ONNX.** From ONNX, produce:
  - **Pi:** ONNX Runtime (CPU) as baseline, Hailo HEF if an AI HAT+ is used.
  - **Phones:** TFLite/LiteRT, one format for both platforms, with GPU/Core ML delegates.
- **Mobile framework:** React Native (Expo dev build) with `react-native-vision-camera` frame
  processors and `react-native-fast-tflite`. One codebase for both platforms, with real-time frame
  access.
- **Gallery on device:** phones download the versioned gallery (float16 vectors + fish IDs +
  listing URLs) and search locally.

## Alternatives

- **Flutter** + `tflite_flutter`: also cross-platform; pick it if the team knows Dart better.
- **Native Swift + Kotlin**: best performance and camera control, but two apps to build.
- **Server-side inference only**: simplest app, but laggy live preview and useless without signal.

## Open questions

- Which framework does the team already know?
- iOS only, Android only, or both for the demo?
