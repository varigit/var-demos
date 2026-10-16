<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://nyc3.digitaloceanspaces.com/variscite-marketing/demos/branding/v1/variscite-logo-white.png">
  <img src="https://nyc3.digitaloceanspaces.com/variscite-marketing/demos/branding/v1/variscite-logo-black.png" alt="Variscite" width="320">
</picture>

**Demos for Variscite System on Modules**

## Installing Variscite Demos

Use a compatible Variscite Linux image with NPU and graphics support.
Boot your kit, connect it to the internet and run as root:

```sh
curl -fsSL https://raw.githubusercontent.com/varigit/var-demos/edge-ai/install.sh | sh
```

The SoM is detected automatically. To update, close the demos and repeat
the command.

## Running Variscite Demos

Open the demo manager with the command below, then choose demos to try:

```sh
var-demos
```

Choose a demo. Arrow keys to navigate, Enter to select, Esc to return.

Available demos and input options depend on your platform and BSP.

## Documentation

Explore the [demo guides](docs/README.md) and the
[NXP Machine Learning User's Guide](https://www.nxp.com/docs/en/user-guide/UG10166.pdf).

## License

Licensed under the [BSD 3-Clause License](LICENSE), except where otherwise noted.
