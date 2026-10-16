# Cross-board presentation and playback validation

[Documentation](README.md) · [Project Overview](../README.md)

This is a chronological record: older failures, counts and menus describe
the revisions tested then, not necessarily the current implementation.
Classification, object detection and DeepLab use Buildings A/B; face detection
and lightweight people segmentation use City Selfie, each in HD and Full HD.
See [SoM Support](som-support.md) for current availability.

## Functional Retest, October 16, 2026

Retained local `results.json` records contain 148 passing scenarios:

| Processor | Scenarios |
| --- | ---: |
| i.MX 8M Plus | 59 |
| i.MX 93 | 40 |
| i.MX 95 | 49 |

These cover the installed catalog, including AI images, video choices,
configured camera modes, player and available GPU/BSP demos. MX95 face-camera
checks completed with a working sensor; the earlier probe failure below is
historical. The records include process status and display telemetry, not
labeled accuracy scores or an exhaustive visual audit of every frame.

Seven MPlus cases with low frame counts were repeated for longer after
cooldown. All repeats passed with 37 or more processed frames; thermal pauses
still occurred. DeepLab repeats processed roughly 0.8–1 FPS on that setup.
Separate longer Selfie Segmenter HD checks completed on MX93 and MX95.
Do not turn these bounded, mixed-temperature checks into a comparative
benchmark or a guarantee of sustained real-time processing.

Raw logs, screenshots and result JSON were retained locally under
`/tmp/edge-ai-validation-20261016`, outside the public repository. This path
is a review artifact, not a permanent public download or an installation
requirement. The documentation review does not constitute a new hardware run.

## Earlier Presentation Checks

Requested checks for i.MX 8M Plus, VAR-SOM-MX93 and DART-MX95:

- Use the same wording for shared demos, followed by the actual NPU name.
- Show the same eight video samples in the same order on every board.
- Keep board-specific codecs and models; never imply identical capabilities.
- Use the MPlus colors, typography, panels and labels for every vision demo.
- Anchor inference, FPS, model and temperature panels to fixed screen positions.
- Keep classification scores in fixed columns and boxes attached to objects.
- Preserve readability on the 800x480 displays for HD and Full HD sources.
- Investigate reported backward/forward motion in MX95 video inference.
- Validate frame ordering and ownership, not only frame count or inference time.
- Keep thermal protections enabled and distinguish smoothness from correctness.

### Completed checks at that revision

The same six primary menu entries appear first on every board: classification
(image, video, camera), then detection (image, video, camera). The actual
NPU is named VIP8000, Ethos-U65 or Neutron. Optional extras follow.

| Check | i.MX 8M Plus | VAR-SOM-MX93 | DART-MX95 |
| --- | --- | --- | --- |
| Image classification / detection displayed | Passed | Passed | Passed |
| 720p / 1080p classification and detection displayed | Passed | Passed | Passed |
| VGA / HD / Full HD camera classification and detection | Passed | Passed | Passed |
| Fixed 800×480 panels and readable labels | Passed | Passed | Passed |
| Identical eight-video menus and manifest coverage | Passed | Passed | Passed |
| Additional SD 720×480 camera mode | Passed | Not offered | Not offered |
| Hand sample with shared overlay | Passed, experimental | Not offered | Not offered |

Graphical checks captured annotated frames, verified display dimensions and
non-black reference imagery, and exercised shutdown with Esc. They are short
functional checks, not sustained FPS benchmarks: saving screenshots on each
frame adds overhead. Do not substitute these rates into performance tables.
MPlus warmup now happens before measured inference, matching the other boards.
An explicit BGR camera caps filter fixes grayscale negotiation at larger
capture resolutions. The root suite forwards video-source and camera-mode
metadata to the shared launcher; direct CLI listing was checked on all boards.

## MX95 forward/backward playback

The problem was reproduced: the automatic hardware decoder / DMA_DRM / EGL
path supplied increasing PTS but visually reordered images. Matching 245
captured frames to an independent CPU-decoded reference exposed 93 backward
transitions in one run. Removing B-frames alone reduced the problem but still
left stale images around GOP boundaries; this alone was not accepted as a fix.

