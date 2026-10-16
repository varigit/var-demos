# Demo Benchmarks

[Documentation](README.md) · [Project Overview](../README.md)

These are results from our own runs of this repository's demos on the connected
SoMs, not vendor TOPS ratings or timings copied from vendor examples. No new
hardware benchmark was run as part of this documentation reorganization.
The [validation record](validation.md) explains the run conditions and history.

The same scenarios appear in each SoM table, so missing measurements are
visible rather than omitted.

**Validation:** Measured = tested with recorded timing; Functional = works,
without reported timing; Experimental = needs further validation;
Not enabled = unavailable in this suite. **N/A** means no recorded value.

**FPS** measures processed frames per second, including capture, decoding
and drawing. **Inference** measures only model execution, in milliseconds.
Lower inference time does not necessarily mean higher video FPS.

MPlus and MX93 video results below use 200 visible frames of Buildings A
(25 FPS), with accelerated 800×450 working images on an 800×480 display.
These are short runs, not sustained-load guarantees. Thermal limiting can
reduce processing to 15 FPS; details are in the [validation record](validation.md).

### i.MX 8M Plus

VIP8000 NPU. MobileNet V1 classification and SSD MobileNet V1 detection.

| Scenario | Source | Validation | Duration | FPS | Inference |
| --- | --- | --- | --- | ---: | ---: |
| Image classification | Sample image | Functional | N/A | N/A | N/A |
| Image detection | Sample image | Functional | N/A | N/A | N/A |
| 720p video classification | 720p H.264 | Measured | 8.29 s | 24.11 | 3.42 ms |
| 1080p video classification | 1080p H.264 | Measured | 8.34 s | 23.99 | 3.70 ms |
| Camera classification | Camera | Functional | N/A | N/A | N/A |
| Camera detection | 720×480 | Measured | 10 min | 15.76 | 9.00 ms |
| 720p video detection | 720p H.264 | Measured | 8.42 s | 23.74 | 9.00 ms |
| 1080p video detection | 1080p H.264 | Measured | 8.42 s | 23.75 | 9.21 ms |
| Video player | 720p H.264 | Functional | N/A | N/A | N/A |
| OpenCL / GPU examples | GPU | Functional | N/A | N/A | N/A |
| Hand gestures | Camera | Experimental | N/A | N/A | N/A |

### VAR-SOM-MX93

Ethos-U65 NPU. MobileNet V1 classification and SSD MobileNet V1 detection.

| Scenario | Source | Validation | Duration | FPS | Inference |
| --- | --- | --- | --- | ---: | ---: |
| Image classification | Sample image | Functional | N/A | N/A | N/A |
| Image detection | Sample image | Functional | N/A | N/A | N/A |
| 720p video classification | 720p MJPEG | Measured | 8.29 s | 24.11 | 4.15 ms |
| 1080p video classification | 1080p MJPEG | Measured | 8.29 s | 24.12 | 4.14 ms |
| Camera classification | 640×480 | Measured | 60 s | 29.98 | 4.12 ms |
| Camera detection | 640×480 | Measured | 60 s | 29.97 | 8.64 ms |
| 720p video detection | 720p MJPEG | Measured | 8.27 s | 24.19 | 9.33 ms |
| 1080p video detection | 1080p MJPEG | Measured | 8.35 s | 23.97 | 9.14 ms |
| Video player | 720p MJPEG | Functional | N/A | N/A | N/A |
| OpenCL / GPU examples | N/A | Not enabled | N/A | N/A | N/A |
| Hand gestures | N/A | Not enabled | N/A | N/A | N/A |

MJPEG is decoded on the CPU; this BSP has no H.264 decoder.

### DART-MX95

Neutron NPU. MobileNet V1 classification and SSD-Lite V2 detection.

| Scenario | Source | Validation | Duration | FPS | Inference |
| --- | --- | --- | --- | ---: | ---: |
| Image classification | Sample image | Functional | N/A | N/A | N/A |
| Image detection | Sample image | Functional | N/A | N/A | N/A |
| 720p video classification | 720p H.264 | Functional | N/A | N/A | N/A |
| 1080p video classification | 1080p H.264 | Functional | N/A | N/A | N/A |
| Camera classification | 1280×720 | Measured | 10 s | 5.90 | 1.40 ms |
| Camera detection | 1280×720 | Measured | 12 s | 5.83 | 3.72 ms |
| 720p video detection | 720p H.264 | Functional | N/A | N/A | N/A |
| 1080p video detection | 1080p H.264 | Functional | N/A | N/A | N/A |
| Video player | 720p H.264 | Functional | N/A | N/A | N/A |
| OpenCL / GPU examples | GPU | Functional | N/A | N/A | N/A |
| Hand gestures | N/A | Not enabled | N/A | N/A | N/A |

The previous Full HD timing was withdrawn: its GL conversion delivered
black frames. The corrected path was checked with visible detections;
representative sustained video timings must be measured again. Thermal
pauses occurred around 82 °C under the previous universal application guard;
that guard has since been replaced with the kernel-aware policy documented
in [Face Detection](face-detection.md). Camera throughput is limited by capture.
The final video path explicitly uses MMAP decoder buffers before GPU
conversion; automatic DMA_DRM import produced out-of-order image content
even with increasing timestamps. See the [validation record](validation.md).

These are existing validation results, not one standardized benchmark.
Different camera resolutions, models, codecs, durations and temperatures
prevent a fair speed ranking. Uniform-duration comparative measurements
are still pending; multi-hour stability is not certified.

## Segmentation Diagnostics

The lightweight Selfie Segmenter variant has complete HD and Full HD runs
on all three SoMs. See [People Segmentation](people-segmentation.md#measured-video-results)
for timings, source resolution, temperatures and cooling pauses.

The optimized experimental DeepLab runner's ten-second Buildings A HD checks
measured 1.42 FPS on MPlus, 5.48 on MX93 and 5.15 on MX95. These are diagnostic
runs at different temperatures/codecs, not a standardized hardware ranking.
See [Segmentation Profiling](segmentation-profiling.md) for per-stage costs,
timing scope and repeatable commands. No 25/30 FPS guarantee is implied.

[Camera and video flows](models.md#image-video-and-camera-input-flow) ·
[Model conversion](model-conversion.md)

Models and media are stored on DigitalOcean Spaces and verified with
SHA-256. No Git LFS.

## Related Guides

- [Models and Processing Flows](models.md): why model and pipeline differences matter when comparing boards.
- [Validation Record](validation.md): test conditions, historical results and thermal behavior.
- [SoM Support](som-support.md): supported demos and tested camera capture modes.
