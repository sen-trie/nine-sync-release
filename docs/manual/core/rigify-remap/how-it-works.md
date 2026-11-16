# How Rigify Remap Works

A Rigify rig converted with **MMD Tools Append** still has its MMD bones, but you animate it using Rigify controls such as
hand IK and spine FK. Since the PMM contains motion for the MMD bones, Rigify Remap transfers that motion to the controls.

## Why not copy the pose

Naively copying each MMD bone's pose to a control would be wrong whenever the conversion **re-rolled** a bone (changed its
local axes) so the control's rest pose is not the MMD bone's rest pose. Core therefore carries the **move from rest**,
not the pose.

## The method

For each Rigify target, `retarget` in `sync/rigify.py`:

1. **Unbinds the rig.** With the bind off, the armature behaves as the plain MMD model, so its MMD bones show the VMD
   pose, IK included. (The bind properties are saved and restored at the end.)
2. For every **baked frame**, reads each MMD bone's _move from its rest pose_, computed as
   `bone.matrix @ rest_inverse`.
3. Applies that move to the matching **control**, starting from the control's _own_ rest pose: `move @ control_rest`.
4. Does this **parents first**, one level of the control hierarchy at a time with a dependency-graph update between
   levels, because a control's parent is itself driven by other controls.
5. Keys location, rotation and scale of each control.
6. Sets interpolation of the baked keys to **linear**, puts the result in an action named with the `MMDBridge_` prefix and
   `_rigify` suffix on its **own NLA track**, and restores the binds, the visibility of the meshes (hidden during the
   bake) and the rigid-body world.

```python
for frame in frames:
    scene.frame_set(frame)
    moves = {m: rig.pose.bones[m].matrix @ mmd_rest_inverse[m] for _n, m in pairs}
    for layer_pairs in layers:
        for name, mmd_name in layer_pairs:
            rig.pose.bones[name].matrix = moves[mmd_name] @ rest[name]
        layer.update()
    for name, _m in pairs:
        key_control(rig.pose.bones[name], frame)
```

_(from `retarget`, shortened)_

### Which frames are baked

`bake_frames` takes every frame where a _moving_ track has a key, plus **the middle of every gap of two frames or more**,
so a straight line between baked frames stays close to the curve MMD draws. Keys are not baked on every frame of the
timeline.

## IK or FK: the limb switch

Rigify limbs have an `IK_FK` switch (0 is IK, 1 is FK) stored on one bone per limb:

| Limb                 | Switch bone                                 |
| -------------------- | ------------------------------------------- |
| left arm / right arm | `upper_arm_parent.L` / `upper_arm_parent.R` |
| left leg / right leg | `thigh_parent.L` / `thigh_parent.R`         |

The mapping table, `CONTROLS` in `common/rigify_map.py`, has one row per (MMD bone, Rigify control) and tags each as
**`ik`**, **`fk`** or **`any`** (the control is used in either mode), and with a **group** (the limb, or the torso).
`transfer_pairs` selects the rows whose kind matches each limb's switch **as it is set at that moment**. A limb that is in
IK mode is carried through the hand IK control and the base of the chain; in FK mode, through the FK controls. Rows of
the other mode show as _inactive_ in the mappings dialog.

<!-- prettier-ignore -->
!!! warning "The switch is read, not animated"
    The remap follows each limb's switch as it is when the remap runs (below 0.5 counts as IK). The change-detection
    signature covers the mapping table version, your mapping edits and the on/off checkbox, **not** the switch itself. If
    you change a limb's IK/FK switch afterwards and want the PMM carried through the other mode, use **Force Resync**.

## The mapping table

The built-in rows come from the Rigify bind table of MMD Tools Append (GPL-3.0-or-later, credited to its authors). Only
rows with both a control and a bind are kept, and a few IK rows that table lacks are added so IK limbs are driven.

You can edit it from the panel (see [Rigify Remap](index.md#editing-mappings)):

- a row you do not touch **follows the table**;
- **Add Mapping** keeps rows for bones the table does not have;
- a control can follow only **one** MMD bone: if two rows choose the same control, both turn red and the first keeps it;
- an MMD bone can have **several** controls (an IK and an FK one).

**Missing** means a bone the PMM actually _moves_ that has no control (or whose mapping you cleared). Helper bones of the
rig are never listed as missing.

## Staying up to date

`rigify_signature` adds the table version (`RIGIFY_FORMAT = 3`), your mapping edits and the on/off state to the motion
part's hash. Editing a mapping, a new table version or turning the remap off therefore **re-runs** the remap on the next sync, while a rig that is not
Rigify keeps its old hash and is unaffected.

Core checks the installed mmd_tools API before using Rigify. See [Installation](../../../installation.md) for requirements.

## Limitations

- The remap bakes keys on the controls; it does not create an IK/FK animation.
- Only the MMD bones that the PMM moves are carried.
- A target must be a Rigify rig made by MMD Tools Append; other Rigify rigs are not detected.

## Related pages

- Source: [`sync/rigify.py`](https://github.com/sen-trie/nine-sync-core/blob/master/sync/rigify.py),
  [`common/rigify_map.py`](https://github.com/sen-trie/nine-sync-core/blob/master/common/rigify_map.py)
