# NPU Guides

The lightweight [People Segmentation](../people-segmentation.md) guide covers
the same Selfie Segmenter source prepared for all three NPUs, exact tensor
interfaces, converter commands and the frame-processing flow.

[Documentation](../README.md) · [Project Overview](../../README.md)

Choose the NPU in your SoM to see how to start the demos, what the model must
contain and which processing steps run in software or dedicated hardware.

| SoM / NPU | Runtime Expects | Complete Guide |
| --- | --- | --- |
| i.MX 8M Plus / VIP8000 | Supported quantized TFLite; VX prepares the graph at runtime | [VIP8000](vip8000.md) |
| VAR-SOM-MX93 / Ethos-U65 | TFLite compiled by Vela for Ethos-U65-256 | [Ethos-U65](ethos-u65.md) |
| DART-MX95 / Neutron | BSP-compatible Neutron-compiled TFLite graph | [Neutron](neutron.md) |

These are this suite's paths, not an exhaustive list of every model format or
data type supported by the hardware. A `.tflite` filename alone proves neither
NPU compatibility nor full hardware delegation. Check operator support,
compiler/driver compatibility and the actual delegation logs.

The linked [NXP ML guide](https://www.nxp.com/docs/en/user-guide/UG10166.pdf)
was checked at revision LF6.18.37_2.1.0 (2026-09-24). Its latest edition can
differ from the BSP installed on each SoM. Library versions, converter targets
and firmware must follow the matching BSP, not this link's newest revision.

[Compare models and origins](../models.md) ·
[Exact artifacts and conversion commands](../model-conversion.md) ·
[Our demo benchmarks](../performance.md)
