---
hide:
  - toc
---

# Synchronization

When you save changes in MMD, use **Preview** to see what Blender will pick up, then click **Sync Now** when you're ready.

## Retiming

MMD runs at 30 fps. If your Blender scene uses a different frame rate, turn on **Retime to Scene FPS** to keep the animation playing at the same speed. A key at frame 30 in MMD lands at frame 60 in a 60 fps scene. Camera cuts and changes to visibility or IK still take effect in a single frame. If two keys land on the same frame, NineSync keeps the later one.

If you bake physics with MMDBridge, set its export frame rate to match your Blender scene. NineSync uses the baked frames as they are.

## Checking for changes

NineSync checks each model's motion, morphs and visibility separately. It also checks the camera and light. If you only change a model's morphs in MMD, NineSync updates its **Shapekey** clip and leaves its **Motion** clip alone.

With **Sync Model Constraints** on, changes can carry over to attached models. If you edit a dancer's hand, for instance, NineSync can recalculate the motion of a prop attached to it. The preview tells you why the prop needs an update.

### Reading Preview

In **Sync Preview**, each row shows what will happen when you sync (**Create**, **Update**, **Skip** or **Blocked**), along with the old and new key counts and frame ranges. The dialog also shows which bones or morphs changed and warns if any of your edits would be overwritten. The log has the full list of changes.

Click **Sync Now** in the dialog to apply the updates. Afterwards, the panel and log show what happened, what failed and how long the sync took.

## What happens to your edits?

- If the MMD animation stays the same, NineSync skips the clip and keeps your edits.
- If the MMD animation changes, NineSync updates the affected clip and warns you before replacing any keys you edited within the PMM's frame range.
- If only the import settings change and you've edited the clip, NineSync marks it **Blocked** to protect your edits. To replace it anyway, use **Force Resync** in the **PMM Motion Inspector**. The refresh button on a model's row forces a resync for that model alone.

Keys you add outside the PMM's frame range stay in place during an update. Your own visibility keys take priority, and any animation you add on higher NLA tracks stays intact.

## Where does the animation go?

Motion and morphs go into separate NLA clips. Baked physics and Rigify remaps get their own clips too. New motion actions have names starting with `MMDBridge_`. To reuse an action, select it in **Motion**, **Shapekey** or the Rigify **Clip** field. NineSync updates its keys and keeps the strips and other references that already use it.

## If something goes wrong

If a model fails to sync, its row shows the error and NineSync continues with the other models.

Press **Esc** to stop after the current sync step finishes. Any models that have already synced stay in the scene. To undo everything that run changed, including work done before a cancellation or failure, press **Ctrl+Z**. Preview and Inspector refreshes leave the undo history alone.

For implementation details, see [Incremental Synchronization](how-it-works/incremental-sync.md).
