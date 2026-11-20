# PMM Reading and Writing

MikuMikuDance saves projects as `.pmm` files. NineSync reads them to bring animation into Blender and can write a new PMM from your Blender scene.

## Reading a PMM

NineSync only supports version 2 PMM files. The following table shows where their animation and other project data go in Blender.

<!-- prettier-ignore -->
| PMM data | In Blender |
|---|---|
| Bone animation | mmd_tools imports bone keys into a **Motion** clip on an NLA track. |
| Morph animation | Morphs get their own **Shapekey** clip. UV morphs shift textures through material nodes, and bone morphs are baked into bone keys. |
| IK switches | NineSync keys the model's IK constraints. |
| Outside parents | With **Sync Model Constraints** on (the default), bones follow their attachments to other models, including changes to those attachments over time. See [Outside parents](how-it-works/ik-morphs-parents.md#outside-parents). |
| Model visibility | Turn on **Sync Model Visibility** to apply visibility to the viewport and render. |
| Camera and light | NineSync adds keys to the MMD camera rig and light. |
| Accessories | [FX](accessories-and-effects.md) imports accessories when installed. |
| Audio | NineSync adds audio to the sequencer. Use **Audio File** to choose a different file. |

NineSync matches bones and morphs by name. The **PMM Motion Inspector** counts keys on unmatched bones as **lost keys**. **Preview** also warns about keys on bones marked invisible in the PMX, which MMD skips during playback.

### A damaged PMM

If NineSync has trouble reading a later section, such as camera and light, accessories or audio, it still uses the models and keys it has already read. The error identifies the section it couldn't read.

## Creating a PMM

To export your Blender scene as a new MMD project, follow the [PMM Create guide](../pmm-create/index.md).

For the file format and how NineSync reads it, see [PMM Parsing and Serialization](how-it-works/parsing.md).
