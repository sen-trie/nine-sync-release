# Creating a Rigify Rig from an MMD Model

Use **MMD Tools Append** to turn your MMD model into a Rigify rig, then select that rig as a sync target in NineSync. For the full setup instructions, see the [MMD Tools Append wiki](https://github.com/MMD-Blender/blender_mmd_tools_append/wiki).

## Required add-ons

- **MMD Tools Append**, which adds the Rigify conversion operators.
- Blender's **Rigify** add-on (Preferences > Add-ons > Rigging > Rigify).

## Steps

1. Import the PMX with mmd_tools at the scale you plan to use for syncing.
2. Select the MMD armature. In the sidebar's **MMD** tab, open **Append Operator** and click **Add Metarig**.
3. Select the metarig and adjust its bones to fit the model. Check the spine, limbs and fingers before generating the rig.
4. With the metarig selected, open **Object Data Properties**, find **Rigify Buttons** and click **Generate Rig**. You can then hide or remove the metarig.
5. Select both the MMD armature and the generated Rigify armature, then click **Integrate Armatures**. Choose an [integration mode](#choosing-an-integration-mode).
6. In the sidebar's **Item** tab, check that **MMD Append Rigify** appears with **Bind**, eye, leg, toe and **IK-FK** controls.
7. In NineSync, set the integrated armature as the **Target** for the corresponding PMM model. The **Rigify Remap** panel appears.

<!-- SCREENSHOT: MMD Tools Append Rigify panel -->

## Choosing an integration mode

- Choose **MMD Compatibility Focused** if you mainly want to play existing MMD motion. PMM Sync keys the rig directly, and tools that expect MMD bone names can still use them.
- Choose **Rigify Operability Focused** if you plan to animate with Rigify controls, such as hand IK or spine FK. **Rigify Remap** turns the imported MMD motion into keys on those controls.

See [Which rigs need it](index.md#which-rigs-need-it) for NineSync's defaults in each mode.

## Next

- [Use Rigify Remap](index.md)
- [Set up Rigify and import VMD motion](../../../examples/rigify-vmd.md)
