# Third-party components

Tracker and anchors: NXP `eiq-example`, commit
`67cce2905b4343fd9d87b273905a53dc4357348b`, Apache-2.0.
Original tracker: `wolterlw/hand_tracking`, Apache-2.0.
The Apache license and MIT notices are included in
[the component license](../ai-ml-demos/hand-gesture/LICENSE);
modified files retain credits.
The reference image is from the same NXP example repository.

Models: Google's MediaPipe hand models, converted by PINTO0309 and
distributed by `terryky/tflite_gles_app`, commit
`bfc2015a6d1234deebc9574798b175a6d1b2afc2`.
The model-directory README identifies PINTO's hand-model conversion.
Models have float32 inputs/outputs and quantized internal operators.
SHA-256 identities are recorded in the
[asset manifest](../ai-ml-demos/hand-gesture/assets.manifest).

Sources:

- https://github.com/nxp-imx/eiq-example
- https://github.com/terryky/tflite_gles_app/tree/master/gl2handpose/handpose_model
- https://github.com/PINTO0309/PINTO_model_zoo/tree/main/033_Hand_Detection_and_Tracking
- https://github.com/google/mediapipe

Google MediaPipe: Apache-2.0; see the component license linked above.

## MIT notices

Copyright (c) 2019 terryky
Copyright (c) 2024 Katsuya Hyodo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
