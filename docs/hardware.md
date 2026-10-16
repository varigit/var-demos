# SoM Hardware

[Documentation](README.md) · [Project Overview](../README.md)

The photographs illustrate three Variscite module products. They do not
establish the exact SKU of a connected test board. The installer identifies
processor families; this is not a claim
that every carrier, camera, SKU or Linux image has been validated.

## DART-MX8M-PLUS

<img src="https://dev.variscite.com/static/assets/dart-family/DART-MX8M-PLUS_wiki.png" alt="DART-MX8M-PLUS front view" width="240">

| Component | Product Specification |
| --- | --- |
| Processor | NXP i.MX 8M Plus |
| Linux CPU | 4 Cortex-A53 cores, up to 1.8 GHz |
| Real-Time Core | Cortex-M7, up to 800 MHz |
| Graphics | Vivante GC7000UL 3D and GC520L 2D engines |
| NPU | VeriSilicon VIP8000; advertised 2.3 TOPS |

Sources: [Developer Center](https://dev.variscite.com/dart-mx8m-plus/) and its
linked [product specifications](https://variscite.com/system-on-module-som/i-mx-8/i-mx-8m-plus/dart-mx8m-plus/).
For model preparation and actual demo flows, open the [VIP8000 guide](npus/vip8000.md).

## VAR-SOM-MX93

<img src="https://dev.variscite.com/static/assets/som-family/VAR-SOM-MX93_wiki.png" alt="VAR-SOM-MX93 front view" width="240">

| Component | Product Specification |
| --- | --- |
| Processor | NXP i.MX 93 |
| Linux CPU | Dual Cortex-A55, up to 1.7 GHz, for the NPU-equipped configuration |
| Real-Time Core | Cortex-M33, up to 250 MHz |
| Graphics | No 3D GPU; PXP hardware for pixel conversion/scaling |
| NPU | Arm Ethos-U65; advertised 0.5 TOPS |

Sources: [Developer Center](https://dev.variscite.com/var-som-mx93/) and its
linked [product specifications](https://variscite.com/system-on-module-som/i-mx-9/i-mx-93/var-som-mx93/).
The product family also includes a single-core option without an NPU; that
variant is not the configuration validated for these NPU demos.
See the [Ethos-U65 guide](npus/ethos-u65.md) for Vela compilation and CPU/PXP responsibilities.

## DART-MX95

<img src="https://dev.variscite.com/static/assets/dart-family/DART-MX95_wiki.png" alt="DART-MX95 front view" width="240">

| Component | Product Specification |
| --- | --- |
| Processor | NXP i.MX 95 |
| Linux CPU | Up to 6 Cortex-A55 cores, up to 2.0 GHz; 4-core SKUs also exist |
| Graphics | Arm Mali-G310 3D GPU and 2D acceleration |
| NPU | NXP Neutron; product page advertises 8 eTOPS |

Sources: [Developer Center](https://dev.variscite.com/dart-mx95/) and its
linked [product specifications](https://variscite.com/system-on-module-som/i-mx-9/i-mx-95/dart-mx95/).
The [NXP ML guide](https://www.nxp.com/docs/en/user-guide/UG10166.pdf) identifies
the Mali-G310 and Neutron execution paths. See the [Neutron guide](npus/neutron.md)
for this suite's model and runtime requirements.

## Reading These Specifications

CPU figures are product maxima, not a measurement of the current CPU frequency.
TOPS/eTOPS are manufacturer ratings, not measured inference speed or video FPS;
do not treat the MX95 eTOPS figure as a like-for-like benchmark against the
other TOPS ratings. Available acceleration also depends on the BSP and drivers.
Product specifications and photos were checked on 2026-10-07; photos remain
hosted by Variscite and may depict a different hardware revision.

Software on the CPU can use optimized libraries and SIMD. Here, **CPU/software**
distinguishes that path from dedicated decoder, PXP/G2D, GPU or NPU hardware.
A delegate is software that submits supported model operations to hardware;
unsupported operations or postprocessing can still run on the CPU.

## Related Guides

- [SoM Support](som-support.md): enabled demos and tested camera modes.
- [NPU Guides](npus/README.md): exact artifacts, expected tensors and processing flows.
- [Demo Benchmarks](performance.md): measurements from our own demo runs.
