# Documentation

[Project Overview](../README.md)

Start with SoM support, then follow the model diagrams to understand how
images, videos and camera frames are processed.

These guides describe this suite, not every capability of the processors.
Catalogs and asset manifests define the installed demos and exact artifacts.
Recorded measurements apply only to their stated software and test conditions;
they are not performance promises for a different BSP or camera.

## Supported System on Modules

| SoM | Photo | CPU | GPU / Image Engine | NPU |
| --- | :---: | --- | --- | --- |
| [DART-MX8M-PLUS](https://dev.variscite.com/dart-mx8m-plus/) | <img src="https://dev.variscite.com/static/assets/dart-family/DART-MX8M-PLUS_wiki.png" alt="DART-MX8M-PLUS" width="130"> | 4× Cortex-A53<br>Up to 1.8 GHz | Vivante GC7000UL (3D)<br>GC520L (2D) | [VIP8000](npus/vip8000.md) |
| [VAR-SOM-MX93](https://dev.variscite.com/var-som-mx93/) | <img src="https://dev.variscite.com/static/assets/som-family/VAR-SOM-MX93_wiki.png" alt="VAR-SOM-MX93" width="130"> | 2× Cortex-A55<br>Up to 1.7 GHz | No 3D GPU<br>PXP image engine | [Ethos-U65](npus/ethos-u65.md) |
| [DART-MX95](https://dev.variscite.com/dart-mx95/) | <img src="https://dev.variscite.com/static/assets/dart-family/DART-MX95_wiki.png" alt="DART-MX95" width="130"> | Up to 6× Cortex-A55<br>Up to 2.0 GHz | Arm Mali-G310 (3D)<br>2D acceleration | [Neutron](npus/neutron.md) |

Specifications depend on SKU. See [hardware sources](hardware.md) and
[demo availability](som-support.md); not every carrier or BSP is validated.

| Category | Demos |
| --- | --- |
| [AI / ML](models.md) | Classification, object/face detection, segmentation and hand gestures |
| [Multimedia](video-sources.md#video-player) | Video player |
| [OpenCL](som-support.md#non-ai-demos) | GPU computation on i.MX 8M Plus and i.MX 95 |
| BSP | Supported graphical examples already installed in `/opt` |

Hand gestures are experimental and available only on i.MX 8M Plus.

## Complete Guides

| Guide | What You Will Find |
| --- | --- |
| [SoM Support](som-support.md) | Demo availability, NPUs and tested camera modes |
| [Software Versions](software-versions.md) | Recorded test environments and BSP validation policy |
| [Face Detection](face-detection.md) | UltraFace image/video/camera demos, NPU preparation, frame flow and validation limits |
| [People and Vehicle Segmentation](segmentation.md) | Colored masks, shared input modes, model conversion and current platform limits |
| [People Segmentation](people-segmentation.md) | Lightweight person/background model, conversion, frame flow and HD/Full HD results |
| [Hand Gestures](hand-gestures.md) | Palm and landmark models, geometric gesture labels and limitations |
| [Hardware](hardware.md) | Official CPU/GPU/NPU specifications, photos and source links |
| [NPU Guides](npus/README.md) | What each NPU expects and per-SoM startup, classification and detection flows |
| [Models and Processing Flows](models.md) | Model comparison, origins and preparation, classification and detection flows |
| [Model Sources and Conversion](model-conversion.md) | Exact artifacts, source links, SHA-256, tensor interfaces and compiler commands |
| [Video Sources](video-sources.md) | Supplied clips, codecs, conversion and license limitations |
| [Demo Benchmarks](performance.md) | Our measured per-SoM results, FPS versus inference time and benchmark limitations |
| [Validation Record](validation.md) | Historical checks, decoder fixes and thermal/performance tests |
| [Experiment Ideas](ideas.md) | Research candidates, not installed or validated demos |

## Profiling and References

For frame-level bottlenecks and repeatable profiling commands, see
[Segmentation Profiling](segmentation-profiling.md).

For the vendor software stack, use the
[NXP i.MX Machine Learning User's Guide](https://www.nxp.com/docs/en/user-guide/UG10166.pdf)
matching your BSP. It complements, rather than replaces, this suite's model
provenance, conversion records and validation limits.

See [third-party notices](third-party.md) for component origins and attribution.
Adequate cooling is required; demos may slow down or pause when hot.

## Uninstalling

Run as root:

```sh
var-demos --uninstall
```
