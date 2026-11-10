# Manual

This manual is organised by what you want to do. Start with **Core** for PMM projects and animation syncing; use **FX** for accessories, effects and node workflows.

All controls live in the **NineSync** tab of the 3D Viewport sidebar (press **N**).

## Core — PMM Bridge

- [PMM Create](core/pmm-create.md): write an MMD project from your Blender scene.
- [PMM Sync](core/pmm-sync.md): bring a `.pmm` into Blender and keep it up to date.
- [Rigify Remap](core/rigify-remap.md): carry PMM motion onto a Rigify rig.

## FX — FX Importer

- [Import Accessories and Effects](fx/import.md)
- [Geometry Nodes Setup](fx/geometry-nodes.md)
- [Shader Nodes Setup](fx/shader-nodes.md)

!!! note "Rendering"
    **EEVEE is recommended** for imported effects. **Cycles** can work, but some effects need manual shader and transparency adjustments. Treat this as a per-effect consideration, not a guarantee of parity with MMD.

!!! warning "Not supported"
    Full-screen and post-processing MME effects are not supported.
