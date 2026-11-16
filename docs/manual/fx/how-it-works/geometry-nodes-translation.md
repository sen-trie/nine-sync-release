# MME Translation to Geometry Nodes

The **vertex shader** of an MME effect moves vertices. FX reads that HLSL code and writes the equivalent Geometry Nodes
graph. This page goes through two tests:

- the **Synth** test effect that ships in the FX repository (`tests/fixtures/Synth/synth.fx`), which exercises one of
  every construct, and
- a **lightning effect** (Thunder lv2) built in Blender.

## How an MME vertex shader becomes nodes

### The interpreter does the work, the backend writes the nodes

FX contains one HLSL interpreter, `FxExec`. It is not a true HLSL compiler, it _runs_ the shader symbolically. Every value in
the shader is either

- a **known number** (a constant, or a parameter value frozen at build time), which is folded away, or
- a **node output** (something that changes: a vertex position, `Tr`, the loop index), which is wired into a node.

`MmeGeoBackend` is the backend that turns operations on node outputs into nodes. Identical operations are cached so the
graph reuses nodes, and constants never produce a node at all. The same interpreter drives the Python backend, which emits numpy
arrays instead.

**Why it was built this way:** an artist who opens the graph should see roughly the arithmetic they would recognise
from the `.fx`, not a wall of constants. It also means anything the interpreter cannot decide at build time is the
thing that cannot become nodes ([see below](#when-an-operation-cannot-be-translated)).

### Operation dictionary

<!-- prettier-ignore -->
| HLSL | Blender node | Notes |
|---|---|---|
| `+ - * /` on floats | **Math** (Add, Subtract, Multiply, Divide) | labelled `+`, `-`, `*`, `/` |
| `abs sign floor ceil trunc round frac sqrt rsqrt exp sin cos tan asin acos atan sinh cosh tanh` | **Math** with the matching function | table `MME_NODE_UNARY` in `nodes/backend_base.py` |
| `a ? b : c`, `if / else` | **Switch** nodes (one per value that differs) | both branches are evaluated; the switch picks one |
| `smoothstep(a, b, x)` | **Map Range** (smooth step) | seen in the Line pass below |
| `saturate(x)` | **Clamp** | |
| `a & b`, `a | b`, `a ^ b`, `<<`, `>>`, `~` in a **vertex** shader | **Bit Math** | not available in a pixel shader |
| `mul(float4, float4x4)` etc. | a **shared node group** built on **Matrix Multiply** | HLSL uses row vectors, Blender column vectors; the group transposes when needed |
| `normalize`, `cross`, `dot`, `length`, vector `+ - *` | **Vector Math** | |
| `float4x4` values | Matrix sockets, split with **Separate Matrix** | |
| a user HLSL function (`inv_pow`, `getRandom`) | a shared group `MME fn <name>` | keyed by a hash of the function, so a second effect with the same function reuses it |
| `tex2Dlod` in a vertex shader | **Image Texture** (geometry) | |
| `LoopByCount` / `LoopGetIndex` | **Points → Instance on Points → Realize Instances**, with **Integer Math** for the index | [see Loops](#loops-and-instances) |

### Example of statement mapping

Three statements from the Thunder Line pass (`LineFunc`) and the nodes FX generated for them.

<!-- prettier-ignore -->
| HLSL statement | Generated nodes |
|---|---|
| `float mt = inv_pow(1 - Tr, 2) * 0.5;` | a **Math** node (`1 - Tr`), the group **MME fn inv_pow**, a **Math** multiply named `mt` |
| `float t = smoothstep(0 + index_rnd.y*0.5, 0.2 + index_rnd.y*0.5, 1-Tr);` | three **Math** nodes and a **Map Range** labelled `smoothstep` |
| `CenterPos.xyz = mul(CenterPos.xyz, matRot);` | **Combine XYZ**, **Combine Matrix** and the shared group **MME mul(float3,float4x4)** |

The whole Line vertex shader compiles to **201 nodes** inside one group (111 Math, 35 frames, 12 groups, 9 Combine XYZ,
7 Vector Math, 6 Switch and 3 Clamp among them), plus shared groups for the camera, the object matrix and the clip-space
conversion.

<!-- prettier-ignore -->
!!! note "Why 'Math' dominates"
    Blender's Math node does one scalar operation. A vector expression in HLSL such as `a * b + c` on a `float3` becomes
    three scalar multiplies and three scalar adds, unless a Vector Math node can express it directly.

## A real generated graph

The graph below is the **pass group** of the Thunder _Line_ pass (`MME Pass Thunder_MainTec1_Line`). It is a layered
redraw of the real node tree: nodes, labels and links are the generated ones, but positions are re-laid for the page.
Scroll sideways to read left to right.

<div class="graph-scroll"><img src="../../../../assets/images/fx/thunder-line-pass.svg" alt="Generated Geometry Nodes pass group for the Thunder Line pass" height="330"></div>

Reading it from left to right:

1. **Inputs.** `Group Input` supplies the geometry, **Effect Density**, the loop-count parameter **LineNum** and **Tr**.
   Named Attribute nodes read `mme_p` (the source vertex position) and `mme_uv` from the mesh.
2. **LoopByCount** (frame). _Math_ nodes compute the loop count (`LineNum × Effect Density`, rounded, at least 1).
   **Points** makes that many points, **Store Named Attribute** writes each point's index as `mme_inst`,
   **Instance on Points** puts one copy of the mesh on every point, and **Realize Instances** turns the copies into one
   mesh. **Integer Math** turns `mme_inst` back into the shader's `g_index`.
3. **Vertex shader** (`MMEffects`, the 201-node group). Everything the HLSL does per vertex.
4. **Clip space to object space.** MME vertex shaders end by writing a **clip-space** position
   (`Out.Pos = mul(Pos, ViewProjMatrix)`). Blender needs a position in the object's own space, so FX multiplies back
   through the camera: the groups **MME Camera (MMD)** and **MME Blender to MMD matrix** supply the matrices, and
   **MME Clip to object (MMD)** converts. This is also why effects that billboard towards the camera follow Blender's
   active camera.
5. **Set Position.** Vertices are moved there. Vertices MMD would have culled collapse to the origin.
6. **Store Named Attribute** writes what the **material** needs: `mme_cull`, and the shader's outputs as
   `mmeV_TEXCOORD1_0`, `mmeV_TEXCOORD1_1`, `mmeV_TEXCOORD6_0` (the `Tex` and `Alpha` values; the name is `mmeV_` +
   semantic + component).
7. **Strip unused attributes**, then **Hide at Tr = 0** (a **Switch** that outputs empty geometry when `Tr ≤ 0`; added
   only to passes that FX proved are empty at Tr = 0).
8. **Bake** (`NineSync Bake`) and the **Group Output**.

The pass group sits inside a one-node wrapper group named `MME <pass label>`, which is what the object's modifier uses.
Particle passes (meshes of quads) have a larger wrapper; see [Particles](#particles-and-instance-editing).

<!-- prettier-ignore -->
!!! tip "Open it yourself"
    Select a pass object, open a **Geometry Nodes** editor, and look at the **MME** modifier. Press **Tab** on the group
    node to enter it; **Tab** again to leave.

## Loops and instances

MME effects often draw the same mesh many times, each with a different index (`LoopByCount=LineNum;
LoopGetIndex=g_index;`). In FX:

1. The loop count is `max(1, round(parameter × Effect Density))`. With several nested loops the counts multiply.
2. **Points** makes that many points. Each gets its index stored as the integer attribute `mme_inst`.
3. **Instance on Points** + **Realize Instances** make real geometry: one copy of the (already reduced) mesh per point.
4. The loop variable is recovered by **mixed-radix decomposition** (`Integer Math`: divide and modulo) from `mme_inst`,
   so nested loops produce the right per-loop indices.
5. For the material, the loop index is stored per vertex as `mmeL_<variable>`.

<!-- prettier-ignore -->
!!! warning "Realize Instances is the expensive step"
    After **Realize Instances**, every copy is real geometry, so memory and bake size grow with the loop count. Pruning before this stage (see
    [Culling](culling.md)) is what keeps the node graph performant. the Thunder _Line_ pass instantiates 140 vertices 28 times
    (3,920 evaluated vertices), instead of 20,000-face meshes which it originally came with.

## Attributes FX writes

<!-- prettier-ignore -->
| Attribute | Domain | Meaning | Used by |
|---|---|---|---|
| `mme_src` | point | index of the vertex in the merged `.x` mesh | matching vertices in tests and tools |
| `mme_p`, `mme_n`, `mme_uv` | point | source position, normal and UV | the vertex shader inputs (removed before the Bake node) |
| `mme_inst` | point | loop copy number | loop index decomposition |
| `mme_cull` | point | 1 where MMD would cull the vertex | material alpha |
| `mmeV_<SEMANTIC>_<k>` | point | a vertex-shader output component | the material's pixel shader |
| `mmeL_<var>` | point | a loop index | the material's pixel shader |

## From MME parameters to Blender controls

### How FX decides what to expose

FX scans the `.fx` globals. A global becomes an artist-facing **parameter** when **all** of these hold (function
`fx_find_params` in `fx/params.py`):

- it is a plain `float`, `int` or `bool`, or a vector of up to four floats (a colour, say);
- it has **no hardware semantic** (so not `WORLDVIEWPROJECTION`, `TIME`, `POSITION`…);
- it is not `static`/`const`, not an array, not a loop counter, not one of the add-on's internal flag names;
- it has an **initial value** or a **UI annotation**, and is not marked `UIVisible = false`.

### What it looks like: the Synth effect

<!-- prettier-ignore -->
| In `synth.fx` | Blender control | Why |
|---|---|---|
| `float Spread < UIWidget="Slider"; UIMin=0; UIMax=10; > = 2.5;` | root property `mmeP_Spread`, slider 0–10, default 2.5; modifier input **Spread** (driven) | an obvious artist knob; the range comes from the annotations |
| `float3 Tint < UIWidget="Color"; > = float3(1, 0.5, 0.25);` | root property `mmeP_Tint` (colour); inputs **Tint.x / .y / .z** | colours are edited as colours |
| `int Copies = 4;` | root property `mmeP_Copies`; input **Copies**; also the loop count | structural: changes how many copies exist |
| `bool Hidden < bool UIVisible=false; > = true;` | **not exposed** | the author hid it |
| `float Time : TIME;` | **not a parameter**: it becomes the **ElapsedTime** / scene-time input | MMD supplies it, not the artist |
| `float4x4 WVP : WORLDVIEWPROJECTION;` | not a parameter: built from the camera and object groups | MMD supplies it |
| `float Tr : CONTROLOBJECT < string name="(self)"; string item="Tr"; >` | modifier input **Tr**, driven from `mme_tr` on the accessory | opacity from the PMM |

(These come from a real build of the Synth fixture: the Geometry Nodes pass has the inputs _Effect Density, Copies, Spread,
Tr, Tint.x, Tint.y, Tint.z, Viewport width, Viewport height, ElapsedTime_.)

### And the real effect

Thunder lv2 declares `MainColor`, `ParticleNum`, `LineNum`, `FlashNum` and `WaveNum`. FX stores all five on the root. The
_Line_ pass's modifier shows only **Effect Density**, **LineNum** and **Tr**, because that pass's shader reads only
those: the others are not wired into it. `MainColor` is read by the pixel shader, so it reaches the material through
the pass object's `mmeU_MainColor_0..2` custom properties, which are driven from the root.

<!-- prettier-ignore -->
!!! info "Parameters stay on the root"
    You edit values on the accessory root (**Selected Effect > Effect Parameters**). The modifier inputs and material
    uniforms are driven from there. Editing a driven modifier input directly is overwritten by the driver.

## Try it: change a value, see the result

Same built effect, rendered before and after changing the `MainColor` parameter. This is a **live** change: no rebuild, because
`MainColor` is read by the pixel shader and reaches the material as a driven value.

| `MainColor = (0, 0.75, 2)` (default)                            | `MainColor = (2, 0.25, 0.05)`                                     |
| --------------------------------------------------------------- | ----------------------------------------------------------------- |
| ![](../../../assets/images/fx/thunder-default.png){ width=420 } | ![](../../../assets/images/fx/thunder-maincolor.png){ width=420 } |

Changing `LineNum` is different: it is **structural**. The wrench icon marks it. In a measured test, changing `LineNum`
from 28 to 20 made FX report that a rebuild is needed (`mme_rebuild_needed` returned true), and the rebuild recreated all four
passes because their build signatures changed.

## A practical example: a camera-facing ribbon

The _Line_ pass turns thin quads into a bolt that always faces the camera. The relevant HLSL (shortened) is:

```hlsl
float3 V = normalize(CenterPos - NextCenterPos);   // along the bolt
float3 E = normalize(CameraPosition - CenterPos);  // towards the camera
float3 side = normalize(cross(E, V)) * 1.5 * 10 * length(WorldMatrix[1]) * 0.1 * 0.5;
Pos.xyz = CenterPos.xyz;
if (PosBuf.x > 0) { Pos.xyz += side; } else { Pos.xyz -= side; }
```

**What it does for an artist:** each vertex of the ribbon is pushed left or right, perpendicular to both the bolt's
direction and the direction to the camera, so the ribbon is always seen face-on. This is a **spatial relationship** (bolt
direction × camera direction) plus a **deformation** (offset by `side`).

**What FX generates:** a **Vector Math** _normalize_ for `V` and `E` (frames `float3 V…`, `float3 E…`), a **Vector Math**
_cross_ for the perpendicular, **Switch** nodes for the `if (PosBuf.x > 0)` branches (both sides are computed, the
switch picks one per vertex), and finally the clip-space conversion. `CameraPosition` is a group input fed from Blender's
active camera, so moving the camera in Blender rotates the ribbons.

**What you can change safely:** none of the nodes need editing for artistic control. Use the exposed values: **LineNum**
(how many bolts; structural), **MainColor** (colour; live), **Tr** (progress; live), **Effect Density** (preview
speed). Editing nodes inside the generated group is possible but fragile, as the next section explains.

## Customising the generated graphs

### What is safe

- **Changing exposed values.** Always safe and always preserved.
- **Reading and learning.** Open any generated group; frames are labelled with the HLSL line that produced them.
- **Adding your own nodes** on an object that you do not intend to rebuild, or in the place FX provides for it
  ([particle passes](#particles-and-instance-editing)).
- **Your own Bake nodes.** FX acts only on the node named `NineSync Bake`.

### Which edits survive rebuilds

These results come from a controlled test in Blender: a node was added to a pass group and the gamma
of its material was edited, then the effect was rebuilt under different conditions.

<!-- prettier-ignore -->
| Action | Pass group (your added node) | Material (gamma edit) | Bake |
|---|---|---|---|
| Rebuild with **nothing changed** | kept | kept | kept (**Bake Changed** skips it) |
| Rebuild after an input the pass reads changed (even a pixel-shader colour) | **lost**: the pass is replaced by a new tree | kept once: FX logs *material was edited; only its pixel shader group was regenerated* | cleared when the pass is dropped |
| A second rebuild after that | lost again if the pass changes again | **reset to the default** | |
| **Force Rebuild All** | lost | reset | cleared |
| Editing a node upstream of the Bake node | – | – | the bake becomes **stale** and is cleared; the pass evaluates live until you rebake |

<!-- prettier-ignore -->
!!! warning "Rule of thumb"
    Treat generated node trees as **disposable output**. Put lasting artistic changes in the exposed parameters. If you
    modify a tree, keep a note of the change and expect to re-apply it after a rebuild. The material edit that
    survived one rebuild did not survive the next: this is how FX behaved in the test, and it has been reported to the FX
    maintainers.

### What survives regardless

- Parameters on the root (`mmeP_*`): kept when they still fit; properties the effect no longer declares are removed.
- Visibility flags and the action (keys) on a pass object: carried over when only that pass is replaced.
- Passes whose build signature did not change: **everything**, including your node edits and the bake.

## Particles and instance editing

A pass whose mesh is made of quads (one quad per particle) gets a larger wrapper group. After the Bake
node it adds a frame titled _Add your nodes (Ensure "Enable Instance Editing" is checked)_ containing:

1. **Particles to Instances**: one instance per particle, placed at the particle's centre;
2. a **Delete Geometry** node in the _Instance_ domain (a placeholder with selection `False`: put your own logic here);
3. **Realize Instances** and removal of the internal `mme_sprite` attribute;
4. a **Switch** driven by the group input **Enable Instance Editing** (off by default, because it costs far more than the
   pass itself on large effects);
5. **Particle Mesh (optional swap)**: an object input; when set, its mesh replaces each particle.

Everything here sits _after_ the Bake node, so editing it never invalidates a bake.

## When an operation cannot be translated

FX never guesses. It tries the Geometry Nodes build first; when the interpreter meets something that needs a value it
cannot know without running the shader per vertex, it raises _unsupported_, and **only that pass** falls back to the Python
backend. The effect continues with the other passes on Geometry Nodes.

<!-- prettier-ignore -->
| Cause | Message in the log | Example in the Synth fixture |
|---|---|---|
| A loop whose count depends on vertex data | `data-dependent loop` | `for (int j = 0; j < (int)(Tex.x * 4 + 1); j++) { acc += 0.1; }` |
| An unknown intrinsic function | `unknown function <name>` | – |
| A struct constructor | `struct constructor` | – |
| An array whose size is not a constant | `array size is not constant` | – |
| A function call chain deeper than the limit | `call depth exceeded` | – |
| A loop that never ends within the limit (4,096 iterations) | `loop did not finish` | – |

A real example, from building the Synth fixture:

```text
effect pass Synth_T_P1: vertex shader cannot run in Geometry Nodes (data-dependent loop); using the Python backend
effect pass Synth_T_P1: Python, 49 vertices, 72 faces, 1 instance(s), fallback material
```

**What changes for you:** that pass has no node tree to edit (the geometry is written into the mesh each frame, and its
tree only holds the Bake node), its **Live Effect Preview** follows the setting, and the **Passes** tab shows **Python**
beside it. The rest of the effect is unaffected.

## Related pages

- Source: [`nodes/geo_tree.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/geo_tree.py),
  [`nodes/backend_geo.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/backend_geo.py),
  [`nodes/geo_sprites.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/geo_sprites.py),
  [`fx/params.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/fx/params.py)
