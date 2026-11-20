---
hide:
  - toc
---

# PMM Create

Export your Blender scene as an MMD project (`.pmm`) with up to **255 models**, plus optional props, camera and animation. See the [Compatibility Matrix](compatibility.md) for export support.

<!-- SCREENSHOT: Create MMD Project panel -->

## Steps

1. Open **Create MMD Project** in the **NineSync** tab.
2. Refresh **MMD Armatures** and tick the mmd_tools models to include. MMD loads each model from the PMX path shown.
3. To export a camera, choose an mmd_tools rig under **MMD Camera**. **Spawn MMD Camera** creates or selects one. Leave the field empty to use MMD’s default camera.
4. Add any [props](#props).
5. Turn on **Export Animation** and select the channels to export (**Bones**, **Morphs**, **Visibility**, **Markers**). With **Export Animation** off, the models and camera use their initial poses.
6. Select **Create PMM** and choose where to save.

The export uses the Blender scene’s frame range and converts it to MMD’s 30 fps timeline.

## Props

Select meshes and click **Add Selected Meshes** under **Props (.x)**. Meshes that belong to mmd_tools models are skipped. Props export as text `.x` files in the `accessories` folder beside the PMM, with transform and visibility keys at the original Blender keyframes.

Use **Read Materials** (the prop’s colour button) to set colours. Each material exports as a single colour without textures.

## Options explained

- **Bake Root Motion** transfers motion from the root empty to the model’s parent bones so it can export.
- **Visibility** hides a model in MMD when all its meshes are hidden in Blender’s viewport or render.
- **Markers** exports timeline markers as keys on a hidden accessory.
- **Clean MMD Labels** creates PMX copies with English names and unhides keyed bones in those copies.
- **Link to Syncer** sets the exported file as the **Source PMM** and maps its models to your Blender objects.

## Limitations

MMD checks the PMM against the PMX when opening a project. If MMD reports a different model structure, export again using the same PMX that MMD loads. See [Common Issues](../../../issues.md#pmm-create).

For a walkthrough, see [Preparing a Blender Scene for Export to MMD](../../../examples/export-to-mmd.md).
