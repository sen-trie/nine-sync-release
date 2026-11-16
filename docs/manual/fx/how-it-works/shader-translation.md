# Shader Translation

The **pixel shader** of an MME effect decides the colour and transparency of every pixel. FX turns it into a **material**
(shader nodes) in two parts:

1. a node group **`MME PS <pass label>`** that holds your effect's own arithmetic, translated from the HLSL, and
2. a fixed **output stage** that FX adds after it. The stage depends on the pass's DirectX blend states and reproduces
   how MMD blends and gamma-corrects the result.

The pixel shader does not move vertices. Anything it needs from the vertex shader (texture coordinates, a fade value, the
loop index) arrives as a **mesh attribute** that the [Geometry Nodes pass](geometry-nodes-translation.md) stored.

## A real material

The graphs below come from the Thunder _Line_ pass, redrawn from the real node trees (layout re-computed for the
page; nodes, labels and links are the generated ones). The pass material has **17 nodes** and its pixel-shader group
has **28**.

**The material** (what you see in the Shader Editor):

<div class="graph-scroll"><img src="../../../../assets/images/fx/thunder-line-material.svg" alt="Generated material for the Thunder Line pass" height="300"></div>

**Inside the group `MME PS …`** (Tab into the group node):

<div class="graph-scroll"><img src="../../../../assets/images/fx/thunder-line-pixel-shader.svg" alt="Pixel-shader group for the Thunder Line pass" height="300"></div>

### The shader it came from

The Thunder effect uses one pixel shader for all its passes, selected by a `mode` argument. `Main_PS(…, 2)` is used by
the Line pass; the shader begins:

```hlsl
float4 Main_PS(VS_OUTPUT IN, uniform int mode) : COLOR0
{
    float t = IN.t;
    float4 Col = 1;

    if (bController)
    {
        MainColor.rgb = float3(morph_r, morph_g, morph_b) * (1 + morph_add_si);
    }

    if (mode == 0)
    {
        Col = tex2D(SampParticle, (IN.Tex * 0.5) + float2(0.5, 0.0));
        ...
```

Three things happen when FX translates it:

- `mode` is a **uniform argument**, a constant for this pass, so the interpreter folds every `if (mode == …)` at build
  time. Only the branch for this pass produces nodes. This is why a Line pass material is much smaller than the whole
  function looks.
- `IN.t` and `IN.Tex` are **vertex-shader outputs**. In the material they are **Attribute** nodes reading
  `mmeV_<SEMANTIC>_<k>`, the same attributes the Geometry Nodes pass stored.
- `MainColor` is a global that is not a semantic, so it is an exposed parameter. The pixel shader reads it, so it becomes a
  material **uniform**: a custom property `mmeU_MainColor_0..2` on the pass object, driven from the root's `mmeP_MainColor`.
  Changing it is live, with no rebuild.

## What each HLSL construct becomes

