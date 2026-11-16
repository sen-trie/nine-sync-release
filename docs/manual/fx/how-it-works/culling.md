# Culling and Geometry Optimization

Many MME accessories are built far larger than what they ever show. Thunder lv2, the effect used throughout this manual,
has meshes with 20,000 to 30,000 faces per pass, copied 28 or 64 times, to draw a few lightning bolts. Building all of it
would produce tens of millions of vertices.

So **before** FX builds any node, it works out which parts of each pass can never appear on screen and **removes them from
the mesh**. This page explains how that is decided, what it costs, and when you can trust it.

<!-- prettier-ignore -->
!!! info "Order matters"
    Culling runs _before_ the Geometry Nodes tree is generated (see [FX Architecture](index.md#the-pipeline)). The nodes
    you see in Blender operate on the already-reduced mesh. It is not a node you can toggle.

## The stages

For each pass, `mme_build_pass` (in `runtime/build_pass.py`) does the following in order:

<!-- prettier-ignore -->
| Stage | Question it answers | Code |
|---|---|---|
| **Alpha gates** | Does the pixel shader make a pixel invisible when some vertex output is ≈ 0? | `mme_alpha_gates` |
| **Pre-cull** | For which vertices does the vertex shader ever put the vertex on screen, or open a gate, under realistic conditions? | `mme_prune_mask` |
| **Prune faces** | Keep only faces that touch a kept vertex (and an open one, when there are gates) | `mme_keep_faces` |
| **Grow margin** | Add rings of neighbouring faces so a gate that opens slightly away from a vertex leaves no hole | `mme_grow_faces` |
| **Strip simplification** | Merge rows of ribbons and rings that the shader could recreate by interpolation | `mme_simplify_strip` |
| **Empty at Tr = 0** | Can the pass be switched off completely when opacity is 0? | `mme_empty_at_zero_tr` |

The build log reports the result for each pass in one line:

```text
effect pass <label>: <kept> of <before> faces kept (<n> never drawn, <n> always transparent via <semantic>.<component>, <n> merged along strips) in <t>s (alpha gates …, pre-cull …, strips …)
```

### Alpha gates

A **gate** is a vertex-shader output (for example the `x` of a `TEXCOORD`) that the pixel shader multiplies into its
alpha. If setting it to almost zero makes the pixel shader return alpha ≈ 0 for every random probe, but the unmodified
values are visible somewhere, FX treats it as a gate. Vertices whose gate is _closed_ never show.

How it is tested (`mme_alpha_gates` in `runtime/pruning.py`):

- the pixel shader is run in numpy on **96 random probes** (`MME_GATE_PROBES`);
- a component is forced to `1e-5` (`MME_GATE_EPS`);
- "invisible" means alpha ≤ `1/512` (`MME_GATE_ALPHA`);
- the test only counts under a blend state in which alpha 0 really draws nothing (`mme_alpha_scaled`): source-alpha
  blending, added with ONE or inverse source alpha. For opaque or multiply passes alpha 0 proves nothing, so no gate is
  used.
- if anything fails or is uncertain, the result is "no gates". Culling never guesses.

### Pre-cull

The vertex shader is run in numpy for **every vertex** of the pass (and every loop copy) under a set of probe
conditions, and FX records which vertices ever land inside the view, or open a gate:

- opacity (**Tr**) samples of `1.0, 0.8, 0.6, 0.4, 0.2, 0.0` (`MME_PRUNE_TR`);
- parameter extremes and the keyed variants of the effect (parameters or controllers that are animated in the PMM).

A vertex that never shows in any of those states is dropped, along with the faces that only touch dropped vertices.
This is the expensive stage. Its result is cached on disk so that a re-import, a copy of the effect or a rebuild with
unchanged inputs skips it ([Cache Architecture](cache.md)).

<!-- prettier-ignore -->
!!! warning "Culling is based on sampled states"
    Pre-cull evaluates the shader under a finite set of states (the Tr samples, parameter extremes and keyed variants
    above), not every possible state. An effect driven in a way that those samples do not cover could lose geometry that
    MMD would show. The source does not try to detect that case. If you suspect it, **Clear Effect Caches**, rebuild, and
    compare against MMD; then report the effect to the FX maintainers.

### Prune faces and grow the margin

Faces are kept when they touch a kept vertex. When gates are in use, the face must touch both a kept vertex and an
_open_ one, and then a **margin of 2 rings** of neighbouring faces is added (`MME_GATE_MARGIN`). The margin exists
because a gate is judged per vertex but the pixel shader interpolates it across the face, so a gate that opens in the
middle of a face would otherwise be cut.

### Strip simplification { #strip-simplification }

Beams, trails and rings in MME effects are usually **strips**: a ladder of rows of vertices, each row the same width,
with faces only between neighbouring rows. Thunder's rings use thousands of rows to make a smooth curve. When the vertex
shader's output between two rows is almost a straight interpolation of their neighbours, the middle rows add nothing.

FX detects the layout (`mme_strip_layout`: UV rows form a ladder, at least 16 vertices, at least 8 distinct rows, faces
only between adjacent rows) and then **recursively splits** each span at the row that interpolates worst, until every
remaining row interpolates within the tolerance (`mme_simplify_prepared`):

- the error is measured on **positions and on every vertex-shader output that varies** (UVs, alpha, colour), not on
  positions alone, over all the probe runs (Tr samples `1.0, 0.9, 0.75, 0.6, 0.45, 0.3, 0.15, 0.0`, parameter extremes
  and up to 8 keyed variants);
- the tolerance is relative to the effect's size. The **Geometry Tolerance** setting is the share; the default is
  **0.0005** (0.05 %), the maximum 0.05. **0 turns simplification off** and keeps every row;
- rows where a lane's cull state changes are always kept, so merging never moves the boundary of the culled region;
- there is a **15-second time budget** per run of rows (`MME_SIMPLIFY_BUDGET`). If it runs out, the remaining rows are kept
  as they are. That is a quality-safe fallback, not an error;
- a span of 3 rows or fewer is kept unchanged;
- results are cached per run of rows (key includes the probe conditions, camera, tolerance, loop instances and density).

<!-- prettier-ignore -->
!!! note "Not a lossless step"
    This is the only stage that can change the look. Pre-cull and alpha gates remove things that were never visible
    under the probed states; strip simplification removes rows that were _almost_ redundant. Lower **Geometry Tolerance**
    if you see faceting, then **Rebuild**.

### Empty at Tr = 0

If the effect reads the accessory's opacity (`Tr`) and a pass draws nothing when it is 0, FX adds the **Hide at Tr = 0**
switch seen at the end of the Geometry Nodes pass. It is only added when one of two tests proves it
(`mme_empty_at_zero_tr`): every vertex is clipped when the vertex shader runs with Tr = 0, or the pixel shader returns
alpha 0 for random inputs, under a blend state where alpha 0 draws nothing. A pass that fails both tests never gets the
switch.

A pass that is empty at _every_ state is removed entirely and remembered, so a later rebuild does not try it again.

## Effect Density and Build Memory

Two settings change how heavy the analysis is without changing what the analysis decides:

<!-- prettier-ignore -->
| Setting | Effect on culling |
|---|---|
| **Effect Density** | Scales the loop count, so fewer loop copies are analysed and built. It *does* change what you see (fewer copies). See [Geometry Nodes Setup](../geometry-nodes.md#the-settings-panel) |
| **Build Memory** | Low / Balanced / High: the number of vertices per shader batch in pre-cull and strips, and whether large strip buffers are file-backed in the temp folder (Low only). `MME_MEMORY_BUDGETS` in `common/constants.py`. **Every budget gives the same result**, only the speed and peak RAM differ. |

<!-- prettier-ignore -->
| Budget | Vertices per batch (pre-cull) | Vertices per batch (strips) | Scoring block | File-backed buffers |
|---|---|---|---|---|
| Low | 262,144 | 65,536 | 64 MB | yes |
| Balanced | 4,194,304 | 262,144 | 256 MB | no |
| High | unbounded | 1,048,576 | 1,024 MB | no |

## A real run: Thunder lv2

Measured in headless Blender with a development build of FX, on one development machine, with Thunder's own defaults
(LineNum 28, ParticleNum 64, FlashNum 1, WaveNum 1). Your numbers will differ with the machine, but the face counts come
from the algorithm, not the machine.

The effect has 5 draws. One of them (_MainPass_, 1,984 faces) is empty after culling, so **4 pass objects** are built.

| Pass     | Faces in | Faces kept | Why                        | Evaluated vertices (kept × copies) |
| -------- | -------- | ---------- | -------------------------- | ---------------------------------- |
| Particle | 30,000   | 128        | 29,872 never drawn         | 7,168                              |
| Flash    | 30,000   | 2          | 29,998 never drawn         | 112                                |
| Line     | 20,000   | 138        | 19,862 always transparent  | 3,920                              |
| Wave     | 20,000   | 314        | 19,686 merged along strips | 8,848                              |

Reading the table:

- **Particle** and **Flash** are billboard sprites: nearly every face of the big source mesh is a particle that the
  vertex shader never places on screen, so pre-cull removes them (_never drawn_).
- **Line** has a gate: the alpha of most of its faces is always zero (_always transparent_).
- **Wave** is a ring built from thousands of rows; simplification merges the rows that interpolate (_merged along strips_).

| Build                                  | Time                                                                       |
| -------------------------------------- | -------------------------------------------------------------------------- |
| **Cold** (nothing cached)              | 49.8 s (pre-cull 39.7 s, strips 6.7 s)                                     |
| **Warm** (same folder, caches present) | 3.4 s, identical face counts                                               |
| **A renamed copy in another folder**   | 3.5 s, log: _57 of 57 visibility states known_, cache file count unchanged |

The last row shows that the caches are keyed by **content**, not by file name or path. See
[Cache Architecture](cache.md#how-keys-are-built).

## When something is missing

<!-- prettier-ignore -->
| Symptom | Likely cause | What to do |
|---|---|---|
| Part of a ring or trail looks faceted or cut after a rebuild | Strip simplification (the only stage that can alter the look) | Lower **Geometry Tolerance** (0 disables simplification), then rebuild |
| A draw in the `.fx` has no pass object | After culling it had no faces, or it is a full-screen pass | Turn on **Detailed Build Log** and read the line for that pass; full-screen passes are listed in **Passes** |
| Geometry missing that MMD shows | The pass was judged by sampled states that did not cover your use | **Clear Effect Caches**, rebuild, and report it with the `.fx` |
| First build takes minutes | Pre-cull evaluates heavy effects once | Later builds read the cache. **Build Memory: Low** lowers peak RAM, not time |

## Related pages

- Source: [`runtime/build_pass.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/runtime/build_pass.py),
  [`runtime/pruning.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/runtime/pruning.py),
  [`runtime/strips.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/runtime/strips.py),
  [`runtime/precull.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/runtime/precull.py)
