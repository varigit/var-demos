# Video Sources

[Documentation](README.md) · [Project Overview](../README.md)

Classification, object detection and the player offer the two Buildings
clips supplied by the user and identified as Freepik downloads.
Face detection and lightweight people segmentation offer City Selfie,
supplied as clip `1117992`.
All three clips were supplied in 720p and 1080p.

| Clip | Original Filename Pattern | Duration | Frame Rate |
| --- | --- | --- | --- |
| Buildings A | `458687_High_rise_Buildings_<resolution>.mp4` | 34.08 seconds | 25 FPS |
| Buildings B | `458688_High_rise_Buildings_<resolution>.mp4` | 31.80 seconds | 25 FPS |
| City Selfie | `1117992_1080p_4k_<resolution>.mp4` | 41.24 seconds | 25 FPS |

The menu first selects HD (1280x720) or Full HD (1920x1080), then A or B.
Classification, detection and the player use the same content on each SoM.
Face and lightweight people menus show City Selfie at the selected quality on all three
SoMs. Despite `4k` in its downloaded name, the supplied versions are
1280×720 and 1920×1080, not 4K.

| SoM | Installed Video Format | Preparation |
| --- | --- | --- |
| i.MX 8M Plus | H.264 MP4 | Original supplied clips, renamed to `buildings_<id>_<resolution>.mp4` |
| VAR-SOM-MX93 | MJPEG AVI | Converted copies of those clips for CPU decoding |
| DART-MX95 | H.264 MP4 | Compatibility copies without B-frames for the tested decoder path |

Conversion preserves source resolution, frame rate and duration, not the
original encoding. The original files are retained; manifests specify the
SHA-256 checksum of each installed copy. See [camera/video flows](models.md#image-video-and-camera-input-flow)
for decoding and preprocessing differences.

The original Freepik page URLs and license documents were not supplied.
No independent license verification or new video license is claimed here.
Model license files do not serve as licenses for these videos.

## Preparing the Face Clip

The original H.264 files are retained on MPlus. MX93 receives MJPEG
compatibility copies and MX95 receives H.264 copies without B-frames:

```sh
ffmpeg -i input.mp4 -an -c:v mjpeg -q:v 3 -pix_fmt yuvj420p -threads 2 output.avi
ffmpeg -i input.mp4 -an -c:v libx264 -preset fast -crf 18 -bf 0 -g 50 -pix_fmt yuv420p -movflags +faststart -threads 2 output.mp4
```

No output size or frame rate is forced. Both versions were probed after
conversion: their dimensions, 25 FPS and 41.24-second duration are preserved.
They are stored under `demos/machine-learning/face-detection/v1/` on
DigitalOcean Spaces with names `face_1117992_<resolution>.mp4` or `.avi`.
The installer verifies each SHA-256 in its per-SoM manifest. The original
downloaded files were not overwritten. No original page or license document
was supplied for City Selfie, so its redistribution license is not
independently verified here.

See [Face Detection](face-detection.md) for model preparation and frame flow.

Chicago and Jijiga examples are retired. Updates remove their known,
unchanged suite-installed files by checksum. Changed files, custom videos
and symlink targets are preserved. No external storage objects are deleted.

## Video Player

Select **Multimedia** in `var-demos`, then a video resolution and clip.
The player offers Buildings A/B, not the face-demo clip. Use its playback,
seek and volume controls; Space toggles playback, S stops, F toggles
fullscreen and Esc exits. Open selects a local file supported by your BSP.
G2D, PXP or EGL prepares a bounded preview, preserving aspect ratio. This
is not a zero-copy or native-resolution rendering claim. MX93 uses CPU
MJPEG decoding; MX95 selects MMAP decoder buffers before EGL conversion.

## Related Guides

- [Input Processing Flow](models.md#image-video-and-camera-input-flow): where the decoder, CPU, G2D/PXP and GPU fit.
- [Performance](performance.md): how different decoding paths affect the comparison.