<!-- prettier-ignore -->
| HLSL | Shader node | Notes |
|---|---|---|
| `tex2D(sampler, uv)` | **Combine XYZ** → **Image Texture** → **Separate Color** (+ the texture's Alpha) | `v` is replaced by `1 - v` because HLSL texture space starts at the top and Blender's at the bottom. Samples are cached per image and coordinate |
| arithmetic, `lerp`, `saturate`, `pow`… | **Math**, **Vector Math**, **Mix**, **Clamp** | same translation tables as the vertex shader; see [Operation dictionary](geometry-nodes-translation.md#operation-dictionary) |
| `if` / `?:` on a value that varies per pixel | **Switch** / **Mix** nodes | both branches are computed |
| `if` on a constant (a uniform argument like `mode`) | nothing: folded at build time | |
| `IN.<semantic>` | **Attribute** node `mmeV_<SEMANTIC>_<k>` | |
| loop index (`LoopGetIndex`) | **Attribute** node `mmeL_<var>` | |
| global parameter read by the pixel shader | driven custom property `mmeU_<name>_<k>` on the pass object, read with an **Attribute** (object) node | |
| a user function called with a texture | not supported ([below](#unsupported-operations-and-approximations)) | |

### Textures

- The image is loaded **once per file** (matched by normalised path), with colour space **Non-Color** so that Blender
  does not add its own gamma on top of the shader's own handling.
- `ResourceName` paths are resolved beside the `.fx`; case is ignored and another extension is tried if needed (see
  [Textures](../shader-nodes.md#textures)).
- A texture that cannot be found reads as **transparent black**, so the pass still builds but that layer is invisible.
- Sampler state (linear / point filtering, clamp / wrap) is copied to the Image Texture node's _Interpolation_ and
  _Extension_.
- Render-target textures are not images: they come from off-screen passes that FX emulates (see
  [FX Architecture](index.md#the-pipeline)).

## The output stage

The pixel-shader group has two outputs, **Color** and **Alpha**. FX reads the pass's render states
(`SrcBlend`, `DestBlend`, `BlendOp`, `AlphaBlendEnable`) and picks one of six modes. The mode is shown in the frame
title inside the material (_MMD blending: …_).

<!-- prettier-ignore -->
| Mode | Render states | Stage |
|---|---|---|
| **Opaque** | `AlphaBlendEnable = FALSE`, or `ONE`/`ZERO` | Emission → Output |
| **Alpha blend** | `SRCALPHA`, `INVSRCALPHA` (the default) | Mix Shader (Transparent ⟷ Emission) by Alpha |
| **Additive** | `ONE`, `ONE` | colour × visible → Emission + Transparent via Add Shader |
| **Additive (alpha)** | `SRCALPHA`, `ONE` | colour × alpha → Emission + Transparent via Add Shader |
| **Premultiplied** | `ONE`, `INVSRCALPHA` | Emission added to a black/transparent mix by alpha |
| **Multiply** | `ZERO`/`SRCCOLOR` or `DESTCOLOR`/`ZERO` | Transparent BSDF coloured by the result |

Any other combination, or a `BlendOp` that is not Add, falls back to **Alpha blend**.

All modes share the same first steps, which you can see as labelled nodes:

1. **Culled vertex (mme_cull)**: the attribute that the Geometry Nodes pass wrote. `Visible = 1 - culled`, and
   **Alpha = effect alpha × Visible** (clamped). Vertices MMD would have culled are therefore invisible.
2. **MMD gamma**: a **Gamma** node set to **2.2** on the effect's colour. MMD blends in gamma space; the node reproduces
   that.
3. **MMD emission**: the colour is output as **Emission**, strength 1. Effects are light, not lit surfaces.

The material is `BLENDED` for everything except opaque, which uses `DITHERED`. Back-face culling is on only when the
pass sets `CullMode` to CCW. These last two nodes are the ones exposed as **Gamma** and **Emission** in **Pass Material**.
See [Shader Nodes Setup](../shader-nodes.md#pass-material).

<!-- prettier-ignore -->
!!! warning "Edits to this stage"
    Gamma and Emission are the right places for a final tweak, but a rebuild can regenerate them. See
    [Which edits survive rebuilds](geometry-nodes-translation.md#which-edits-survive-rebuilds).

## Unsupported operations and approximations

When the pixel-shader translation meets something it cannot express, **only that pass** loses its translated shader. The
pass keeps its geometry and gets a **plain material** instead, and the build logs why.

<!-- prettier-ignore -->
| Cause | Log message | Example |
|---|---|---|
| Bit operations on a value that varies per pixel (`&`, `|`, `^`, `<<`, `>>`, `~`) | `bit operation in a pixel shader` | the Synth fixture's `(a & 3) / 3.0` |
| A texture read inside a shared (user) function | `texture inside a shared shader function` | an effect that wraps `tex2D` in its own helper |
| An operation or function the interpreter does not know | `unknown function …` | |
| Full-screen, post-process or screen-space passes | listed in the **Passes** tab, not built | outside the scope of FX |

Example of an unconverted pass:

```text
effect pass Synth_T_P1: pixel shader not converted (bit operation in a pixel shader); using a plain material
```

**What changes for you:** the pass still appears, in the right place, with the right deformation, but its colour does not
follow the effect. Edit its material by hand if you want a look, or leave it. Other passes of the same effect are
unaffected.

<!-- prettier-ignore -->
!!! info "Bit operations are fine in vertex shaders"
    The Geometry Nodes backend has a **Bit Math** node, so `&` and friends work in a vertex shader. The material has no
    equivalent that is available for per-pixel values.

## Related pages

- Source: [`nodes/material_post.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/material_post.py),
  [`nodes/material_env.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/material_env.py),
  [`nodes/backend_ps.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/backend_ps.py),
  [`nodes/images.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/images.py)
