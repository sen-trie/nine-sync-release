# Shader Nodes Setup

The **pixel shader** of an MME effect decides the colour and transparency of each pixel. FX turns it into **shader nodes**, so the effect renders with Blender's own materials. Each effect pass gets its own material.

New to shader nodes? A material determines how objects in Blender appear; they can be animated and take values from external parameters. [Shader translation](how-it-works/shader-translation.md)
walks through how a material is generated for each pass.

<!-- SCREENSHOT: Selected Effect panel and an effect material -->

### Tr and Si

**Tr (opacity)** and **Si (scale)** are the accessory's transparency and size. They come from the PMM's accessory keys
when there is a PMM and are stored as `mme_tr` and `mme_si` on the accessory root. Effects that read `Tr` (the usual
way to animate an effect's progress) receive this value through a driver; effects that read `Si` receive it multiplied by
the accessory unit (10).

### Effect Parameters

Every plain `float`, `int` or `bool` value (and small vector such as a colour) that the `.fx` declares with an initial
value or a UI annotation becomes an editable property on the root, named `mmeP_<ParameterName>`. They are listed in
**Effect Parameters**:

<!-- prettier-ignore -->
| Icon | Meaning |
|---|---|
| wrench | The parameter changes **geometry** (the vertex shader reads it, or it is a loop count). Editing it marks the effect out of date; rebuild to apply, or turn on **Auto Rebuild** |
| link | A **controller** takes over this parameter while it is linked and enabled. The row is greyed out |
| none | A live value. Pixel-shader values and most Geometry Nodes values are driven, so edits show immediately |

**Reset Parameters** restores the values written in the `.fx`.

**Why only these are exposed:** parameters with a hardware _semantic_ (`WORLDVIEWPROJECTION`, `TIME`…), `static` or `const`
values, arrays and values hidden with `UIVisible = false` are things MMD or the effect computes itself, not values an
artist is meant to set. The full rule is on the
[Geometry Nodes translation page](how-it-works/geometry-nodes-translation.md#from-mme-parameters-to-blender-controls).

### Linked Objects

Effects often read other things in the MMD scene with `CONTROLOBJECT`: a controller model's morph, a bone, another
accessory. **Linked Objects** lists each one and what it was matched to:

| Shown as         | Meaning                                         |
| ---------------- | ----------------------------------------------- |
| this accessory   | the accessory's own transform, **Tr** or **Si** |
| object / model   | another object in the scene                     |
| morph (keyed)    | a morph slider, keyed on the accessory root     |
| shape key (live) | read live from a shape key on a mesh            |
| bone             | a bone of an armature                           |
| **missing**      | no match; the effect uses fixed values          |

For a **missing** link, use the eyedropper (**Assign Controller**) to choose the object or bone. The assignment is saved
with the accessory; an automatic match from the PMM always wins over a stored one. A control that reads another object
also gets a _use_ switch you can key to turn it on and off.

### Pass Material

In **Effect Details > Selected Pass**, **Pass Material** edits the last two nodes of the generated material on their own
sockets:

| Control                  | Node it edits                                | Origin                                                                  |
| ------------------------ | -------------------------------------------- | ----------------------------------------------------------------------- |
| **Gamma**                | the _Gamma_ node after the effect's colour   | FX applies MMD's gamma of 2.2 to the effect's colour                    |
| **Emission**             | the _Emission_ node's Strength               | the effect's colour is output as emission (light), not as a lit surface |
| **Produce Diffuse Rays** | the object's _visible diffuse_ flag (Cycles) | lets the pass light nearby surfaces when the scene has diffuse bounces  |

<!-- prettier-ignore -->
!!! warning "Rebuilds can reset material edits"
    A rebuild regenerates the generated material. Edits to Gamma and Emission can be reset by a later rebuild of that pass.
    Treat them as a final adjustment and re-apply them if you rebuild.

## Rendering

- **EEVEE is the recommended render engine for most users.** Effect materials use blended transparency (additive and multiply modes included).
- **Cycles can work**, but some effects do not display properly since they heavily rely on many alpha planes. Several stacked transparent layers can
  render black until you raise **Transparent** bounces in the render settings. Though, one advantage of Cycles is that _Produce Diffuse Rays_ lets an effect pass light surrounding objects (which is impossible for blended effects in EEVEE)
- When a scene has effects, FX turns on **Lock Interface** in the render settings so effects can update safely while a
  render is running.

## Textures

Textures are looked up beside the `.x`/`.fx`, using the paths the effect names (`ResourceName`). The lookup ignores
case and, if the exact name is not found, tries the same name with another image extension. Keep the original folder
layout, and use **Accessory Folder** if a PMM path no longer exists. A texture that cannot be found reads as transparent
black, so the pass still builds but that layer shows nothing; see [Common Issues](../../issues.md#fx-import).
