# Hardware

Starting points to validate in M4/M5. Measure before buying in quantity.

## Pond node

| Part | Suggestion | Why |
|---|---|---|
| Computer | Raspberry Pi 5 (8 GB) | Enough CPU for a small detector + embedder at a few fps |
| Accelerator (optional) | Raspberry Pi AI HAT+ (Hailo) | Real-time detection with headroom; needs models compiled to HEF |
| Camera | Camera Module 3 (wide) or HQ Camera with a wide lens | Wide field of view from a practical mounting height |
| Filter | Circular polarizer | Cuts surface glare, the biggest enemy of pattern matching |
| Power / network | PoE HAT + outdoor PoE switch | One cable per pond |
| Enclosure | IP65 box with a clear window and a sun/rain hood | Outdoor, wet, hot |

### Mounting

- Camera straight down over the pond, like the listing photos.
- Height sets coverage vs. detail: a fish should span at least ~150 px along its body for
  reliable identification. Test with the smallest fish kept in that pond.
- Avoid pointing at the sun's reflection. Shade the water in view if possible.
- Log capture settings. Auto-exposure hunting on ripples can be worse than fixed exposure.

### Software on the Pi

- Raspberry Pi OS (64-bit), Python 3.11+, `pip install -e '.[vision]'`.
- Camera via picamera2 (preferred) or OpenCV.
- Models as ONNX (CPU baseline) or HEF (AI HAT+).
- Run as a systemd service with the spool directory on persistent storage.

## Phones

- On-device models as TFLite/LiteRT, with GPU or Core ML delegates where available.
- Target: smooth live preview with detection and classification. Identification runs once per
  tap or per stable detection, not every frame.
- Test on at least one older mid-range Android phone, not just recent iPhones.
