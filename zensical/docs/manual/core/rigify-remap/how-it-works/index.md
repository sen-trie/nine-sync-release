# How Rigify Remap Works

Rigify Remap samples the evaluated pose of an MMD model and bakes that motion onto Rigify controls, in an action of its own. Setup and controls are described in [Rigify Remap](../index.md).

The implementation is in [`sync/rigify.py`](https://github.com/sen-trie/nine-sync-core/blob/master/sync/rigify.py), and the default mappings are in [`common/rigify_map.py`](https://github.com/sen-trie/nine-sync-core/blob/master/common/rigify_map.py).

## Why the integration mode matters

A rig converted with MMD Tools Append contains both the MMD bones and the Rigify hierarchy, and the conversion can bind them in two directions. In **MMD Compatibility Focused** mode the Rigify controls carry the MMD bone names, so the ordinary PMM import keys those controls directly. In **Rigify Operability Focused** mode the MMD bones follow Rigify's deform bones instead. For this mode the remap evaluates the MMD motion with the rig unbound and then transfers the resulting pose to the controls.

## Detecting the integration mode

`is_converted_rig` recognizes a converted rig by `rig_id` on the armature data and `mmd_append_bind_mmd_rigify` on the `torso` pose bone. `is_mmd_focused_rig` then looks at the bone with the MMD name 上半身. If that bone has a constraint targeting a `DEF-` or `ORG-` bone, the rig is Rigify Operability Focused; otherwise it is MMD Compatibility Focused.

The detection only sets the default of **Remap**. An explicit choice, and any edits to the mapping, are saved on the model's row. `rigify_signature` adds the version of the mapping table, the mapping edits and the remap setting to the motion hash, so changing any of them triggers a remap on the next sync. The limb switches are checked separately, when [an earlier bake is reused](baking.md#reusing-an-earlier-bake).

## The transfer

At each sampled frame $f$, NineSync reads the evaluated MMD bone matrix $M_{\text{src}}(f)$ with the rig unbound. This source pose already includes MMD IK and append transforms. With $R_{\text{src}}$ and $R_{\text{ctl}}$ the rest matrices of the source bone and the control, the remap computes the displacement $D(f)$ of the source from its rest pose and applies the same displacement to the control:

$$
D(f) = M_{\text{src}}(f)\,R_{\text{src}}^{-1},
\qquad M_{\text{ctl}}(f) = D(f)\,R_{\text{ctl}}
$$

Both matrices are in armature space. Applying the displacement to the control's own rest matrix, rather than copying the source matrix, accounts for any difference in bone roll. When the pose is applied through a temporary empty, the bake converts it to world space with the armature object's matrix $W$ ([applying the pose](baking.md#two-ways-to-apply-a-pose)).

## What is preserved

The remap reproduces the evaluated pose at the sampled frames, for controls whose rest pivot matches the source bone's. Between samples the control keys are linear. The separate **Motion** clip keeps the imported animation, and the active limb mode determines which controls carry the pose.

The default mappings pair bones and controls with matching rest pivots. A custom mapping can pair bones whose rest heads lie in different places, and the same displacement can then put the control and its children somewhere other than the source pose. NineSync applies custom mappings as entered.

## Which controls are carried

`CONTROLS` is based on the bind table of MMD Tools Append (GPL-3.0-or-later), with added rows for hand IK and for the bases of IK chains. Each row pairs an MMD bone with a control and gives its group and mode (`ik`, `fk` or `any`). `transfer_pairs` selects the active rows and orders parents before children, with tweak controls last.

`limb_modes` reads the switches on `upper_arm_parent.L/R` and `thigh_parent.L/R` when the remap runs; a value below 0.5 selects IK. The exceptions for leg IK are in [IK and FK](../index.md#ik-and-fk).

One MMD bone can drive several controls. If two rows target the same control, the first wins and both rows are flagged. A bone that the PMM moves but that has no mapped control is reported as missing.

Sampling, writing the action and reuse are described in [Baking a Remap](baking.md).
