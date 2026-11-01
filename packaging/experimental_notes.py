#!/usr/bin/env python3
"""Prints the release notes for an experimental pre-release (used by experimental-release.yml)."""
import os

sha = os.environ.get("GITHUB_SHA", "unknown")
print("""**Experimental pre-release. The bundled extension has NOT been validated in Blender.**

It passed packaging, manifest, licence and checksum checks only. It has not been installed or run in any
Blender build, and no official Blender 5.3 validation exists for it. Expect problems and do not rely on it
for production work. Back up your projects.

Installation compatibility: bundled and standalone NineSync (Core, FX, mmd_tools) must not be enabled at
the same time. Disable one configuration before enabling the other, and restart Blender when switching.

Built from %s. See artifact-manifest.json for the Core and FX commits, the bundled dependency versions and
the SHA-256 of the ZIP.""" % sha)
