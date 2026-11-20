# Getting Started

Imports MMD `.x` accessories and, where supported, builds their MME `.fx` effects in Blender. You can import one file
directly, or let a PMM sync bring in every accessory the project uses.

## Before you start

- Keep the `.x`, its textures and any `.fx` together in their **original folder structure**. Effects usually look for
  textures with relative paths such as `../Texture/Line.png`.
- **EEVEE** is recommended for starting out. Cycles can work but needs per-effect adjustments (see [Shader Nodes Setup](shader-nodes.md#rendering)).

<!-- SCREENSHOT: File > Import > MMD Accessory (.x) -->

## Import FX directly

1. Choose **File > Import > MMD Accessory (.x)** and select the file, or use **Import Accessory (.x)** in the
   NineSync panel.
2. If a `.fx` with the same name sits next to the `.x`, it is used automatically. To choose another one, set
   **Effect File** in the **Accessory Directory** panel.
3. The accessory appears in the NineSync panels. With an effect, it is built as one object per effect pass.

## Import via a PMM

1. Sync the PMM with **Sync Now** (see [PMM Sync](../core/pmm-sync/index.md)).
2. Accessories in the PMM are automatically imported and animated.
3. In the accessory list, the link toggle beside each accessory (**Sync From PMM**) controls whether it updates from the
   PMM.

### Which `.fx` file is used

FX uses the following order:

1. The **Effect File** you chose in the panel.
2. The PMM's **`.emm`** file (same name as the PMM, next to it): the accessory's `[Effect]` entry, then the file's
   `Default`. The value `none` means "no effect"; `hide` hides the accessory.
3. A `.fx` with the **same name beside the `.x`**.

If the `.emm` names an effect FX cannot find, the accessory is reported ("Effect not found") and no other file is chosen. How the `.emm` is matched
to accessories is explained in [Accessories and effects in a PMM sync](../core/pmm-sync/accessories-and-effects.md).

### Moving a project: stored file paths

When FX picks a `.fx` or `.x` itself, the path is stored **relative to the saved `.blend`** (`//...`), so a project folder that is moved or copied as a whole keeps working. A path is stored as absolute when the `.blend` is not saved yet, when the file is on another drive, or when you chose the effect by hand with **Effect File**. Save the project before importing if you want portable paths.

If a recorded file is missing later (a moved folder, an unmounted drive):

- Opening the project shows a warning; the existing passes and bakes stay as they are.
- **Rebuild** reports "Not rebuilt, ..." and leaves the working passes alone. **Bake** reports "Not baked, ...". Clearing a bake still works.
- Restore the folder, or point **Effect File** (and **Accessory Folder** for a PMM sync) at the new location, then rebuild.

## Options explained

| Option                         | Where                      | What it does                                                                                | Applies              |
| ------------------------------ | -------------------------- | ------------------------------------------------------------------------------------------- | -------------------- |
| **Use Effect**                 | accessory row, shader icon | Off imports the plain mesh without running the effect                                       | next sync or rebuild |
| **Sync Accessories**           | PMM options                | Import and animate the PMM's accessories (static meshes only)                               | next sync            |
| **Accessory Folder**           | PMM options                | Extra folder searched for `.x` files when the path stored in the PMM does not exist         | next sync            |
| **Sphere Maps (Experimental)** | PMM options                | Rebuild `.sph`/`.spa` sphere maps from accessory textures with a camera-space normal lookup | next sync            |
| **Effect File**                | Accessory Directory        | Use this `.fx` instead of the one found by the rules above                                  | next sync or rebuild |
| **Parent Bone**                | accessory row              | Override the parent bone stored in the PMM                                                  | next sync            |
| **Keyframe Visibility**        | accessory row              | Inserts a visibility key (hide in viewport and in renders) at the current frame             | immediately          |
| **Clean Accessories**          | panel                      | Deletes imported accessories, effects and their animation. Your own data is not touched     | immediately          |

## What happens to the accessory's size and opacity

PMM accessories have **Tr** (opacity) and **Si** (scale) keys. FX stores them on the accessory root as `mme_tr` and
`mme_si` and keys them from the PMM. Accessories **without** an effect fade with Tr; accessories **with** an effect
receive Tr as the value of the effect's `Tr` input. Many MME effects use it as a progress control, and passes that FX
proves are empty at Tr = 0 are switched off then.

## Troubleshooting

- **Effect not applied:** check **Accessory Directory** for a note, and the **Effect File** path.
- **Files missing after moving a project:** see [Moving a project](#moving-a-project-stored-file-paths).
- **Project made with an older FX:** use **Rebuild Changed Effects** to update its effects.