The final pipeline uses `qtdemux ! h264parse ! v4l2h264dec capture-io-mode=2 !
video/x-raw,format=NV12` before GPU upload. In the same 720p comparison,
245 captured frames matched reference frames 0–244 in order, with **zero
backward transitions**. The installed samples use SHA-256-verified
`media/ordered-v2/` compatibility copies; originals are retained externally.
HD and Full HD classification/detection were retested with the final path.

The GTK player's hardware decoder also selects MMAP on MX95. Its integration
check passed play, pause, seeking, stop, restart, fullscreen toggling and close,
with decoded non-black, opaque frames. This does not certify all arbitrary
user files, long-term stability or absence of thermal pauses.

## Model reproduction

Vela 3.12.0 recompilation of both MPlus source models on MX93 reproduced the
installed artifacts byte-for-byte. MobileNet input/output are UINT8;
SSD input is UINT8 with FLOAT32 detection outputs. MX95 uses separate
NXP UINT8-input/FLOAT32-output compiled artifacts; no current-SDK custom
Neutron conversion or equal-weight claim is made. Details and SHA-256 values
are in [the conversion guide](model-conversion.md).

## Installer and removal

The full candidate installer was run on all three boards in disposable
prefixes, preserving their active `/opt/var-demos` installations. All installed
AI assets were SHA-256 checked: 22 manifest entries on MPlus, 15 on MX93 and
16 on MX95 (shared assets can occur in more than one demo manifest).
Installed menu listing and the shared overlay module were checked too.

Removal passed on every board with no asset, executable or symlink left
in the disposable prefixes. Installation metadata now records a custom
command directory so `var-demos --uninstall` removes that launcher too;
older empty markers retain the `/usr/bin` default. Only the temporary
test installations were removed; the active board installations were kept.

Local regression suites: 77 AI tests and 44 suite/installer/documentation
tests passed. Functional board checks above are additional to those suites.

## Video Processing Optimization, 2026-10-07

The user-provided Buildings A source is 25 FPS, not 30 FPS. Native-frame
profiling found CPU resize and display/event work outside the roughly 9 ms
SSD inference. Changing OpenCV to one thread did not improve throughput.
Nearest-neighbor preview was investigated but not selected; BSP accelerated
conversion was used instead, preserving the preview's aspect ratio.

The file is still decoded at 720p or 1080p. G2D (MPlus) and PXP (MX93)
convert it to an 800x450 working image before CPU model resizing and overlay
drawing. Model dimensions, weights and data types are unchanged, but this
adds a resampling step: prediction equivalence has not been established.
`VAR_AI_NATIVE_FRAMES=1` preserves the older native-frame preprocessing.

All recorded runs below displayed 200 annotated frames in fullscreen at
800x480, with a non-black first-frame check. One first-frame screenshot was
saved per run. Rates use the demo's processing interval, excluding model
warmup. Runs used temporary source trees and the installed verified assets.

| SoM | Task | Source | Processing FPS | Mean Inference |
| --- | --- | --- | ---: | ---: |
| MPlus | Classification | 720p H.264 | 24.11 | 3.42 ms |
| MPlus | Classification | 1080p H.264 | 23.99 | 3.70 ms |
| MPlus | Detection | 720p H.264 | 23.74 | 9.00 ms |
| MPlus | Detection | 1080p H.264 | 23.75 | 9.21 ms |
| MX93 | Classification | 720p MJPEG | 24.11 | 4.15 ms |
| MX93 | Classification | 1080p MJPEG | 24.12 | 4.14 ms |
| MX93 | Detection | 720p MJPEG | 24.19 | 9.33 ms |
| MX93 | Detection | 1080p MJPEG | 23.97 | 9.14 ms |

Repeated warmed MPlus detection runs gave 15.06 and 16.82 FPS, while cooler
retests reached 23.74/23.75 FPS. Its thermal pacing uses the hottest SoC/CPU
zone, which can be hotter than the footer sensor. This is not a guarantee of
24 FPS under prolonged load. The HD-specific extra runner separately gave
20.23 FPS at 720p and is not the common-menu detection measurement above.

