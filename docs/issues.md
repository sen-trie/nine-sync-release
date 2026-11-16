# Common Issues

If your problem is not listed here, use **Support Report** in the NineSync panel. Check the report for private information before sharing it, and see [Triage](triage.md).

## PMM Create

### MMD says "model structure is different"

- **Cause:** a bone, morph or model name was longer than MMD's field. Core cuts names at the exact **Shift-JIS byte
  limit** of each field, but a PMM written by an older Core, or edited by hand, can have longer ones.
- **Do:** create the PMM again with a current Core. See [Creating a PMM](manual/core/pmm-sync/how-it-works/reading-and-writing.md#creating-a-pmm).

### The panel says _Needs mmd_tools_ or warns that the template is missing

- **Cause:** Create PMM drives mmd_tools' exporter and starts from a bundled project template.
- **Do:** install and enable mmd_tools; if the template warning persists, reinstall the extension.

### My light, or my camera, is not in the new PMM

- **Cause:** the light is never written (the template's light is kept), and the camera is written only if a camera rig is
  chosen under **MMD Camera**.
- **Do:** pick the camera rig. Set the light in MMD. See [Creating a PMM](manual/core/pmm-sync/how-it-works/reading-and-writing.md#creating-a-pmm).

### A mesh I selected is not offered as a prop

- **Cause:** meshes that belong to an mmd_tools model are skipped.
- **Do:** select a mesh that is not part of a model.

---

## PMM Sync

### The PMX Models list is empty

- **Cause:** the list is filled when you refresh it, not when you pick the file.
- **Do:** set **Source PMM**, then press the refresh icon beside **PMX Models**. A PMM that is not version 2 is rejected
  with an error rather than read.

### A model shows a warning and nothing was imported ("use Force Resync…")

- **Cause:** the import settings changed, but you had edited the clip in Blender. Core refuses to overwrite it
  (**Blocked**).
- **Do:** open **PMM Motion Inspector** and use **Force Resync** for that model. This replaces your edits.
- **See:** [What happens to your edits](manual/core/pmm-sync/how-it-works/synchronization.md#what-happens-to-your-edits).

### I synced again and nothing changed

- **Cause:** Core compares a fingerprint of the parsed tracks, not the file. If the animation did not change, the part is
  **skipped**, and your edits are kept.
- **Do:** this is normal. **Preview** shows why each part is skipped. Use **Force Resync** only if you want to replace a clip.

### Some bones or morphs do not move

- **Cause:** the PMM names a bone or morph that the PMX in Blender does not have (renamed, or too long to match). The keys
  are counted as **lost keys**, not applied.
- **Do:** open **PMM Motion Inspector**, which shows per model how many animated bones and morphs reach the target and
  names the ones that do not. Rename the bone or morph in the PMX to match.
- **See:** [Reading a PMM](manual/core/pmm-sync/how-it-works/reading-and-writing.md#reading-a-pmm).

### Preview warns that the PMM keys bones that the PMX hides

- **Cause:** MMD never plays keys on bones that are flagged not visible, so those keys do nothing in MMD either.
- **Do:** unhide the bone in the PMX if you expect it to animate.

### Motion is too fast or too slow

- **Cause:** a PMM is 30 fps. If the scene frame rate differs, the keys must be rescaled.
- **Do:** accept the notice and use **Retime to Scene FPS**. For a baked MMDBridge physics VMD, Core does not retime it:
  set MMDBridge's export rate to the scene's rate ([known limit](manual/core/pmm-sync/how-it-works/synchronization.md#retiming)).

### The models are the wrong size

- **Cause:** the scale of the model import and of the sync differ.
- **Do:** use **Import at Scale 1.0 From Now On** from the warning and import the models again.

### Accessories in the PMM are not imported

- **Cause:** accessories are built by FX, which is the other half of the extension. Without FX, Core only logs a notice.
- **Do:** make sure FX is available and enabled, and that **Sync Accessories** is on. See
  [Accessories and effects](manual/core/pmm-sync/how-it-works/fx-integration.md).

---

## Rigify Remap

### The Rigify Remap panel is not shown

- **Cause:** it appears only when a sync target is a Rigify rig created with **MMD Tools Append**. Other Rigify rigs are
  not detected.
- **Do:** convert the model with MMD Tools Append first.

### A limb does not follow the PMM correctly after I switched IK/FK

- **Cause:** the remap reads each limb's IK/FK switch when it runs. A later change of the switch is not part of the
  change-detection signature.
- **Do:** set the switch, then use **Force Resync** for the model.
- **See:** [IK or FK: the limb switch](manual/core/rigify-remap/how-it-works.md#ik-or-fk-the-limb-switch).

### A bone is listed as _Missing_

- **Cause:** the PMM moves that MMD bone but no Rigify control is mapped to it.
- **Do:** **Edit Mappings** → pick a control for it → sync. A control can follow only one MMD bone, so two rows with the
  same control turn red.

---

## FX Import

### The effect did not get applied

- **Cause:** one of three rules decided. FX uses (1) the **Effect File** you chose, (2) the PMM's **`.emm`**, (3) a
  same-name `.fx` beside the `.x`. The `.emm` can say `none`, or name a file that cannot be found on this machine.
- **Do:** read the note in **Accessory Effects** and the path in **Effect File**. If the `.emm` names a file you moved,
  choose the effect file yourself.
- **See:** [Which `.fx` file is used](manual/fx/import.md#which-fx-file-is-used) and
  [how the `.emm` is matched](manual/core/pmm-sync/how-it-works/fx-integration.md#matching-accessories).

### An accessory is hidden

- **Cause:** the `.emm` marks it hidden (`hide`, or `Show = false`), as in MME.
- **Do:** change it in MME and save, or use **Keyframe Visibility** / the eye toggle in Blender.

### The accessory imported as a plain mesh, with no effect

- **Cause:** the `.x` is a **binary** `.x`. FX can build effects only from a text `.x`; the build reports it.
- **Do:** convert the file to a text `.x`.

### A layer of the effect is invisible

- **Cause:** a texture could not be found. A missing texture reads as **transparent black**, so the pass still builds and
  that layer shows nothing.
- **Do:** keep the original folder structure (`../Texture/…` is common) or set **Accessory Folder**. See
  [Textures](manual/fx/shader-nodes.md#textures).

### One pass looks flat, and the log says _pixel shader not converted_

- **Cause:** the pixel shader uses something that has no shader-node equivalent: a **bit operation** on a per-pixel value,
  or a **texture read inside a shared function**. FX gives only that pass a plain material.
- **Do:** nothing is broken; the geometry is right. Edit the material by hand if you need the look.
- **See:** [Unsupported operations and approximations](manual/fx/how-it-works/shader-translation.md#unsupported-operations-and-approximations).

### A pass is slow, and the log says _using the Python backend_

- **Cause:** the vertex shader contains something that cannot be a node graph (for example a **data-dependent loop**).
  Only that pass falls back to numpy.
- **Do:** it works but recomputes per frame; **Bake** it. **Live Effect Preview** can be turned off to scrub faster.
- **See:** [When an operation cannot be translated](manual/fx/how-it-works/geometry-nodes-translation.md#when-an-operation-cannot-be-translated).

### Part of the effect is missing, or a ribbon looks faceted

- **Cause:** build-time culling removes what was never visible under the sampled states, and **Geometry Tolerance** merges
  rows of strips.
- **Do:** lower **Geometry Tolerance** (0 keeps every row) and rebuild. If geometry is missing that MMD shows,
  **Clear Effect Caches**, rebuild, and report it with the `.fx`.
- **See:** [Culling](manual/fx/how-it-works/culling.md#when-something-is-missing).

### The first build takes minutes

- **Cause:** pre-cull analyses every vertex of a heavy effect once. In the measured Thunder run, a cold build took 49.8 s
  and a warm one 3.4 s.
- **Do:** wait for the first build. **Build Memory: Low** lowers peak RAM (not time). Leave **Pre-cull Cache** on.
- **See:** [Cache Architecture](manual/fx/how-it-works/cache.md).

### I changed a parameter and nothing happened

- **Cause:** parameters with the **wrench** icon change geometry: the effect is marked out of date until you rebuild (or
  **Auto Rebuild** is on). A **link** icon means a controller takes the value over.
- **Do:** press **Rebuild Changed Effects**.
- **See:** [Effect Parameters](manual/fx/shader-nodes.md#effect-parameters).

### My node or material edit disappeared after a rebuild

- **Cause:** a rebuild replaces any pass whose inputs changed. Generated trees are output, not storage. In a measured test,
  a gamma edit survived one rebuild and was reset by the next.
- **Do:** keep lasting changes in the exposed parameters; re-apply tweaks after a rebuild.
- **See:** [Which edits survive rebuilds](manual/fx/how-it-works/geometry-nodes-translation.md#which-edits-survive-rebuilds).

### Cycles renders the effect black or too dark

- **Cause:** effects use stacked blended transparency, and Cycles stops at the scene's **Transparent** bounce limit or the pass material has low gamma.
- **Do:** under Light Paths, raise **Transparent** bounces. In pass materials, increase **Gamma**.
- **See:** [Rendering](manual/fx/shader-nodes.md#rendering).

### Baking runs out of memory

- **Cause:** Blender keeps every baked frame of a pass in RAM, including disk bakes.
- **Do:** bake fewer frames or fewer passes at a time; close other applications. FX removes attributes only the material
  needs before the Bake node to reduce it.

### I cleared the caches but the bake is still there

- **Cause:** there are three different stores. **Clear Effect Caches** removes only the build cache.
- **Do:** use **Clear All** for project bakes and **Clear Shared Bakes** for the shared store.
- **See:** [What clears what](manual/fx/how-it-works/cache.md#what-clears-what).

### The effect library cannot be updated ("being updated by another Blender")

- **Cause:** a lock file guards `mme_core.blend` while it is rewritten. A lock left by a crash expires after 120 seconds.
- **Do:** wait, or close the other Blender. FX falls back to the bundled copy until Blender restarts.
- **See:** [Staying up to date](manual/fx/how-it-works/shared-library.md#staying-up-to-date).
