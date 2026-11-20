# Common Issues

## PMM Create

### MMD says "model structure is different"

Create the PMM again with a current Core, from the same PMX that MMD loads.

### A mesh I selected is not offered as a prop

Select a mesh that is not part of an mmd_tools model.

---

## PMM Sync

### A model shows a warning and nothing was imported

The clip is **Blocked** to protect your edits. Use **Force Resync** for that model if you want to replace them.

### I synced again and nothing changed

This is normal: unchanged parts are skipped. **Preview** shows why.

### A model updated although I did not change it in MMD

This is normal: a model bound to a changed model is solved again. **Preview** names the reason.

### Some bones or morphs do not move

Open **PMM Motion Inspector** to see which names do not reach the target, and rename them in the PMX to match.

### Preview warns that the PMM keys bones that the PMX hides

Unhide the bone in the PMX if you expect it to animate.

### Motion is too fast or too slow

Accept the notice and use **Retime to Scene FPS**.

### The models are the wrong size

Use **Import at Scale 1.0 From Now On** from the warning and import the models again.

---

## Rigify Remap

### The Rigify Remap panel is not shown

Convert the model with MMD Tools Append first.

### A limb does not follow the PMM correctly after I switched IK/FK

Set the switch, then use **Force Resync** for the model.

### A bone is listed as _Missing_

**Edit Mappings**, pick a control for it, and sync.

---

## FX: Importing

### The effect did not get applied

Read the note in **Accessory Directory** and the path in **Effect File**. If the `.emm` names a file you moved, choose the effect file yourself.

### An accessory is hidden

The `.emm` hides it (`hide`, or `Show = false`). Change it in MME and save, or use **Keyframe Visibility** / the eye toggle in Blender session.

### The accessory imported as a plain mesh, with no effect

Convert the `.x` to a text `.x`.

### A layer of the effect is invisible

Keep the original folder structure, or set **Accessory Folder**.

### "Not rebuilt" or "Not baked" mentions missing files

Restore the folder or choose the **Effect File** again, then rebuild.

---

## FX: Building and Editing

### One pass looks flat, and the log says _pixel shader not converted_

Nothing is broken. Edit the material by hand if you need the look.

### A pass is slow, and the log says _using the Python backend_

**Bake** it, or turn off **Live Effect Preview** to scrub faster.

### Part of the effect is missing, or a ribbon looks faceted

Lower **Geometry Tolerance** and rebuild.

### The first build takes minutes

Wait for the first build and leave **Pre-cull Cache** on.

### I changed a parameter and nothing happened

Press **Rebuild Changed Effects**.

### My node or material edit disappeared after a rebuild

Keep lasting changes in the exposed parameters; re-apply tweaks after a rebuild.

### The effect library cannot be updated ("being updated by another Blender")

Wait, or close the other Blender.

---

## FX: Rendering and Baking

### Cycles renders the effect black or too dark

Raise **Transparent** bounces under Light Paths, or increase **Gamma** in the pass material.

### Baking runs out of memory

Bake fewer frames or fewer passes at a time.

### I cleared the caches but the bake is still there

Use **Clear All** for project bakes and **Clear Shared Bakes** for the shared store.

### An effect shows a stale or missing bake after a sync

Press **Bake Changed**, or **Force Rebake All** to start over.
