---
hide:
  - toc
---

# Compatibility Matrix

PMM Sync imports MMD projects into Blender. PMM Create exports Blender projects to MMD. Some data is lost on a round trip.

🟩 Full · 🟨 Partial · 🟦 Conditional · 🟥 Unsupported

## Animation

| Feature | MMD to Blender | Blender to MMD | Notes |
|---|---|---|---|
| Bone animation | 🟩 | 🟨 | Sync preserves MMD interpolation on matching PMX bones. Create exports keyed PMX bones via mmd_tools. PMM stores neither bone scale nor root motion. See [Bake Root Motion](index.md#options-explained). |
| Morph animation | 🟩 | 🟨 | Sync imports vertex and material morphs, applies UV morphs through material nodes with **UV Morphs** enabled, and bakes bone morphs every frame. Create exports shape keys that mmd_tools matches to PMX morph names. |
| Camera animation | 🟩 | 🟨 | Sync builds an mmd_tools rig. Curves match MMD at import scale 1.0. Create exports only the mmd_tools rig selected under **MMD Camera**. |
| Light animation | 🟨 | 🟥 | Sync keys colour and direction. Create keeps the template light. |
| Model visibility | 🟦 | 🟦 | **Sync Model Visibility** (off by default) toggles all model meshes in viewport and render. Create hides a model when all its meshes are hidden. Both directions use on/off visibility. |
| Audio | 🟦 | 🟥 | Sync needs **Sync Audio** and an accessible audio file. Create keeps the template audio settings. |
| Frame rate | 🟩 | 🟩 | **Retime to Scene FPS** converts MMD frames to Blender scene FPS. Create converts back to MMD FPS. |

## Models and scene

| Feature | MMD to Blender | Blender to MMD | Notes |
|---|---|---|---|
| Accessories | 🟦 | 🟨 | Sync needs FX and accessible text or binary `.x` meshes. Create exports selected meshes as text `.x` props with existing keys and one colour per material. Textures and effects are omitted. |
| Outside-parent bindings | 🟦 | 🟥 | Sync needs **Sync Model Constraints** (on by default) and a synced parent model. Create exports solved bone motion without the binding. |
| MMD IK switches | 🟩 | 🟥 | Sync toggles IK constraints at the original PMM keyframes. |
| MMD leg IK | 🟦 | 🟥 | [MMD Leg IK](../pmm-sync/index.md#options-explained) is optional and handles two-bone leg chains only. |
| Physics | 🟥 | 🟥 | Sync can layer an MMDBridge-baked VMD over the PMM clip using an experimental option. MMD simulates physics when it opens the exported project. |
| MME effects | 🟦 | 🟥 | Sync passes assignments (including `.emm`) to FX, which translates supported effects into Geometry Nodes and Shader Nodes. See [FX limitations](../../fx/index.md#limitations). |
| Rigify animation | 🟦 | 🟥 | Sync supports *Rigify Operability Focused* rigs made with MMD Tools Append. Bake motion to MMD bones before export. |
| Timeline markers | 🟥 | 🟨 | Create exports markers as keys on a hidden accessory for viewing in MMD. |
