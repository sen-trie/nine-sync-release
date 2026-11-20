---
hide:
  - toc
---

# Preparing a Blender Scene for Export to MMD

Before you export, check that MMD can load your models and that the scene uses the camera, props and animation you want to send over. For the export options, see [PMM Create](../manual/core/pmm-create/index.md).

## Checklist

1. Import the models with mmd_tools and keep their PMX files at the paths shown in the exporter. MMD uses those files to load the models.
2. If you animated a model's root empty, use [**Bake Root Motion**](../manual/core/pmm-create/index.md#options-explained) to transfer that motion to its bones.
3. If you want to export a camera, use **Spawn MMD Camera** and animate that rig.
4. Select the meshes you want as props and click **Add Selected Meshes**. Each exports as a text `.x` file with one colour per material and no textures.
5. Key the poses and changes you want in MMD. To hide a model, key the visibility of all its meshes.

<div class="ns-media"><strong>Screenshot</strong><span>The Create MMD Project panel with a model, the camera rig and one prop selected.</span></div>

## Write the project

1. Tick the models to include. To include animation, turn on **Export Animation** and select the channels you want (**Bones**, **Morphs**, **Visibility**, **Markers**).
2. If you plan to sync changes back from MMD, turn on **Link to Syncer**. Click **Create PMM** to save.
3. Open the PMM in MMD. If MMD reports a different model structure, export again using the same PMX that MMD loads.

## What to check in MMD

Play the project and check the bone and morph animation, camera, visibility and props. See the [Compatibility Matrix](../manual/core/pmm-create/compatibility.md) for what to expect.

If the Blender scene came from a PMM with an outside-parent binding, the export carries over the resulting bone motion. Recreate the binding in MMD if you need it there.
