# PMM Reading and Writing

A `.pmm` is MikuMikuDance's project file. NineSync reads it to bring a project into Blender and can create a new one from your Blender scene.

## Reading a PMM

NineSync reads PMM (version 2) files. It brings in model motion, morphs, visibility, camera, light and audio. If FX is installed, accessories and their effects can be imported too.

<!-- prettier-ignore -->
| PMM data | In Blender |
|---|---|
| Bone animation | A **Motion** clip on an NLA track, imported through mmd_tools. |
| Morph animation | A separate **Shapekey** clip. UV morphs also use material nodes to move the texture. |
| IK switches | Keys on the model's IK constraints. |
| Model visibility | Viewport and render visibility, if **Sync Model Visibility** is enabled. |
| Camera and light | Keys on the MMD camera rig and light. |
| Accessories | Imported by [FX](fx-integration.md), when installed. |
| Audio | Added to the sequencer, or chosen separately with **Audio File**. |

By default, MMD uses 30 fps. If needed, NineSync adjusts the timing to match your Blender scene; see [Retiming](synchronization.md#retiming).

NineSync matches bone and morph names between the PMM and your model. If a bone can't be matched, its keys are counted as **lost keys** in the **PMM Motion Inspector** so you can check what was missed.

### Failure stays local

If NineSync can't read a later section of a PMM, it can still use the models and keys it already read. The error is reported so you know which part needs attention.

## Creating a PMM

**Create PMM** starts with a template saved by MMD. It replaces the template's models and camera, adds your selected accessories, and sets the play range. Other settings, including the template's light and audio, are kept.

<!-- prettier-ignore -->
| Blender data | What NineSync writes |
|---|---|
| Model animation | Bone and morph keys exported through mmd_tools. |
| Visibility | A model is hidden in MMD when all its meshes are hidden in Blender. |
| Camera | The selected camera rig, or the template's camera if none is selected. |
| Props | Selected meshes become text `.x` files in an `accessories` folder beside the PMM. Their animation is sampled at your keyframes. |
| Markers | Keys on a hidden **Markers** accessory. MMD has no timeline markers, and Sync doesn't read these back. |
| PMX labels | **Clean MMD Labels** creates labelled copies of the PMX files; the originals are left alone. |

A PMM can contain up to **255 models**. Names are shortened to fit MMD's byte limits, and bone and morph order follows the PMX model. This helps MMD recognise the model when it opens the project.

**Link to Syncer** optionally makes the new file your scene's Source PMM, ready for syncing changes back from MMD. **Bake Root Motion** is a separate button that bakes the empty parent motion onto the root bone of the pmx.

<!-- prettier-ignore -->
!!! warning "A round trip is not lossless"
    Create PMM only writes the data listed above. For example, Blender light animation is not exported.
