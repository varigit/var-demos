# Supported System on Modules

[Documentation](README.md) · [Project Overview](../README.md)

| Demo | i.MX 8M Plus | i.MX 93 | i.MX 95 |
| --- | :---: | :---: | :---: |
| NPU | VIP8000 / VX | Ethos-U65 | Neutron |
| Camera classification | ✓ | ✓ | ✓ |
| Camera detection | ✓ | ✓ | ✓ |
| Image classification / detection | ✓ | ✓ | ✓ |
| 720p / 1080p classification | ✓ | ✓ | ✓ |
| 720p / 1080p detection | ✓ | ✓ | ✓ |
| Face detection, image | ✓ | ✓ | ✓ |
| Face detection, HD / Full HD video | ✓ | ✓ | ✓ |
| Face detection, camera | ✓ | ✓ | ✓ |
| People / vehicle segmentation, image, video and camera | Experimental | Experimental | Experimental |
| Lightweight people segmentation, image, video and camera | Experimental | Experimental | Experimental |
| Video player | ✓ | ✓ | ✓ |
| OpenCL / GPU examples | ✓ | N/A | ✓ |
| Hand gestures | Experimental | N/A | N/A |

✓ means tested on the connected boards. N/A means not enabled. This does not certify
continuous operation. MX93 uses CPU-decoded MJPEG, not H.264.
Both buildings clips are available in 720p and 1080p; 720p is the default.
Face menus use the separate City Selfie clip. See
[Face Detection](face-detection.md) for its shared menus and model preparation.
MX95 camera mode requires the OV5640 to initialize successfully. Its sensor
was absent during earlier checks; later face and segmentation checks
succeeded with a working media graph. See [Validation](validation.md).

| Camera capture choice | i.MX 8M Plus | i.MX 93 | i.MX 95 |
| --- | :---: | :---: | :---: |
| VGA 640×480 | ✓ | ✓ (default) | ✓ |
| SD 720×480 | ✓ (default) | N/A | N/A |
| HD 1280×720 | ✓ | ✓ | ✓ (default) |
| Full HD 1920×1080 | ✓ | ✓ | ✓ |

These choices were checked with the connected OV5640 cameras for both
classification and detection. They are capture modes, not a promise of
30 FPS at every resolution or compatibility with other sensors.
Every camera entry in the manager, including face detection and experimental
hand gestures, opens this selector. The fixed CAMERA panel below FPS shows
capture dimensions even if processing subsequently resizes the frame.
The selector describes the configured OV5640/BSP modes, not automatic discovery
of arbitrary replacement cameras. A previously successful test does not
guarantee that a disconnected or differently configured sensor will work.

## Non-AI Demos

The video player decodes and displays media without running an AI model;
see [Video Sources](video-sources.md#video-player) for controls and codecs.
The OpenCL example uses Python `ctypes` to call `libOpenCL`, selects a GPU,
compiles a vector-addition kernel and verifies the results. It requires the
BSP's OpenCL runtime, not PyOpenCL. Kernel profiling is separate from
dispatch/readback time; it is not an NPU benchmark.
The BSP category launches supported examples already present in `/opt`.
The installer does not install, update or remove those BSP applications.

## Related Guides

- [Models and Processing Flows](models.md): what each NPU runs and how frames are processed.
- [Video Sources](video-sources.md): HD and Full HD clips and decoding differences.
- [Performance](performance.md): measured results and limitations for each SoM.
