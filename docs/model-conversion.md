# Model Sources and Conversion

[Documentation](README.md) · [Project Overview](../README.md)

Use separate artifacts for each backend. A `.tflite` suffix alone does not
establish compatibility. Preserve the source model, license, labels,
preprocessing, quantization parameters and compiler version with each asset.

| Board | Model preparation | Runtime delegate |
| --- | --- | --- |
| i.MX 8M Plus | Quantized TFLite; VX prepares its graph | [VIP8000 / `libvx_delegate.so`](npus/vip8000.md) |
| i.MX 93 | Quantized TFLite compiled with Vela | [Ethos-U65 / `libethosu_delegate.so`](npus/ethos-u65.md) |
| i.MX 95 | BSP-compatible Neutron compiled model | [Neutron / `libneutron_delegate.so`](npus/neutron.md) |

The backend paths are documented in the
[NXP machine-learning guide](https://www.nxp.com/docs/en/user-guide/UG10166.pdf).
Use the guide and tools matching the installed BSP, not automatically the
newest release.

## Exact installed artifacts and provenance

The original MPlus artifacts are distributed with the
[Variscite demos](https://github.com/varigit/var-demos/tree/demos/ai-ml-demos).
Our installer downloads SHA-256-verified copies from the
[MPlus asset distribution](https://nyc3.digitaloceanspaces.com/variscite-marketing/demos/machine-learning/imx8mplus/v2/models/mobilenet_v1_1.0_224_quant.tflite).
Their earlier training/export recipe and exact upstream Google archive have
not been recovered; no new training or calibration is claimed here.

| SoM / task | Installed file | Artifact SHA-256 |
| --- | --- | --- |
| MPlus classification | `mobilenet_v1_1.0_224_quant.tflite` | `ecc3a67c47c5a609ec35f6a58a7d97532834e43df4cb7d3f1204a8164b7d20dd` |
| MPlus detection | `ssd_mobilenet_v1_1_default_1.tflite` | `e4b118e5e4531945de2e659742c7c590f7536f8d0ed26d135abcfe83b4779d13` |
| MX93 classification | `mobilenet_vela.tflite` | `f57cf65901827a9fb1c5917cdf859c158044a3e23385a790b64787470e6ab6c3` |
| MX93 detection | `ssd_vela.tflite` | `4133c77dcd38cb3c5738bc9d0a6c4c2a5e042e18329d01eab25639b6e42ae98b` |
| MX95 classification | `mobilenet_neutron.tflite` | `a4d15d923469bbaf3c173625135ef7cfa83212af821085df35969b576031bb55` |
| MX95 detection | `ssd_neutron.tflite` | `13f2da71c9f9978d6780d83b682118d23258b0cea4c0b62d6a00c48a53637527` |

SHA-256 identifies the complete artifact, not just its learned weights.
Different compiled hashes are expected, but do not prove model equivalence.
The retained MX93 SSD source `/tmp/var-demos-ssd/ssd.tflite` has exactly the
MPlus detector's SHA-256 above. Its Vela summary records `Ethos_U65_256`,
`internal-default` system configuration and memory mode. The MobileNet
Vela conversion was reproduced from the MPlus source with SHA-256 `ecc3a67c47c5a609ec35f6a58a7d97532834e43df4cb7d3f1204a8164b7d20dd`;
the resulting artifact matched the installed MX93 model byte-for-byte
(`f57cf65901827a9fb1c5917cdf859c158044a3e23385a790b64787470e6ab6c3`).
Thus both MX93 source models are the MPlus models; the compiled execution
artifacts differ. This verification does not establish weight equivalence
with the separate NXP MX95 models.

### Tensor interface, verified on the installed boards

All inputs are `[1,H,W,3]` RGB. Quantization means
`real_value = scale × (stored_value − zero_point)`; signed INT8 and unsigned
UINT8 are not interchangeable.

| SoM / task | Input size / dtype | Input scale / zero point | Outputs |
| --- | --- | --- | --- |
| MPlus classification | 224×224 / UINT8 | 0.0078125 / 128 | UINT8, 1001 scores; scale 0.00390625, zero point 0 |
| MPlus detection | 300×300 / UINT8 | 0.0078125 / 128 | FLOAT32 boxes, classes, scores and count after detection postprocessing |
| MX93 classification | 224×224 / UINT8 | 0.0078125 / 128 | UINT8, 1001 scores; scale 0.00390625, zero point 0 |
| MX93 detection | 300×300 / UINT8 | 0.0078125 / 128 | FLOAT32 detection postprocessing outputs; NPU graph plus CPU postprocessing |
| MX95 classification | 224×224 / UINT8 | approximately 1/255 / 0 | FLOAT32, 1001 scores |
| MX95 detection | 300×300 / UINT8 | approximately 1/255 / 0 | FLOAT32 `[1,1917,1,4]` boxes and `[1,1917,91]` scores; decode/NMS on CPU |

These are the external tensor interfaces, not a claim that every internal
operator or tensor uses the same dtype. MX95 uses
`mobilenet_v1_1.0_224_quant_uint8_float32_neutron.tflite` and
`ssdlite_mobilenet_v2_coco_quant_uint8_float32_no_postprocess_neutron.tflite`
from the matching [NXP release](https://github.com/nxp-imx-support/nxp-demo-experience-assets/tree/lf-6.18.20_2.0.0/models),
renamed locally as listed above. The paired `box_priors.txt` and
`coco_labels.txt` come from that release too. They must not be replaced
with the MPlus SSD labels/postprocessor.

## Quantization and preprocessing

Quantize with a representative dataset from the intended application.
Check input dtype, scale, zero point, RGB/BGR order, resize policy and output
tensor layout. Do not cast normalized floats directly to unsigned bytes.
For detectors, preserve matching anchors, label indices, box decoding and
non-maximum suppression. These operations may remain on the CPU.

## i.MX 8M Plus

Load a supported quantized TFLite model with the VX delegate. Neither Vela
nor Neutron compilation is used for this backend. Warm up before measuring;
the first invocation includes graph preparation. Check delegation logs for
CPU fallback rather than assuming that loading a delegate accelerates all
operators.

## i.MX 93

Use the Vela version supplied with the BSP. On the tested Scarthgap image,
Vela 3.12.0 successfully compiled MobileNet V1 for Ethos-U65-256:

```sh
vela model_quant.tflite --accelerator-config ethos-u65-256 --output-dir output
```

Load the generated `*_vela.tflite` with the Ethos-U delegate. This command
was tested with MobileNet. SSD was also compiled for the same accelerator,
as recorded in its retained compiler summary; it is not a guarantee for
arbitrary operators. To reproduce SSD from the verified MPlus source:

```sh
vela ssd_mobilenet_v1_1_default_1.tflite --accelerator-config ethos-u65-256 --output-dir output
```

Use Vela 3.12.0 and its `internal-default` settings for this recorded
configuration. SSD compilation was reproduced from the retained source
with these options; its SHA-256 matched the installed compiled artifact
(`4133c77dcd38cb3c5738bc9d0a6c4c2a5e042e18329d01eab25639b6e42ae98b`).
Vela reports 60 NPU operators and one CPU detection postprocessing operator
for SSD, versus 60 NPU operators and no CPU operators for MobileNet. These
are compiler operator counts, not measured application throughput.
The old repository MobileNet artifact failed with this image's TFLite
runtime, while recompiling its uncompiled model with the image's Vela passed.
The NXP examples also
[compile quantized MX93 models with Vela](https://github.com/nxp-imx/nxp-nnstreamer-examples/blob/main/downloads/compile_models.sh).

## i.MX 95

Use the Neutron converter and model artifacts matching the BSP's driver and
firmware. Do not reuse a Vela artifact or copy a converter from an older SDK.
The tested Wrynose 6.18.20 image reported driver microcode 3.1.2; an older
locally compiled SSD reported microcode 3.0.0 and produced a mismatch warning.
That older artifact is not selected for installation.

MobileNet V1 and SSD-Lite camera/video inference were tested using the matching
[NXP model release](https://github.com/nxp-imx-support/nxp-demo-experience-assets/tree/lf-6.18.20_2.0.0/models).
The classifier, SSD-Lite detector and UltraFace use NXP-precompiled artifacts;
their Neutron conversions were not reproduced locally. DeepLabV3 and Selfie
Segmenter were compiled locally with Neutron Converter 3.1.2 and exercised
on the tested driver. See [DeepLabV3](segmentation.md) and
[Selfie Segmenter](people-segmentation.md) for source revisions, commands
and hashes. These checks do not establish compatibility for arbitrary models.
Use the BSP's `tflite_runtime` with its delegate. On this image, switching
to the installed `ai_edge_litert` runtime crashed during tensor allocation;
the presence of an importable runtime does not establish delegate ABI
compatibility.

## Validation before publishing

1. Confirm the intended NPU subgraph is delegated; XNNPACK is CPU execution.
2. Compare predictions with the source model on fixed reference inputs.
3. Measure warm inference separately from full camera/video throughput.
4. Check cleanup, restart, memory growth and named thermal sensors over time.
5. Publish the artifact externally with its SHA-256 and license, then update
   the platform catalog only after testing the installed demo.

NPU availability does not imply video decoder availability. The tested MX93
image has a working camera but no GStreamer H.264 decoder. Its video demos
use MJPEG AVI copies decoded on the CPU, preserving source resolution,
frame rate and duration. This does not preserve the original encoding or
make video throughput a like-for-like comparison with the other boards.

## Related Guides

- [Models and Processing Flows](models.md): visual overview of model preparation and inference.
- [Validation Record](validation.md#model-reproduction): recorded conversion reproduction checks.
- [Video Sources](video-sources.md): video conversion, which is separate from model compilation.
