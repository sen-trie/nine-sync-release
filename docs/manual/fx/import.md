# Import Accessories and Effects

## What it does

Imports MMD `.x` accessories and, where supported, builds their MME `.fx` effects in Blender.

## Before you start

- Keep the `.x`, its textures and any `.fx` together in their original folder structure.
- Use **EEVEE** for the best results.

<!-- SCREENSHOT: File > Import > MMD Accessory (.x) -->

## Steps: import directly

1. Choose **File > Import > MMD Accessory (.x)** and select the file. Or use **Import Accessory (.x)** in the NineSync panel.
2. If a matching `.fx` is next to the `.x`, it is used automatically. To choose another, set **Effect File** under **Accessory Effects**.
3. Imported accessories appear in the NineSync panels.

## Steps: with a PMM

1. Sync the PMM with **Sync Now** (see [PMM Sync](../core/pmm-sync.md)).
2. Accessories in the PMM are imported and animated in the same sync. Effects assigned in the PMM's `.emm` are used.
3. In the accessories list, the link toggle beside each accessory controls whether it updates from the PMM. **Parent Bone** can override the PMM's parent bone.

## Options explained

- **Use Effect:** off imports the plain mesh.
- **Sync Accessories:** import and animate the PMM's accessories (static meshes only).
- **Accessory Folder:** extra folder searched for `.x` files when the PMM's path does not exist.
- **Sphere Maps (Experimental):** rebuild `.sph`/`.spa` maps.
- **Keyframe Visibility:** keys the accessory's viewport and render visibility at the current frame.
- **Clean Accessories:** deletes imported accessories, effects and animation; your own data is untouched.

## Limitations

- Full-screen and post-processing effects are not supported.
- Not every effect can be reproduced.
- Respect each effect author's licence and redistribution terms.

## Troubleshooting

- **Effect not applied:** check **Accessory Effects** for a note, and the **Effect File** path.
- **Old project:** use **Repair Legacy Data**, then **Rebuild All Effects**.
- **Report a problem:** **Support Report** copies diagnostics; check them before posting.
