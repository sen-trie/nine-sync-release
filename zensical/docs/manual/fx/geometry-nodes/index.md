# Geometry Nodes Setup

The **vertex shader** of an MME effect decides where every vertex of the accessory ends up (spread, wobble, billboard,
trail…). FX compiles that shader into **Geometry Nodes** so effects move, deform and render in Blender without running Python on every frame.

If you have never opened Geometry Nodes, it is a system that lets you procedurally generate and animate 3D geometry.

## The settings panel

These options are in the **Settings** sub-panel of the **NineSync: FX Importer** panel. Some are shown only for the backend they apply to.

<!-- SCREENSHOT: NineSync: FX Importer panel -->

<!-- prettier-ignore -->
| Setting | Why FX exposes it | Affects |
|---|---|---|
| **Effect Backend** (Geometry Nodes / Python) | Some vertex shaders cannot be expressed in nodes; Python can run any of them, slowly | how every pass is built |
| **Effect Density** | Heavy effects draw tens of thousands of copies; scrubbing at a fraction is much faster. 1 matches MMD | loop counts of every pass |
| **Geometry Tolerance** | Long ribbons and rings are built from thousands of rows; rows the shader can recreate by interpolation can be merged. 0 keeps every row | strip simplification ([Culling](../how-it-works/culling.md#strip-simplification)) |
| **Build Memory** (Low / Balanced / High) | Analysis of huge effects uses temporary arrays; Low trades build time for RAM. The result is identical | analysis batch sizes only |
| **Auto Rebuild** | Rebuilding a heavy effect can take minutes, so it is off by default | whether geometry-changing edits rebuild by themselves |
| **Detailed Build Log** | Logs every changed input behind a rebuild, rebake or skip | the log only |
| **Pre-cull Cache** | Caches the visibility analysis so a rebuild can reuse it ([Cache](../how-it-works/cache.md)) | analysis speed |
| **Per-Particle Shader Stage** (Geometry Nodes backend, on by default) | For effects that copy a mesh many times, runs the part of the vertex shader that depends only on the copy once per copy instead of once per vertex. The picture is the same; turn it off only to compare against the plain per-vertex graph. Changing it rebuilds only the affected looped passes | looped Geometry Nodes passes ([how](../how-it-works/geometry-nodes-translation.md#2-the-per-particle-shader-stage)) |
| **Transparency Order** (Geometry Nodes backend) | How a looped effect whose copies move rigidly is drawn: **Full Shader**, **MMD Order** (default) or **Blender Sorted**. An accessory's **Effect Controls** can override the scene value. Takes effect at once, with no rebuild | only eligible textured or translucent looped passes ([how](../how-it-works/geometry-nodes-translation.md#transparency-order)) |
| **Live Effect Preview** | Python passes recompute on every frame change; turn it off to scrub faster. Shown only with the Python backend | Python passes only |

### Choosing a backend

|                      | Geometry Nodes (default)              | Python                                                 |
| -------------------- | ------------------------------------- | ------------------------------------------------------ |
| Runs                 | inside Blender's node evaluator       | numpy, from a frame-change handler                     |
| Per-frame cost       | no Python per frame                   | Python per frame, unless baked                         |
| Renders and baking   | native                                | recomputed per frame                                   |
| Which vertex shaders | those expressible as nodes            | any the interpreter can run                            |
| Editable             | you can open and change the node tree | the geometry is written into the mesh, no tree to edit |

**You rarely, if ever, need to choose Python.** FX automatically falls back to Python for a single pass whose vertex shader cannot be compiled.

## Rebuilding

Press **Rebuild Changed Effects** after changing something that alters geometry. A rebuild only redoes the passes whose
inputs changed; the others keep their objects, node trees, visibility, keys and bakes.

- **Force Rebuild All** ignores recorded inputs and rebuilds every pass.
- The button turns red when an effect is **out of date**: a geometry-changing parameter was edited while **Auto
  Rebuild** is off.
- **Clear Effect Caches** (trash icon) deletes the caches so the next build analyses everything from scratch.

What counts as "changed" is documented with the architecture:
[Incremental rebuilds](../how-it-works/index.md#incremental-rebuilds).

## Inspecting and repairing

**Selected Effect > Effect Details** has three tabs:

- **Linked Objects**: objects, bones and morphs the effect reads.
- **Passes**: every pass, whether it runs on **Geometry Nodes** or **Python**, loop counts and flags. Full-screen passes
  that were skipped are listed here.
- **Selected Pass**: details of the pass object you selected: **Edit Particle Instances** (only on a pass made of particle sprites), **Enable Geometry Node Editing**, a bake-state hint and **Pass Material** (gamma and emission).

### Editing the generated nodes

**Enable Geometry Node Editing** (per pass, viewport only) shows the live node tree instead of the stored bake so that your edits appear at once; renders ignore it and keep reading the bake. It is not the same as **Live Effect Preview**, which only controls whether *Python-backend* passes recompute when the frame changes.

A typical loop: turn on **Enable Geometry Node Editing**, edit in the stage frames (**Edit Source Mesh**, **Edit Final Geometry**, or **Edit Particle Instances** for particle sprites), check the viewport, then press **Bake Changed**. The Selected Pass tab warns "Edits are not baked yet: Bake Changed" while the bake is stale.

## Baking

Baking stores the evaluated geometry for every frame, so playback and rendering read stored data instead of evaluating
the effect. Open the **Scene Bake** sub-panel.

| Control                                | What it does                                                                                                                                                                              |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Store**                              | **Packed in .blend** keeps bakes in the file; **Disk** writes them to the **Bake Folder**                                                                                                 |
| **Bake Folder**                        | Disk bakes go here. Default `//mme_bake/`                                                                                                                                                 |
| **Share Bakes** (disk only)            | Keeps bakes in the shared cache, named by what they were baked from, so another project with the same effect and animation reuses them ([Cache](../how-it-works/cache.md#shared-bake-store)) |
| **Folder per Pass** (disk, not shared) | Each pass bakes to its own folder named after the `.blend` and pass, so copies of the file never overwrite each other's bakes                                                             |
| **Bake Changed**                       | Bakes only passes whose stored bake no longer matches their inputs                                                                                                                        |
| **Force Rebake All**                   | Rebakes everything                                                                                                                                                                        |
| **Clear All**                          | Removes every bake; passes evaluate live again                                                                                                                                            |

The frame range is the scene's frame range. **Clear Shared Bakes** (disk and sharing on) empties the shared store.

<!-- prettier-ignore -->
!!! tip "Bake memory"
    Blender keeps every baked frame of a pass in RAM, including disk bakes. FX drops the attributes that only the
    material needs before the Bake node to reduce that, but very heavy effects over long frame ranges still need plenty of
    RAM while baking.

## Add-on Preferences

In the extension's preferences (**Edit > Preferences > Add-ons**). Standalone FX has its own page; the Bundled extension shows one NineSync page with Core and FX sections:

| Preference                 | Default                          | Meaning                                                                                                                                |
| -------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Cache Folder**           | empty = a folder belonging to the installed extension | Where parsed `.x` geometry, pre-cull, strip and gate results and shared bakes are kept. The standalone FX and the Bundled extension have different default folders, so set the same folder in both to share it |
| **Cache Limit (MB)**       | 512                              | Least recently used cache files are deleted above this                                                                                 |
| **Shared Bake Limit (MB)** | 4096                             | Least recently used shared bakes are deleted above this                                                                                |

## Core Node Library

Shared node groups live in a library file, `mme_core.blend`. Most users never touch this. See
[Shared Node Library](../how-it-works/shared-library.md) for what it holds. In the **Core Node Library** panel:

- **Open FX Library .blend** opens the file FX reads and writes.
- **Grow Library Automatically** adds newly built shared groups to the library.
- **Save to Library** writes this file's shared groups to the library.
- **Rebuild Standard** rebuilds the standard groups for your Blender version while keeping groups from imported effects. Use it if effects stop building after a Blender update.
