# Software Versions

[Documentation](README.md) · [Validation Record](validation.md)

The project targets the latest official Variscite Yocto release available
for each SoM. Releases are checked separately because the three products do
not always use the same Yocto series or kernel.

## Installed and Tested

These kernels were read from the connected test systems on October 8, 2026:

| SoM | Installed Kernel | Yocto Series |
| --- | --- | --- |
| DART-MX8M-PLUS | 6.6.144 | Scarthgap |
| VAR-SOM-MX93 | 6.6.138 | Scarthgap |
| DART-MX95 | 6.18.20 | Wrynose |

The [validation record](validation.md) describes the actual tests. A matching
kernel number alone does not prove that all userspace packages, model
compilers, delegates or firmware versions match another image.

## Release Targets Recorded on October 8, 2026

The following release targets were recorded against the product pages on
October 8, 2026, not revalidated as the latest releases by this documentation
review. Check the linked release pages before choosing an image:

| SoM | Official Target | Kernel | Source |
| --- | --- | --- | --- |
| DART-MX8M-PLUS | Wrynose | 6.18.20 | [Variscite releases](https://dev.variscite.com/dart-mx8m-plus/) |
| VAR-SOM-MX93 | Scarthgap | 6.6.138 | [Variscite releases](https://dev.variscite.com/var-som-mx93/) |
| DART-MX95 | Wrynose | 6.18.20 | [Variscite releases](https://dev.variscite.com/dart-mx95/) |

MPlus Wrynose validation is pending on our test system. The table identifies
the desired release family; it does not claim that a full image release tag
has been verified merely by reading `uname -r`.

After changing the BSP, validate installation, image/video/camera modes,
NPU delegation, HD/Full HD playback and thermal behavior. Record the exact
image release and compatible converter/runtime versions with the results.
Models with compiled NPU graphs may require recompilation for that BSP.

Updating `var-demos` updates the demos and assets. It does not replace the
Linux image, kernel, drivers or firmware. Use the product's own image and
recovery instructions when updating the BSP.
