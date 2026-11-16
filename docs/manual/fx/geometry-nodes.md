# Geometry Nodes Setup

The **vertex shader** of an MME effect decides where every vertex of the accessory ends up (spread, wobble, billboard,
trail…). FX compiles that shader into **Geometry Nodes** so effects move, deform and render in Blender without running
Python on every frame. Pixel shaders become [shader nodes](shader-nodes.md) instead.

If you have never opened Geometry Nodes, it is a system that lets you procedurally generate and animate 3D geometry. [How MME becomes Geometry Nodes](how-it-works/geometry-nodes-translation.md) shows how graph nodes are generated from a .fx file.

## The settings panel

<!-- SCREENSHOT: NineSync: FX Importer panel -->

<!-- prettier-ignore -->
| Setting | Why FX exposes it | Affects | Live or rebuild |
|---|---|---|---|
| **Effect Backend** (Geometry Nodes / Python) | Some vertex shaders cannot be expressed in nodes; Python can run any of them, slowly | how every pass is built | rebuild |
| **Effect Density** | Heavy effects draw tens of thousands of copies; scrubbing at a fraction is much faster. 1 matches MMD | loop counts of every pass | live on Geometry Nodes passes; Python passes on the next rebuild |
| **Geometry Tolerance** | Long ribbons and rings are built from thousands of rows; rows the shader can recreate by interpolation can be merged. 0 keeps every row | strip simplification ([Culling](how-it-works/culling.md#strip-simplification)) | rebuild |
| **Build Memory** (Low / Balanced / High) | Analysis of huge effects uses temporary arrays; Low trades build time for RAM. The result is identical | analysis batch sizes only | next build |
| **Auto Rebuild** | Rebuilding a heavy effect can take minutes, so it is off by default | whether geometry-changing edits rebuild by themselves | – |
| **Detailed Build Log** | Logs every changed input behind a rebuild, rebake or skip | the log only | – |
| **Pre-cull Cache** | Remembers which vertices can never be drawn so a rebuild skips that analysis ([Cache](how-it-works/cache.md)) | analysis speed | takes effect on the next build |
| **Live Effect Preview** | Python passes recompute on every frame change; turn it off to scrub faster. Shown only with the Python backend | Python passes only | live |

<!-- prettier-ignore -->
!!! warning "Density changes what you see"
    Effect Density below 1 draws fewer copies than MMD. It is a speed tool, not a quality setting. Set it back to 1 before
    final renders.

### Choosing a backend

|                      | Geometry Nodes (default)              | Python                                                 |
| -------------------- | ------------------------------------- | ------------------------------------------------------ |
| Runs                 | inside Blender's node evaluator       | numpy, from a frame-change handler                     |
| Per-frame cost       | no Python per frame                   | Python per frame, unless baked                         |
| Renders and baking   | native                                | recomputed per frame                                   |
| Which vertex shaders | those expressible as nodes            | any the interpreter can run                            |
| Editable             | you can open and change the node tree | the geometry is written into the mesh, no tree to edit |

**You rarely need to choose Python.** FX automatically falls back to Python for a single pass whose vertex shader cannot
be compiled, and says so in the pass details and the log
([When an operation cannot be translated](how-it-works/geometry-nodes-translation.md#when-an-operation-cannot-be-translated)).

## Rebuilding

Press **Rebuild Changed Effects** after changing something that alters geometry. A rebuild only redoes the passes whose
inputs changed; the others keep their objects, node trees, visibility, keys and bakes.

- **Force Rebuild All** ignores recorded inputs and rebuilds every pass.
- The button turns red when an effect is **out of date**: a geometry-changing parameter was edited while **Auto
  Rebuild** is off.
- **Clear Effect Caches** (trash icon) deletes the caches so the next build analyses everything from scratch.

What counts as "changed" is documented with the architecture:
[Incremental rebuilds](how-it-works/index.md#incremental-rebuilds).

## Per-effect values

Select an effect and open **Selected Effect** (see [Shader Nodes Setup](shader-nodes.md#effect-parameters)). Parameters with a **wrench
icon** change the geometry itself; editing them marks the effect out of date. Others update live through drivers.

## Inspecting and repairing

**Selected Effect > Effect Details** has three tabs:

- **Linked Objects**: objects, bones and morphs the effect reads.
- **Passes**: every pass, whether it runs on **Geometry Nodes** or **Python**, loop counts and flags. Full-screen passes
  that were skipped are listed here.
- **Selected Pass**: details of the pass object you selected, including **Pass Material** (gamma and emission).

## Baking

Baking stores the evaluated geometry for every frame, so playback and rendering read stored data instead of evaluating
the effect. Open the **Bake** sub-panel.

| Control                                | What it does                                                                                                                                                                              |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Store**                              | **Packed in .blend** keeps bakes in the file; **Disk** writes them to the **Bake Folder**                                                                                                 |
| **Bake Folder**                        | Disk bakes go here. Default `//mme_bake/`                                                                                                                                                 |
| **Share Bakes** (disk only)            | Keeps bakes in the shared cache, named by what they were baked from, so another project with the same effect and animation reuses them ([Cache](how-it-works/cache.md#shared-bake-store)) |
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

In the add-on's preferences (**Edit > Preferences**, then the NineSync FX entry):

| Preference                 | Default                          | Meaning                                                                                                                                |
| -------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Cache Folder**           | empty = beside your node library | Where parsed `.x` geometry, pre-cull and strip results are kept. Set the same folder in the standalone and bundled add-ons to share it |
| **Cache Limit (MB)**       | 512                              | Least recently used cache files are deleted above this                                                                                 |
| **Shared Bake Limit (MB)** | 4096                             | Least recently used shared bakes are deleted above this                                                                                |

## Core Node Library

Shared node groups live in a library file, `mme_core.blend`. Most users never touch this. See
[Shared Node Library](how-it-works/shared-library.md) for what it holds. In the **Core Node Library** panel:

- **Open FX Library .blend** opens the file FX reads and writes.
- **Grow Library Automatically** adds newly built shared groups to the library.
- **Save to Library** writes this file's shared groups to the library.
- **Rebuild Standard** rebuilds the standard groups for your Blender version.
