---
hide:
  - toc
---

# Custom Geometry Nodes with Instances

Use **Edit Particle Instances** to vary the size of an effect's sprites, remove some of them, or replace them with a mesh of your own.

## What the pass does

The particle pass creates an instance for each sprite. It runs the nodes in the **Edit Particle Instances** frame before realising the instances, so your changes are included in the bake. Set **Particle Mesh** to replace every sprite with a copy of your mesh. Each copy follows the sprite's orientation and size. See [Generated Attributes](../manual/fx/geometry-nodes/generated-attributes.md).

## Steps

1. Import an accessory with a sprite pass and select that pass object.
2. In **Selected Effect > Effect Details > Selected Pass**, turn on **Edit Particle Instances**. This option appears on sprite passes.
3. Turn on **Enable Geometry Node Editing** for the pass.
4. In the **Geometry Nodes** editor, find **Edit Particle Instances (needs the panel checkbox)**.
5. Add nodes that work on instances. For example, connect **Random Value** to **Scale Instances** to vary the sizes, or set **Delete Geometry** to the **Instance** domain to remove some sprites.
6. To replace the sprite mesh, choose an object in the modifier's **Particle Mesh** field.
7. Check the result in the viewport, then click **Bake Changed** under **Scene Bake**.
8. Render a frame to check how the effect looks.

<div class="ns-media"><strong>Screenshot</strong><span>The Edit Particle Instances frame with Random Value driving Scale Instances.</span></div>
<div class="ns-media"><strong>Render</strong><span>The effect before and after replacing sprites with a custom mesh.</span></div>

## Notes

- Keep a copy of your instance edits so you can restore them after a rebuild. See [Which edits survive rebuilds](../manual/fx/how-it-works/geometry-nodes-translation.md#which-edits-survive-rebuilds).
- **Edit Particle Points** works on the **Point** domain on any looped pass. Use **Edit Particle Instances** to work on the resulting sprite instances.
- A replacement mesh follows the sprite's normal. Check its orientation in your render engine.
