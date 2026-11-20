# Generated Attributes

FX's Geometry Nodes passes pass information between nodes as **named attributes**. You can read them with a **Named Attribute** node, or select and transform geometry with them, in one of the [stage frames or the particle stages](../how-it-works/geometry-nodes-translation.md#the-pass-wrapper-and-the-pass-group) of a pass, or anywhere else in a pass group you edit. Which attributes exist depends on **where** in the pass you are, on **which domain** (point, instance) and on **which branch** the pass takes. This page is the reference; the names are defined in `common/constants.py` and `nodes/names.py`.

## By stage, domain and branch

### Source mesh fields

| Attribute | Domain, type | Description |
|---|---|---|
| `mme_src` | Point, Integer | Index of the source vertex in the accessory's `.x` mesh that this output vertex was made from. |
| `mme_p`, `mme_n`, `mme_uv` | Point, Vector | Source position, normal and UV of the vertex as the shader reads them. They exist only while the vertex shader needs them. The realized branch strips them before the Bake node; on the [instanced branch](../how-it-works/geometry-nodes-translation.md#3-the-affine-check-and-the-instanced-branch) the instanced material reads them from the source mesh, so they stay on it. |

### Loop and realized-branch attributes

| Attribute | Domain, type | Description |
|---|---|---|
| `mme_inst` | Point, Integer | Loop instance index: which copy of a looped effect (for example one of `LineNum` strips) the point or vertex belongs to. 0 when the pass has no loop. |
| `mme_cull` | Point, Float | Marks a vertex the effect culls at the current settings; read by the material (`Visible = 1 − culled`). Not intended for editing. |
| `mmeV_<SEMANTIC>_<k>` | Point, Float | A *varying*: component `k` of a value the vertex shader hands to the pixel shader (for example `TEXCOORD1`). Written on the **realized** branch; read by the pass material. |
| `mmeL_<variable>` | Point, Float | The value of a loop variable of the vertex shader at that vertex. In the realized branch it is stored per vertex; in the instanced branch the material reads it from the instance. |

### Particle-point data (`Edit Particle Points`)

These live on the **points**, one per loop copy, and exist only between the per-particle shader stage and the instancing of the points ([Per-Particle Shader Stage](../how-it-works/geometry-nodes-translation.md#2-the-per-particle-shader-stage)).

| Attribute | Domain, type | Description |
|---|---|---|
| `mme_pp_*` | Point | Values computed once per copy by the per-particle group, which the per-vertex part samples back. Editing them changes that copy's shader inputs. Removed from the points that are instanced, so they never reach the realized mesh. |
| `mme_point` | Point, Integer | Each point's index *after* your edits to the points, so a deleted, duplicated or moved point still reads its own values. Dropped before the output. |

### Sprite-instance attributes (particle-sprite passes)

| Attribute | Domain, type | Description |
|---|---|---|
| `mme_sprite` | Point, Integer | Identifies the sprite a vertex belongs to in a particle pass. Exists only in the instance-editing frame; removed after **Realize Instances**. |
| `mme_size` | Float (domain not documented) | The side length of a sprite, used to scale the **Particle Mesh** replacement. Removed after realising. |
| `mme_nrm` | Vector (domain not documented) | The sprite's facing direction; the **Particle Mesh** replacement is aligned to it. Removed after realising. |

### The instanced material's private inputs

These are written on the **instanced branch** only, and are read by the *instanced material*, not by you. They are listed so that you do not mistake them for part of the realized output.

| Attribute | Domain, type | Description |
|---|---|---|
| `mmeA_<SEMANTIC>_<k>_k`, `_p`, `_n`, `_uv` | Instance | Per-copy coefficients that rebuild varying `<SEMANTIC>_<k>`: a constant (`k`) plus a weight on the vertex position (`p`), normal (`n`) or UV (`uv`). The material combines them with the vertex's own `mme_p`, `mme_n` or `mme_uv`. Removed before the output of the ordered (MMD Order) branch. |
| `mme_w*`, `mme_col*` | temporary | Reference-vertex weights and transform columns used while the instanced branch is built; removed before the output. |

## When each one is available

| Stage | What exists |
|---|---|
| **Edit Source Mesh** frame (wrapper) | the source mesh as imported; `mme_p`, `mme_n` and `mme_uv` are taken *from this mesh after your edits*, so edits here reach the shader |
| Inside the pass group, before the shader | `mme_p`, `mme_n`, `mme_uv`, `mme_src`, `mme_inst` |
| **Edit Particle Points** | the points with `mme_inst`, `mme_pp_*` and `mme_point` |
| After the vertex shader, realized branch | `mme_src`, `mme_inst`, `mme_cull`, `mmeL_*`, `mmeV_*` |
| Sprite pass, **Edit Particle Instances** frame | the sprites as instances; `mme_sprite` is available to select them |
| After **Realize Instances** (sprite frame) | `mme_sprite`, `mme_size` and `mme_nrm` are removed |
| **Edit Final Geometry** frame | the finished pass geometry: what the Bake node will store |
| After the **Bake** node | only what the material needs: `mmeV_*` (realized branch) and the source index and loop instance. The source fields are dropped to save memory |

Python-backend passes write `mme_src`, `mme_inst`, `mme_cull`, loop and varying values into the mesh instead of computing them in nodes, so they are readable there too. A Python pass has no stage frames.

## Using them

- **Select** geometry by reading an attribute into a selection, for example *Named Attribute* (`mme_inst`) → *Compare* → *Delete Geometry*, to hide one strip of a looped effect. Do it in **Edit Final Geometry** (point domain) or on the points in **Edit Particle Points**, depending on whether you want to remove vertices or whole copies.
- **Transform** per vertex or per instance by feeding an attribute into *Set Position*, or into *Instance on Points* rotation or scale fields.
- **Do not rename or remove** `mmeV_*`, `mmeL_*` or `mmeA_*`; the materials read them by name, and a missing varying reads as 0.
- Attributes that are removed after realising are not available on realised geometry. Use a stage that comes *before* the removal, and use only attributes the **branch you chose** has: a custom shader that reads `mmeV_*` works on the realized branch, but on an instanced pass the same value is rebuilt from `mmeA_*` inside the instanced material and is not stored as `mmeV_*` on the geometry.

The examples [Custom Geometry Nodes with Instances](../../../examples/custom-instances.md) and [Custom Shaders with Noise and Voronoi](../../../examples/custom-shaders.md) use these attributes in practice.
