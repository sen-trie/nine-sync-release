# Baking a Remap

`retarget` in `sync/rigify.py` evaluates the rig at selected frames and records the resulting control transforms as linear keys. The pose calculation itself is described in [How Rigify Remap Works](index.md#the-transfer).

## Which frames are baked

`bake_frames` starts from the keyframes of the model's moving tracks. Between them it samples every frame in gaps of six frames or fewer, and every second frame in longer gaps. The dense sampling of short gaps keeps quick movements, such as an IK-driven leg swing, close to the source motion. The baked keys are linear.

## Preparing the rig

NineSync saves the `mmd_append_*` properties on `torso` and sets them to zero, so that Blender evaluates the original MMD bones and their IK. With **MMD Leg IK** on, it also mutes the original leg IK constraints, which keeps the knee poses already solved, and keys the Rigify leg switches to FK. The inverse rest matrices of the source bones and the rest matrices of the controls are read once, before baking.

With a Blender window open, `enter_bake_scene` switches to a temporary `NineSync_bake` scene that contains only the rig and its parents. In background mode the bake uses the current scene instead: it temporarily hides the model's meshes, disables the rigid-body world and assigns every control matrix directly, which takes longer than baking in a temporary scene.

## Two ways to apply a pose

At each sampled frame, `moves_at` reads the source displacements $D(f)$. The bake applies them in one of two ways.

- **Most controls follow empties.** A temporary Copy Transforms constraint points each control at an empty placed at $W\,D(f)\,R_{\text{ctl}}$ in world space. One dependency-graph update then evaluates all the followers and their helper bones. `convert_space` gives the control's local transform, and a rotation-compatibility step keeps successive keys from turning the long way round.
- **The roots of Rigify IK chains are assigned directly.** Their poses depend on the IK solve. `bake_levels` groups the controls by their dependencies through parents, helper bones and constraint targets, IK poles included, and each group gets a dependency-graph update before the next. Tweak controls go last.

## Writing the action

The bake collects each control's location, rotation and scale in arrays indexed by frame, in the control's own rotation mode. `write_bake` creates a `Retargeted` layer and writes each F-curve in bulk with `foreach_set`. A limb switch that was forced to FK gets a curve with two keys.

The remap goes on its own NLA track as `MMDBridge_<model>_rigify`. If no clip was selected, `clear_remap` removes the previous remap clip and action before the new one is placed.

## Restoring the scene

Cleanup runs even if the bake fails. It removes the temporary empties and constraints; restores the mesh visibility, the rigid-body settings, the append properties, the limb switches, the muted constraints and the active action; and returns to the original scene and frame. The imported MMD motion therefore remains available after a failed remap.

## Reusing an earlier bake

`bake_signature` records the versions of the layout and the table, the active mappings, the limb modes, the leg IK setting, the frame list, the controls' rotation modes and the rest matrices. Each baked frame also has a hash of its source displacements, stored on the action.

When the signature matches and the F-curves line up with the frame list, NineSync can keep the old values and bake again only the frames whose hashes changed. If at most 70 % of the frames changed, it patches those frames and uses `keep_continuous` to align the rotations across the patched spans; above 70 % it bakes the whole clip again. Reuse assumes that the rig's constraints still evaluate the same way.

Changing an IK/FK switch alone leaves the sync plan unchanged, so it is applied with **Force Resync**. The new mode changes the bake signature, and the whole clip is baked again.
