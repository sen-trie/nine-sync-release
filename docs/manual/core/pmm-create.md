# PMM Create

## What it does

Writes an MMD project (`.pmm`) from your Blender scene: models, an optional camera, props, and optionally the animation Blender already has.

## Before you start

- mmd_tools is installed; the panel says *Needs mmd_tools* otherwise.
- Your models are mmd_tools models loaded from PMX files.
- NineSync's bundled project template must be present; the panel warns if it is missing.

<!-- SCREENSHOT: Create MMD Project panel -->

## Steps

1. Open **Create MMD Project** in the **NineSync** tab.
2. Optional: **Spawn MMD Camera** creates the camera rig (or selects the existing one). Choose it under **MMD Camera**; leave it empty to keep MMD's default camera.
3. Under **MMD Armatures**, press the refresh icon to find models. Tick the ones to include. Each shows the **PMX** it was loaded from; MMD loads the model from that path.
4. Optional: add props (see below).
5. Choose what to write: **Export Animation** with **Bones**, **Morphs**, **Visibility** and **Markers**. With **Export Animation** off, models and camera are written at their initial pose.
6. Select **Create PMM** and choose where to save.

## Props

Under **Props (.x)**, **Add Selected Meshes** lists the selected mesh objects. They are written as `.x` accessories into an accessories folder beside the PMM. **Read Materials** (the colour button on a prop) lets you set material colours. Meshes that belong to an mmd_tools model are skipped.

## Options explained

- **Bake Root Motion:** moves a model's root-empty motion onto its parent bone. This changes your `.blend`; Create PMM never does it on its own.
- **Visibility:** hides the model in MMD where all its meshes are hidden in Blender.
- **Markers:** written as keyframes on a hidden "Markers" accessory. MMD has no markers; Sync does not read them back.
- **Clean MMD Labels:** writes a copy of each PMX with English names so MMD shows no `Null_xx` or garbled rows, and unhides keyed hidden bones. The original PMX is not modified.
- **Link to Syncer:** sets the new PMM as the Source PMM and maps its models to your objects, so MMD changes can be synced back. Off leaves the `.blend` unchanged.

## Limitations

- Create PMM reads the scene and does not change it (apart from actions you trigger yourself, such as Bake Root Motion).
- Only the data listed above is written.