Clocked files no longer have an additional cold-board rate limiter. Hot-board
15 FPS limiting, 82 C pause and below-78 C resume remained at that revision.
The newer policy is recorded below. MX93/MX95 GI capture
pauses the decoder during cooling; the MPlus HD-specific runner does too.
The common MPlus OpenCV backend still has inference-only cooling.
Padded buffer stride, offset and bottom rows are now handled explicitly.

MX95 remained around 81-86 C even without an inference demo, so the new
scaled EGL path could not be safely performance-validated. It remains
experimental (`VAR_AI_ACCELERATED_VIDEO=1`); the default retains the earlier
validated native-frame/MMAP EGL path. A five-second hot-board startup check
confirmed cooling occurs before model/decoder initialization, with zero
inferences and no decoder started. Retesting performance and frame order
with adequate cooling is still required; no new MX95 FPS is claimed.

Local regression: 84 AI tests and 48 suite tests passed before publication.

## Documentation and Detection Overlay Update, 2026-10-07

The guides were reorganized under `docs/`, retaining historical measurement
records. Relative links and heading anchors were checked. Per-NPU guides now
separate model requirements, libraries, startup, classification, detection
and software/hardware responsibilities.

Detection's FPS and inference values use a shared pixel-aligned numeric column.
A fixed panel below FPS displays original stream dimensions, not the scaled
working image, display size or model tensor size. Stream metadata was checked
for Buildings A at 1280x720 and 1920x1080 on all three connected SoMs using
temporary review modules. The panel rendered in memory on each target, and a
clean decoded MX93 frame was inspected for readability. Preview timing values
were illustrative layout values, not new performance measurements.

Regression: 98 AI tests and 51 suite tests passed. This update does not establish
new sustained FPS, prediction equivalence or cooled MX95 inference performance.

## Face Detection and Camera Presentation Update, 2026-10-07

UltraFace Slim was exercised with actual NPU delegates on all three connected
SoMs. The reference image produced 14 detections on each target. City Selfie
(user clip 1117992) completed at both 1280x720 and 1920x1080 with visible
fullscreen output and detected faces. These are single-run measurements,
not sustained-performance guarantees:

| SoM | HD FPS / inference | Full HD FPS / inference | Peak SoC temperature, HD / Full HD |
| --- | --- | --- | --- |
| i.MX 8M Plus | 16.36 / 5.56 ms | 12.53 / 5.66 ms | 80 / 81 C |
| VAR-SOM-MX93 | 23.07 / 7.11 ms | 22.90 / 7.23 ms | 62.35 / 65.35 C |
| DART-MX95 | 24.87 / 4.25 ms | 19.88 / 4.21 ms | 83 / 88.12 C |

The source is 25 FPS, not 30 FPS. MPlus reached application thermal pacing
during these runs. MX95 completed without entering Cooling under the newer
policy, but its default Full HD conversion path still costs throughput.
The experimental scaled MX95 path remains opt-in and is not certified here.

Thermal pacing now reads recognized SoC zones' kernel trip points without
changing them. The tested application warm/pause/resume thresholds were
80/82/78 C on MPlus, 88/90/86 C on MX93 and 93/95/91 C on MX95. These are
conservative application choices, not manufacturer temperature ratings.
Missing policy data retains the 80/82/78 C fallback; reported hardware
throttling still pauses inference. Regression tests cover these cases.

Face camera capture ran in VGA, HD and Full HD on MPlus and MX93. Accelerated
conversion uses G2D and PXP respectively. The final CAMERA badge was checked
while actually displaying 140 SD frames on MPlus and 130 Full HD frames on
MX93: every frame showed the capture dimensions, independent of the 800x480
display and smaller intermediate working frame. All camera launchers now
offer their configured SoM resolution choices, including hand gestures.
Additional live checks covered MPlus classification at VGA (148 visible
frames), object detection at SD (100), and gestures at HD (37), plus MX93
classification at VGA (140) and object detection at HD (29). Each displayed
frame called the CAMERA badge with the selected capture dimensions.
The gesture test exposed unconstrained pixel-format negotiation; capture
now explicitly requests BGR after conversion. Its successful repeat is a
functional check, not a 30 FPS claim for the experimental gesture pipeline.

MX95 camera validation is blocked by OV5640 probe/power errors (-5) and an
absent media graph. Image/video success is not camera validation. Reconnect
or inspect the camera with the board powered off, then retest capture.

