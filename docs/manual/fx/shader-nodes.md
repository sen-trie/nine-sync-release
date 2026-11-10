# Shader Nodes Setup

## What it does

MME pixel shaders become material nodes on the imported accessory, so the effect renders with Blender's materials.

<!-- SCREENSHOT: Selected Effect panel and an effect material -->

## Controls

Select an effect in the panel to open **Selected Effect**:

- **Tr (opacity)** and **Si (scale)** are the accessory's transparency and size, keyed from the PMM when present.
- **Effect Parameters** lists the parameters the `.fx` exposes, with editable values. Greyed rows are driven by something else, such as a linked object. **Reset Parameters** restores defaults.
- **Linked Objects** lists objects and morphs the effect reads. Use the eyedropper (**Assign Controller**) to choose the object or bone for one that could not be matched automatically.

## Rendering

- Start with **EEVEE**.
- **Cycles** may work, but some effects need material and transparency adjustments.
- Effects differ; adjust per effect.

## Textures

Textures are looked up beside the `.x`/`.fx`. Keep the original folder layout, and use **Accessory Folder** if a PMM path no longer exists.

## Limitations

Full-screen and post-processing passes are not supported.
