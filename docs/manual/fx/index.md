# FX Import

**FX Importer** brings MMD accessories (`.x`) into Blender and turns the MME effects (`.fx`) attached to them into
real Blender data: Geometry Nodes for the part of an effect that moves vertices, and shader nodes for the part that
colours pixels. Users can look at the generated nodes, change the exposed values as well as bake the result.

## What you get

| NineSync can read                                                    | NineSync builds in Blender                                                              |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| a `.x` accessory                                                     | a mesh with its materials, parented and keyed from the PMM when it came from one        |
| the `.fx` MME effect beside it (or the one the PMM's `.emm` assigns) | one **pass object** per effect pass, each with a Geometry Nodes modifier and a material |
| effect parameters in the `.fx` (`float Speed = 1;`)                  | custom properties on the accessory's root object that you can edit and key              |
| controllers the effect reads (`CONTROLOBJECT`)                       | links to your objects, bones and morphs                                                 |

## Recommended to learn in this order

<div class="grid cards" markdown>

- **1. [Getting Started](import.md)**

  Import an accessory, see which `.fx` file is used and why.

- **2. [Geometry Nodes Setup](geometry-nodes.md)**

  The settings that control how heavy effects are built, rebuilt and baked.

- **3. [Shader Nodes Setup](shader-nodes.md)**

  The controls on a selected effect: parameters, linked objects, opacity, the pass material.

- **4. [How FX Works](how-it-works/index.md)**

  The pipeline from `.x`/`.fx` to nodes. Read it when you want to
  understand or customise what was generated.

</div>

## Limitations

- **Full-screen and post-process passes** (blur, depth of field, bloom on the whole image) are out of scope. FX
  records them, reports them in the effect details and skips them.
- **Binary `.x` files** cannot drive an effect; only text `.x` files can.
- **Not every vertex or pixel shader can be translated.** When one cannot, FX uses a documented fallback instead of
  guessing; see [Geometry Nodes translation](how-it-works/geometry-nodes-translation.md#when-an-operation-cannot-be-translated)
  and [Shader translation](how-it-works/shader-translation.md#unsupported-operations-and-approximations).
- Effects are **not guaranteed to look identical to MMD**. Render engines, blend rules and sampling differ.