Published face assets were downloaded and SHA-256 checked on the targets.
An isolated MPlus face installation using the normal installer completed
without modifying `/opt/var-demos` or its existing launcher.
Local regression: 116 AI tests and 51 suite tests passed.
Model origins, preparation, video transformations and limitations are in
[Face Detection](face-detection.md) and [Video Sources](video-sources.md).

## Segmentation, Branding and Camera Preflight, 2026-10-08

DeepLabV3-MobileNetV2 semantic masks were checked with visible 800x480
fullscreen output on MPlus and MX93. Both use the same pinned source model;
MX93 uses a locally reproduced Vela 3.12.0 / Ethos-U65-256 artifact.
Input/output boundary tensors were measured as FLOAT32, with a quantized
internal network. NPU delegation is checked without an automatic CPU delegate.

The City Selfie sample frame produced a person mask on both. Buildings A
produced both people and vehicle masks at HD and Full HD. Final short checks:

| SoM | Input | Processed Frames | FPS | Mean Model Invoke |
| --- | --- | ---: | ---: | ---: |
| MPlus | Buildings A HD | 8 | 1.17 | 557.99 ms |
| MPlus | Buildings A Full HD, earlier owned-output path | 9 | 1.30 | 558.33 ms |
| MPlus | Camera VGA | 8 | 1.21 | 556.77 ms |
| MX93 | Buildings A HD | 26 | 4.75 | 89.48 ms |
| MX93 | Buildings A Full HD | 23 | 3.76 | 90.70 ms |
| MX93 | Camera HD | 30 | 5.51 | 88.90 ms |

These are short functional runs, not sustained benchmarks or a 30 FPS claim.
Final complete Buildings A HD runs used the published model assets:

| SoM | Processed Frames | Elapsed | FPS | Mean Model Invoke | Peak SoC |
| --- | ---: | ---: | ---: | ---: | ---: |
| MPlus | 51 | 44.17 s | 1.15 | 557.11 ms | 82 C |
| MX93 | 168 | 34.43 s | 4.89 | 89.57 ms | 62.35 C |

MPlus entered application cooling and resumed before reaching the end of the
clip. Its elapsed time and FPS include that pause. MX93 completed without
cooling. These remain single-run measurements, not long-duration guarantees.
The source videos remain the user's original Buildings clips or their existing
MX93 MJPEG copies. Masks are predictions; no pixel-accuracy guarantee is given.
Large score tensors now use short-lived views to avoid output copies and
duplicate validation scans; only independent class masks leave that scope.

MX95's official SDK 3.1.3 DeepLab trial did invoke but reported microcode
mismatches against driver 3.1.2. It is deliberately not offered in the menu.
This is a software-version issue, not evidence of inadequate NPU hardware.
No driver or firmware was changed. See [Segmentation](segmentation.md) for
conversion provenance, licenses, tensor contracts and CPU/NPU flow.

Camera inputs now check native capture nodes and, on MX93/MX95, the connected
sensor in the media graph before launching a model. Existing MX95 ISI nodes
without a sensor are rejected as unavailable. Direct face-camera execution on
the disconnected MX95 returned a short notice, no traceback, and zero model
invocations. Menu regression verifies return without opening the resolution
selector or starting a child process.

The shared inference layout uses the player's official logo, a device-tree
SoM label and one left-aligned value column for inference, FPS and dimensions.
The logo is installed with each current AI demo and alpha-composited from a
cached resized asset. The player also names the SoM. Existing external NXP BSP
executables are not rewritten; terminal-only OpenCL remains a console demo.

The MPlus module installation was rechecked in a temporary prefix using public,
checksum-verified models, sample frame, license files and logo. The published
MX93 Vela artifact was separately fetched and verified. No `/opt` installation
or existing menu process was overwritten. Local regression: 131 AI tests and
53 suite tests passed.
The MX93 player also passed the on-board playback, pause, seek, stop, restart,
close and fullscreen checks with the official logo and SoM label.

## MX95 Segmentation and Three-SoM Profiling, 2026-10-08

The user supplied Neutron SDK 3.1.2. The same pinned DeepLab source was compiled
locally for MX95 and delegated six Neutron partitions without a microcode
mismatch. No installed driver or firmware was replaced. The new public asset
was fetched and its SHA-256 matched the manifest.

