# Rigify Remap

Rigify Remap carries your PMM's motion onto the controls of a Rigify rig converted with MMD Tools Append, so that an MMD animation can be edited with Rigify's hand IK, spine FK and other controls.

## Which rigs need it

MMD Tools Append can integrate a Rigify rig in two ways ([details](creating-rigify-rig.md#choosing-an-integration-mode)). NineSync recognises which one a target is and chooses its default accordingly.

| Integration mode | What happens on sync | Default **Remap** |
|---|---|---|
| MMD Compatibility Focused | The MMD bone names sit on the Rigify controls, so the ordinary PMM import already keys the controls. Nothing more is needed. | **Nothing** |
| Rigify Operability Focused | The MMD bones follow Rigify's deform bones, so PMM motion on the MMD bones would not move the controls you animate with. NineSync carries the motion onto the controls. | **Rigify focused** |

## Using it

The **Rigify Remap** panel appears in the **NineSync** tab only when a sync target is a rig converted with MMD Tools Append. Other Rigify rigs are not detected.

<!-- SCREENSHOT: Rigify Remap panel -->

1. Set up and sync the model as in [PMM Sync](../pmm-sync/index.md).
2. Open **Rigify Remap**. Each Rigify target has its own box.
3. Check **Remap**: **Rigify focused** carries the PMM motion onto the controls; **Nothing** leaves it on the MMD bones. Until you pick a value, it follows the kind of rig (the table above). Once you pick one, your choice is kept for that model whatever the rig kind. A project saved by an older NineSync whose old on/off checkbox was off opens as **Nothing**.
4. Optional: choose a **Clip** (it is independent of the **Motion** and **Shapekey** clips, and is cleared if you change the target). Empty or an existing action behaves as for the **Motion** clip ([where the animation goes](../pmm-sync/synchronization.md#where-does-the-animation-go)).
5. Select **Show Mappings** to see which Rigify control each MMD bone drives, and **Edit Mappings** to change them.
6. Sync again. The remap runs after the model's motion has been imported. Use **Preview** to check it first.

!!! note "Needs a Blender window for the fast path"
    The bake switches to a temporary scene, which needs an open window. When Blender runs without one (background mode), the bake runs in the current scene instead: it briefly hides the model's meshes and switches the rigid-body world off, and the result is the same but slower. Do not edit the scene while it runs.

The result is an action named `MMDBridge_<model>_rigify` on its own NLA track, with linear keys on the controls. It is separate from the **Motion** clip, which keeps the PMM motion on the MMD bones.

## IK and FK

Rigify limbs have an IK/FK switch. The remap follows each limb's switch **as it is set when the remap runs** (below 0.5 counts as IK): a limb in IK mode is carried through its hand or foot IK control and the base of the chain, and a limb in FK mode through its FK controls. Rows of the other mode show as inactive in the mapping dialog.

- The switch is read, not animated. Changing it afterwards does not mark the remap out of date, and a plain **Sync Now** skips it. Use **Force Resync** in the **PMM Motion Inspector** to carry the motion through the other mode. A forced remap re-bakes the whole clip, because the limb's mode changed which controls are carried, instead of patching only the changed frames.
- MMD's leg IK targets are always carried, even with the legs in FK, because the rig still runs MMD's IK on each knee.
- With **MMD Leg IK** switched on for the model, the legs are carried through their FK controls and the switch is keyed to FK in the remap clip, since Rigify's own leg IK would choose its own knee.

## Editing mappings

- The dialog lists PMM bones that have no control first. **Only Missing** narrows the list; the search box finds bones by either name.
- Pick the **Rigify control** for each **MMD bone** with the bone picker.
- A control can follow only one MMD bone. If two rows choose the same control, both turn red and the first keeps it. An MMD bone can drive several controls, for example an IK and an FK one.
- **Missing** means a bone the PMM actually moves that has no control, or whose mapping you cleared. The rig's helper bones are never listed.

## Resyncing and rebaking

Editing a mapping, a new built-in table version, or switching **Remap** off or on re-runs the remap on the next sync. A rebake reuses the keys of the previous remap for frames whose source motion has not changed, and bakes only the frames that did, unless most frames changed, in which case it bakes them all ([how](how-it-works/baking.md#reusing-an-earlier-bake)).

## Limitations

- The remap bakes keys on the controls, it does not create IK/FK animation or a Rigify-native animation you authored.
- Only bones the PMM moves are carried.
- The remap matches the *evaluated pose* of the MMD bones, it does not recreate MMD's original animation channels ([why](how-it-works/index.md#what-is-preserved)).

For a worked example, see [Setting Up Rigify and Importing VMD Motion](../../../examples/rigify-vmd.md).
