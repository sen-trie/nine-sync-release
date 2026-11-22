---
hide:
  - toc
---

# Nuke2: An Animated Smoke Effect

Nuke2 is an MME effect with a central core and several smoke passes that draw many copies of the same mesh. In this example, you'll import the accessory and its effect, animate its opacity, edit a smoke pass and compare the settings that affect playback speed.

## What you need

- Blender 5.3.0 or newer and either the combined NineSync extension or the standalone FX Importer. Install mmd_tools if you also plan to sync a PMM.
- A copy of Nuke2 from its author's official distribution. Follow the author's terms and keep the original folder layout so FX can find the `.fx` and its textures. For automatic pairing, the `.x` and `.fx` files need the same base name and must be in the same folder.

## 1. Import the accessory with its effect

1. In the 3D Viewport, choose **File > Import > MMD Accessory (.x)**. You can also press **N** to open the sidebar and choose **NineSync > NineSync: Accessories (.x) > Import Accessory (.x)**.
2. Select the Nuke2 `.x` file and check the import options.
    - **Scale** defaults to 0.08 or uses the shared mmd_tools scale.
    - Leave **MME Effect** on to build the effect as you import.
    - Leave **Effect File** empty to use the matching `.fx`. Choose the file yourself if it has a different name.
3. Import the accessory. The first import took 11 to 16 seconds in the benchmark sessions below. Later imports of the same effect reuse cached results.

<div class="ns-media"><strong>Screenshot</strong><span>The MMD Accessory (.x) import dialog with Scale, MME Effect and Effect File.</span></div>

If FX shows a warning, check the list of missing files. See [Troubleshooting](../manual/fx/import.md#troubleshooting).

## 2. Inspect the passes

1. Select the accessory and open **NineSync: FX Importer > Selected Effect > Effect Details**.
2. Open **Passes**. The list shows each entry as *technique / pass*. Click a row such as **Smoke1**, **Smoke2** or **Smoke3** to select it.
3. In **Selected Pass** and **Pass Details**, check the editing switches and material settings, including **Gamma**, **Emission** and **Produce Diffuse Rays**.

Each pass is a separate object with its own Geometry Nodes tree. The smoke passes are expensive because their vertex shader moves many copies of the same mesh. You can change **Transparency Order** to speed them up.

<div class="ns-media"><strong>Screenshot</strong><span>Selected Effect > Effect Details > Passes with the Smoke passes listed.</span></div>

## 3. Animate Tr

**Tr (opacity)** appears under **Selected Effect**. If the accessory came from a PMM sync, change its opacity keys in MMD. See [how FX stores opacity](../manual/fx/import.md#what-happens-to-the-accessorys-size-and-opacity).

For a standalone import, set the keys in Blender.

1. At frame 0, set **Tr (opacity)** to 1. Hover over the field and press **I** to insert a keyframe.
2. At frame 60, set it to 0 and press **I** again.
3. Play or scrub through frames 0 to 60 to see how the smoke responds.

FX passes **Tr** directly to the shader. Nuke2's `.fx` determines how the smoke responds. If you see no change, check for keys on the root object's `mme_tr` property.

Use an animated **Tr** or camera when comparing playback speeds. With a static scene, Blender may reuse the same result between frames.

## 4. Edit the generated Geometry Nodes

Open a smoke pass in the **Geometry Nodes** editor and add nodes to the link inside one of these frames.

- **Edit Source Mesh** changes the mesh used for each smoke copy.
- **Edit Final Geometry** changes the combined smoke geometry.

Each looped pass also has an **Edit Particle Points** group that survives rebuilds. FX keeps edits in these areas within the limits described in the guide. Put any zones inside a group node. See [Which edits survive rebuilds](../manual/fx/how-it-works/geometry-nodes-translation.md#which-edits-survive-rebuilds).

Keep the generated frames, their input and output reroutes, the **NineSync Bake** node and modifier inputs such as **Enable Instance Editing** and **Particle Mesh** connected and named as generated. FX looks them up by name. **Edit Particle Instances** appears on sprite passes. Nuke2's smoke uses mesh copies.

In **Pass Details**, turn on **Enable Geometry Node Editing** to see your edits live in the viewport.

<div class="ns-media"><strong>Screenshot</strong><span>A smoke pass tree showing the Edit Source Mesh and Edit Final Geometry frames.</span></div>

## 5. Speed: Transparency Order, density and baking

- **Transparency Order** controls how FX sorts the smoke meshes. **Blender Sorted** is the fastest option and can make the smoke look lighter in EEVEE. See [the available levels](../manual/fx/geometry-nodes/index.md#the-settings-panel).
- **Effect Density** in **Settings** controls how many copies the pass draws. Keep it at 1 to match MMD's density, or lower it for smoother scrubbing.
- **Scene Bake** stores the evaluated passes for faster playback. Under **Store**, choose **Packed in .blend** (the default) or **Disk**. Disk bakes use **Bake Folder**, which defaults to `//mme_bake/` beside the project. Enable **Folder per Pass** if you want a separate folder for each pass.

Turn on **Share Bakes** to let projects reuse matching disk bakes from the add-on's cache, up to **Shared Bake Limit (MB)**. Click **Bake Changed** to bake new or changed passes.

## 6. Save and reopen

Save the `.blend` and keep the Nuke2 folder in the same place relative to it. Packed bakes travel with the `.blend` file. If you baked to disk, keep the bake folder with the project. See [Moving a project](../manual/fx/import.md#moving-a-project-stored-file-paths).