MX95 displayed a person mask on the sample image (18.68% viewport coverage),
and people/vehicle masks during Buildings A HD and Full HD. An initial full
HD clip completed with 169 processed frames, 4.93 FPS, 131.17 ms mean invoke
and 89.01 C peak. A twelve-second Full HD check processed 40 frames at 3.41 FPS,
205.23 ms mean invoke and 86.07 C peak. These preceded the final parallel-mask
optimization and are not sustained-performance guarantees.

The camera media graph became available again during this validation;
the earlier absent-sensor check remains historical, not its current state.
A bounded HD camera check displayed 17 frames in 6.20 seconds, with 2.68 FPS,
271.17 ms mean invoke and 82.62 C peak. That camera scene contained neither
target category, so this validates capture/display, not segmentation accuracy.

The optimized shared runner completed ten-second HD profiles on all three
SoMs with repeated invocations and no retained-tensor-view errors. It measured
1.42 FPS on MPlus, 5.48 on MX93 and 5.15 on MX95. The same model source does not
make these different-temperature/codec runs a controlled speed ranking.
See [Segmentation Profiling](segmentation-profiling.md) for stage costs,
experiments kept/rejected and commands to reproduce the measurements.
Local regression: 134 AI tests and 53 suite tests passed. The distributed
profiling helper also ran on MX95 and emitted per-stage JSON successfully.

## Lightweight People Segmentation and Task Menus

Selfie Segmenter landscape was checked on the existing MPlus 6.6.144,
MX93 6.6.138 and MX95 6.18.20 images. The sample portrait produced a foreground
mask on all three (about 24% viewport coverage). Complete HD/Full HD City
Selfie runs completed; [recorded timings](people-segmentation.md#measured-video-results)
include thermal pauses rather than hiding them.

Bounded HD camera tests also completed on all three with 800x480 fullscreen
output: MPlus 76 displayed frames, MX93 146 and MX95 31. Mean invocation times
were 4.41, 2.76 and 4.46 ms respectively. These short checks validate camera
capture, repeated inference and display, not an accuracy dataset or sustained
camera benchmark. MX95 camera throughput remained low despite fast inference.

Public downloads of all three model artifacts matched the manifest SHA-256.
Task/input menus share one implementation across SoMs; resolution/video
selectors and camera preflight remain active. The menu helper is included in
both suite and standalone AI installations, including the removal path.

## Complete Demo Smoke Checks

Final checks on October 8, 2026 passed all 86 scenarios:

| SoM | Installed Kernel | Passed Scenarios |
| --- | --- | ---: |
| i.MX 8M Plus | 6.6.144 | 33 |
| VAR-SOM-MX93 | 6.6.138 | 22 |
| DART-MX95 | 6.18.20 | 31 |

Local regression checks passed 147 AI tests and 53 suite tests.

The published installer was run on all three connected SoMs. The installed
catalog was exercised sequentially per SoM: classification, object detection,
face detection, DeepLab segmentation and lightweight people segmentation,
each with an image, HD video, Full HD video and an HD camera capture.
The player checks exercised play, pause, seek, stop, restart, fullscreen and
close. GPU vector addition and the available image-provided graphics demos
were also executed on MPlus/MX95; hand gestures were exercised on MPlus.

These are bounded functional checks with real display output, not sustained
benchmarks or segmentation/detection accuracy certification. The automated
runner closes AI views after approximately five displayed seconds. BSP demos
use their native `--ExitAfterFrame 120` option; an initial duration-format
error in the test command was corrected before the successful rerun.

Visual inspection exposed a missing VIDEO panel in classification. The panel
now reports the source dimensions on all three SoMs. The opening white window
was addressed by preparing the first frame, fullscreen state and decoration
settings in a shared GTK presenter before mapping. The MPlus GTK backend
requires Wayland; automatic socket selection was added and affected cases
were repeated. The player's initial fullscreen request also precedes mapping.

## Related Guides

- [Performance](performance.md): the current per-SoM measurement tables.
- [Models and Processing Flows](models.md): model identities and CPU/NPU responsibilities.
- [Video Sources](video-sources.md): the current curated clip catalog and format preparation.
