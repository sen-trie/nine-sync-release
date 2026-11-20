---
hide:
  - toc
---

# Custom Shaders with Noise and Voronoi

Add Blender's procedural textures to a generated pass material to change how the effect looks. For the basics, see [Shader Nodes Setup](../manual/fx/shader-nodes.md).

## Steps

1. Select a pass object from an imported effect and open its material in the **Shader Editor**. Edit the ordinary pass material. See [How the instanced material works](../manual/fx/how-it-works/shader-translation.md#the-instanced-material).
2. Find the pixel-shader group and trace the connection that feeds its colour.
3. Add **Noise Texture** and **Voronoi Texture** nodes. Feed both **Vector** inputs from a **Texture Coordinate** output, such as **UV**.
4. Add a **Mix** node. For example, use Voronoi's **Distance** as the factor and Noise's **Color** as the second input.
5. Connect the result to the colour input, or multiply it with the existing colour.

<div class="ns-media"><strong>Screenshot</strong><span>The edited material with Noise and Voronoi feeding a Mix node.</span></div>
<div class="ns-media"><strong>Render</strong><span>The effect before and after the change.</span></div>