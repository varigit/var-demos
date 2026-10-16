#!/usr/bin/env python3

# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
from pathlib import Path
import sys
import tomllib


def load_catalog(path):
    with Path(path).open("rb") as catalog_file:
        return tomllib.load(catalog_file)


def find_demo(catalog, demo_id):
    for demo in catalog["demos"]:
        if demo["id"] == demo_id:
            return demo
    raise SystemExit(f"unknown demo: {demo_id}")


def find_launcher(catalog, launcher_id):
    for launcher in catalog.get("launchers", []):
        if launcher["id"] == launcher_id:
            return launcher
    raise SystemExit(f"unknown launcher: {launcher_id}")


def validate(catalog, root):
    if catalog.get("version") != 1:
        raise SystemExit("unsupported catalog version")

    platforms = catalog.get("platforms", {})
    seen = set()
    for demo in catalog.get("demos", []):
        demo_id = demo.get("id", "")
        if not demo_id or demo_id in seen:
            raise SystemExit(f"invalid or duplicate demo id: {demo_id}")
        seen.add(demo_id)

        for platform in demo.get("platforms", []):
            if platform not in platforms:
                raise SystemExit(
                    f"{demo_id} references unknown platform: {platform}"
                )

        demo_path = Path(demo.get("path", ""))
        if demo_path.is_absolute() or ".." in demo_path.parts:
            raise SystemExit(f"unsafe path for demo: {demo_id}")

        manifest = Path(demo.get("manifest", ""))
        if manifest.is_absolute() or ".." in manifest.parts:
            raise SystemExit(f"unsafe manifest for demo: {demo_id}")

        source = root / demo_path
        if not source.is_dir() or not (source / manifest).is_file():
            raise SystemExit(f"missing source or manifest for: {demo_id}")

    launchers = set()
    for launcher in catalog.get("launchers", []):
        launcher_id = launcher.get("id", "")
        if not launcher_id or launcher_id in launchers:
            raise SystemExit(
                f"invalid or duplicate launcher id: {launcher_id}"
            )
        launchers.add(launcher_id)
        if launcher.get("demo") not in seen:
            raise SystemExit(
                f"{launcher_id} references an unknown demo"
            )
        command = launcher.get("command")
        if not isinstance(command, list) or not command:
            raise SystemExit(f"invalid command for: {launcher_id}")


def detect_platform(catalog, compatible_path):
    compatible = Path(compatible_path).read_bytes().split(b"\0")
    values = {value.decode(errors="replace") for value in compatible if value}
    for platform_id, platform in catalog["platforms"].items():
        if values.intersection(platform.get("compatible", [])):
            print(platform_id)
            return
    raise SystemExit("unsupported board")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--root", required=True)

    detect_parser = subparsers.add_parser("detect")
    detect_parser.add_argument(
        "--compatible", default="/proc/device-tree/compatible"
    )

    platform_parser = subparsers.add_parser("platform-field")
    platform_parser.add_argument("platform")
    platform_parser.add_argument("field")

    demos_parser = subparsers.add_parser("demos")
    demos_parser.add_argument("--platform", required=True)
    demos_parser.add_argument("--titles", action="store_true")

    demo_parser = subparsers.add_parser("demo-field")
    demo_parser.add_argument("demo")
    demo_parser.add_argument("field")

    supports_parser = subparsers.add_parser("supports")
    supports_parser.add_argument("demo")
    supports_parser.add_argument("platform")

    launchers_parser = subparsers.add_parser("launchers")
    launchers_parser.add_argument("--platform", required=True)

    launcher_parser = subparsers.add_parser("launcher-field")
    launcher_parser.add_argument("launcher")
    launcher_parser.add_argument("field")

    args = parser.parse_args()
    catalog = load_catalog(args.catalog)

    if args.command == "validate":
        validate(catalog, Path(args.root))
    elif args.command == "detect":
        detect_platform(catalog, args.compatible)
    elif args.command == "platform-field":
        try:
            print(catalog["platforms"][args.platform][args.field])
        except KeyError as error:
            raise SystemExit(f"unknown platform or field: {error}") from error
    elif args.command == "demos":
        for demo in catalog["demos"]:
            if args.platform in demo.get("platforms", []):
                if args.titles:
                    print(f"{demo['id']}\t{demo['title']}")
                else:
                    print(demo["id"])
    elif args.command == "demo-field":
        demo = find_demo(catalog, args.demo)
        try:
            print(demo[args.field])
        except KeyError as error:
            raise SystemExit(f"unknown demo field: {error}") from error
    elif args.command == "supports":
        demo = find_demo(catalog, args.demo)
        if args.platform not in demo.get("platforms", []):
            sys.exit(1)
    elif args.command == "launchers":
        supported = {
            demo["id"]
            for demo in catalog["demos"]
            if args.platform in demo.get("platforms", [])
        }
        for launcher in catalog.get("launchers", []):
            if launcher["demo"] in supported:
                print(f"{launcher['id']}\t{launcher['title']}")
    elif args.command == "launcher-field":
        launcher = find_launcher(catalog, args.launcher)
        try:
            value = launcher[args.field]
        except KeyError as error:
            raise SystemExit(f"unknown launcher field: {error}") from error
        if isinstance(value, list):
            print("\0".join(value))
        else:
            print(value)


if __name__ == "__main__":
    main()
