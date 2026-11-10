# PMM Sync

## What it does

Imports a MikuMikuDance `.pmm` project into Blender through mmd_tools: model bone and morph animation, UV morphs, camera, light and audio. Edit the project in MMD, sync again, and Blender updates.

## Before you start

- mmd_tools is installed and enabled.
- The PMX models used by the PMM are already imported into Blender as mmd_tools models.
- Models are imported at the scale you want. If the panel shows a scale warning, use **Import at Scale 1.0 From Now On** and re-import the models.

<!-- SCREENSHOT: NineSync main panel with a PMM loaded -->

## Steps

1. Open the **NineSync** tab and set **Source PMM**.
2. Press the refresh icon beside **PMX Models**. Each model in the PMM is listed.
3. For each model you want to sync, tick it and choose its **Target** (the mmd_tools model in your scene).
4. Optional: select **Preview** to see what would change. Preview changes nothing in the scene.
5. Select **Sync Now**. Press **Esc** to cancel between models; **Ctrl+Z** undoes the whole sync.

## What to expect

- Unchanged models are skipped on later syncs.
- Motion goes into a **Motion** clip and morphs into a **Shapekey** clip on NLA tracks. Pick an existing action in those fields, or leave them empty to get a new clip.
- Your own keys outside the PMM's frame range are preserved.
- If your scene frame rate differs from the PMM's 30 fps, a notice appears and **Retime to Scene FPS** keeps motion at real speed.
- If the PMM contains accessories and FX is available, they sync in the same step. See [Import](../fx/import.md).

## Re-syncing and Force Resync

**Sync Now** skips unchanged clips and generally preserves your edits to them. To replace a clip with the MMD version, open **PMM Motion Inspector** (at the bottom of the panel) and use **Force Resync**, or the refresh button on one model to force only that model. Edits to forced clips are overwritten.

The Inspector also shows, per model, how many animated bones and morphs reach your target.

## Options explained

| Panel | Option | Meaning |
|---|---|---|
| Options | Auto Scale From Model / Scale | Use the scale the first enabled model was imported with, or set one manually. |
| Options | UV Morphs | Apply UV morphs by offsetting the texture in the material nodes (needed for effects such as `> <` eyes). |
| Options | Sync Model Visibility | Hide and show meshes where the PMM hides the model, in viewport and renders. Your own visibility keys stay on top. |
| Options | MMDBridge Physics (Experimental) | Layer a VMD baked with MMDBridge above the PMM clip. |
| Camera & Light | Sync Camera / Sync Light | Import the camera and light. |
| Camera & Light | Follow Bone / Follow Bone Rotation | Make the camera follow the model and bone stored in each PMM camera key. |
| Audio | Sync Audio / Audio File | Add the PMM's audio to the sequencer at frame 0, or use your own file instead. |

**Camera & Light** also has a collapsed **MMD Values (current frame)** readout.

## Limitations

- Syncing is one way: MMD to Blender.
- Physics results from MMD are not reproduced unless you use the experimental MMDBridge option.

## Troubleshooting

- **Models not listed:** press the refresh icon again after setting **Source PMM**.
- **Something looks wrong:** use **Support Report** to copy a report, check it for private information, then share it. The log is in the Text Editor under `NineSyncLog`.
- **Remove everything NineSync made:** **Clean** removes data created by NineSync; your own actions, clips and shape keys are not touched.
