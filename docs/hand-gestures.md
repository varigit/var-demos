# Hand Gestures

[Documentation](README.md) · [Model Inventory](models.md#model-inventory)

This experimental i.MX 8M Plus demo detects one palm and estimates 21 hand
landmarks. Open hand, closed fist, pointing and victory are geometric rules,
not a trained gesture classifier. Other poses show `Unknown`. Labels settle
for 350 ms; losing the hand clears the label and landmark smoothing.

## Run and Processing Flow

Select Hand Gestures under **AI / ML** in `var-demos`, then the camera mode.
Only live camera input is offered in the menu. The sample image is used for
developer checks and warmup, not substituted for camera input.

Camera frames become RGB, padded/resized to 256×256 for palm detection.
The CPU decodes the palm result and aligns a crop for the landmark model.
Both models take FLOAT32 RGB `[1,256,256,3]`, normalized with
`(pixel - 128) / 128`. VX prepares supported graph operations for the NPU
at runtime; crop preparation, coordinate mapping, gesture rules and drawing
run on the CPU. No local Vela or Neutron conversion is used for this demo.

Both models warm up before capture. Cold initialization can take tens of
seconds. Fullscreen uses a central crop; `--windowed` retains the whole frame.
Esc stops the demo. Thermal pacing remains active.

## Model Origins and Artifacts

The MediaPipe palm and landmark models were converted upstream by PINTO0309
and distributed by `terryky/tflite_gles_app`, revision
`bfc2015a6d1234deebc9574798b175a6d1b2afc2`. The tracker/anchors derive from
NXP `eiq-example`, revision `67cce2905b4343fd9d87b273905a53dc4357348b`.
These are existing converted artifacts, not locally trained models; the
original conversion has not been reproduced here. Sources and attribution
are retained in [third-party notices](third-party.md).

| Installed Model | SHA-256 |
| --- | --- |
| `palm.tflite` | `3ea444e1f7dc8a0b2c06282f1ac6eb4ebf3e2e7d79dd184b440be1cfb3205897` |
| `landmark.tflite` | `3c8f75a0c67ba33fc9b2d9029e71dd1d37ced52afa4a9bae0c59c96f147fe4db` |

The [manifest](../ai-ml-demos/hand-gesture/assets.manifest) also identifies
the anchors and reference image. The tracker validates FLOAT32 inputs;
the upstream models have quantized internal operators. Boundary dtype does
not establish that every operation runs on the NPU.

## Checks and Limits

Run `python3 check_on_board.py` from `/opt/var-demos/ai-ml/hand-gesture`
for the reference CPU/NPU comparison. The recorded checks cover the open-hand
sample, its mirror and blank images, not accuracy across arbitrary gestures.
The legacy landmark `output_handflag` was constant on hand and blank crops
in those checks. Presence instead uses the palm detector's 0.95 threshold.
See [validation](validation.md) for board-test scope. Multi-hand tracking,
multi-hour stability and representative gesture accuracy are not certified.
