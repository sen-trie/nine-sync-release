# Synchronization

You don't need to start over every time you change your MMD project. **Sync Now** checks what has changed and updates the parts that need it.

## Retiming

MMD uses 30 fps. If your Blender scene uses a different frame rate, **Retime to Scene FPS** adjusts the keyframes so the motion plays at the same speed. For example, a key at frame 30 in MMD becomes frame 60 in a 60 fps scene. Camera cuts, visibility and IK switches are held rather than blended.

## Checking for changes

NineSync checks model motion, morphs and visibility separately, along with the camera and light. Saving a PMM without changing its animation won't trigger an update. A morph change won't replace the motion clip, and changes to one model won't cause another model to be imported again.

You can use **Preview** to see what will be created, updated, skipped or blocked before syncing. It also shows which bones and morphs changed.

## What happens to your edits?

| Situation | What happens |
|---|---|
| The PMM is unchanged and you edited a clip | The clip is skipped, so your edits stay. |
| The PMM changed | The affected clip is updated. If you also edited it, NineSync warns you that keys within the PMM's frame range will be replaced. |
| Import settings changed and you edited the clip | The update is blocked to protect your edits. Use **Force Resync** if you want to replace the clip. |
| You added keys outside the PMM's frame range | Those keys are kept when the clip is updated. |
| You keyed model visibility yourself | Your visibility keys stay on top of the synced ones. |

**Force Resync** is in the **PMM Motion Inspector**, near the bottom of the panel. Use it when you want to replace an edited clip even though its PMM animation has not changed.

## Where does the animation go?

NineSync puts motion on an NLA track as a clip, using an action that starts with `MMDBridge_`. Morphs get a separate **Shapekey** clip, and an optional physics VMD gets its own clip. You can also select an existing action in the **Motion** or **Shapekey** field.

You can layer your own animation above these clips using NLA tracks.

## If something goes wrong

- If a model fails, its row shows the problem and the other models continue to import.
- A cancelled or failed sync is one undo step. Press **Ctrl+Z** to undo it.
- If a later section of the PMM cannot be read, NineSync can still use data it already read. See [PMM Reading and Writing](reading-and-writing.md#failure-stays-local).
- **Support Report** copies a report, and the `NineSyncLog` text is available in Blender's Text Editor.
- **Clean** removes data created by NineSync while leaving your own actions, clips and shape keys alone.
