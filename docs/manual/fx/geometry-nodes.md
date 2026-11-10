# Geometry Nodes Setup

## What it does

MME vertex shaders are compiled to **Geometry Nodes** so effects move and deform in Blender without per-frame Python. Not every effect uses Geometry Nodes: pixel shaders become [shader nodes](shader-nodes.md), and passes that cannot compile fall back to a Python (numpy) pass.

## Choosing a backend

In the NineSync FX settings, **Effect Backend** is **Geometry Nodes** (default) or **Python**. It applies on the next sync or **Rebuild All Effects**.

<!-- SCREENSHOT: Effect settings panel -->

## What you can adjust

- **Effect Density:** share of each loop to draw. 1 matches MMD; lower is faster to scrub on heavy effects.
- **Geometry Tolerance:** how far simplified strips may drift from the full mesh. 0 keeps every row. Applies on the next rebuild.
- **Pre-cull Cache:** remembers vertices that are never drawn, so rebuilds are faster. The trash icon clears it.
- **Auto Rebuild:** rebuild after editing a parameter that changes geometry; turn off for heavy effects and press **Rebuild** yourself.
- **Live Effect Preview:** Python passes update on frame change; Geometry Nodes passes always do.
- Per-effect values are under **Selected Effect > Effect Parameters** (**Reset Parameters** restores the `.fx` defaults).

## Inspecting and repairing

**Selected Effect > Effect Details** has tabs for **Linked Objects**, **Passes** and **Selected Pass**, showing backend and node groups. Use **Rebuild** on an effect, or **Rebuild All Effects**; **Clear Effect Caches** forces a fresh analysis.

## Core Node Library

Shared node groups live in a library file (`mme_core.blend`). **Rebuild Standard Groups** rebuilds the standard groups for your Blender version; **Save Shared Groups to Library** adds this file's groups. Most users never need these.

## Baking

**Bake** stores effect geometry over the scene frame range (packed in the `.blend` or on disk) so playback and rendering read stored geometry. **Clear Bake** removes it.
