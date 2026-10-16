# Segmentation Profiling

[Documentation](README.md) · [Segmentation](segmentation.md) · [Validation](validation.md)

## Recorded HD Video Profiles, October 8, 2026

The optimized runner was profiled with Buildings A HD on each connected SoM.
Each run requested ten seconds and used actual fullscreen 800x480 output.
These are short diagnostic runs, not sustained benchmarks or a fair ranking
of different codecs and temperatures.

| SoM | Processed Frames | Elapsed | FPS | Mean Invoke | Peak SoC |
| --- | ---: | ---: | ---: | ---: | ---: |
| i.MX 8M Plus | 15 | 10.33 s | 1.42 | 557.90 ms | 81 C |
| VAR-SOM-MX93 | 55 | 10.09 s | 5.48 | 89.48 ms | 60.85 C |
| DART-MX95 | 51 | 10.13 s | 5.15 | 130.46 ms | 85.62 C |

The telemetry FPS uses its own sampling interval, not necessarily exactly the
elapsed interval printed by the runner. Startup and first-frame costs also
affect short runs. MX95 is not demonstrably fastest in this configuration.

## Where the Time Goes

Mean wall-clock costs, in milliseconds, from the final diagnostic runs:

| Stage | MPlus | MX93 | MX95 |
| --- | ---: | ---: | ---: |
| Read a Ready Video Frame | 2.20 | 2.72 | 2.89 |
| Normalize RGB Input | 13.24 | 13.52 | 3.85 |
| Copy Input Tensor | 1.51 | 1.40 | 0.78 |
| Model Invoke | 557.88 | 89.45 | 130.43 |
| Validate Scores and Select Pixel Classes | 16.82 | 27.42 | 14.64 |
| Resize for Display | 0.75 | 0.85 | 5.28 |
| Blend Person and Vehicle Masks | 7.88 | 10.54 | 5.66 |
| Submit Display Frame | 0.54 | 0.92 | 0.55 |
| GUI Event Wait | 3.73 | 5.33 | 3.93 |

These are not isolated hardware-unit times. Video decoding/GPU conversion
run asynchronously; `capture_read` includes waiting, extraction and copying,
not total decoder utilization. `invoke` includes NPU partitions plus CPU
operators. Unlisted drawing, frame preprocessing and startup remain outside
this table. Nested `resize_all` measurements must not be added again.

The main MPlus limit is model invocation, not the overlay. On MX95, the
converter leaves a float/dilated CPU tail, so six Neutron partitions do not
mean the whole model runs on the NPU. The roughly 21 MiB output also costs
memory bandwidth and CPU time for pixel classification.

## Changes Kept

* MX95 uses Neutron Converter 3.1.2, matching its installed driver. No driver,
  kernel or firmware was replaced.
* XNNPACK and six CPU threads accelerate the MX95 tail. Isolated warm calls
  dropped from roughly 660 ms without XNNPACK to 80 ms with it. Video calls
  remain slower because the complete pipeline shares resources.
* Score validation and argmax run in up to four CPU row blocks. They preserve
  serial results pixel for pixel. Workers are joined before the next invoke
  so no TFLite tensor view survives across invocations.
* OpenCV lookup tables, blending and masked copying replace boolean-indexed
  color conversions. An MX95 paint check dropped from 15.68 to 5.28 ms.
* FLOAT32 normalization reuses one buffer without changing the formula.

Parallel-mask measurements improved from 42.52 to 16.82 ms on MPlus,
40.16 to 27.42 ms on MX93, and 26.51 to 14.64 ms on MX95. These comparisons
come from separate short runs and are not controlled whole-system speedups.

## Experiments Not Selected as Defaults

The alternative UINT8 BSP DeepLab still took roughly 550 ms on MPlus.
Enabling automatic CPU delegation did not materially improve its selected
VX graph. The MX93 tail gained little from XNNPACK. Neither default changed.

OpenCV argmax/checkRange were slower than NumPy on MX95. They were rejected.
Two XNNPACK threads on MX95 were slower than six in isolated checks.

Scaled EGL working frames plus a single OpenCV thread reached 5.39 FPS in
one MX95 HD check, but that combined experiment does not isolate either
change. It remains opt-in, not a certified default or a long-duration result.
Thermal policy remains enabled. A separate native-frame run reached 94.64 C;
cooling and resource contention must be considered before claiming 30 FPS.

## Reproduce a Profile

Run from `/opt/var-demos/ai-ml/camera-vision`, substituting an installed clip:

```sh
python3 profile_segmentation.py --task segmentation --video assets/videos/buildings_458687_1280x720.mp4 --seconds 10
```

Use `.avi` on MX93. Do not run competing inference demos during measurement.
The diagnostic prints `FRAME_PROFILE` JSON with call count, mean and maximum
for each stage. The first call of each stage is excluded from its mean when
there are multiple calls; this is not a complete startup exclusion. The
helper restores patched functions afterward and never changes model options,
clock settings or thermal limits. The current capture timing covers video;
camera capture through the OpenCV backend is not timed by that hook.

To improve further, the next model-level target is a lighter, more completely
quantized segmentation graph with less output data. It must still predict
people and vehicles and be independently compiled and validated on all three
NPUs. Lower source resolution alone does not shrink the fixed 513x513 model.
