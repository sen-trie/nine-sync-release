---
hide:
  - toc
---

# Setting Up Rigify and Importing VMD Motion

Set up your model with MMD Tools Append, load the VMD in MMD, then use NineSync to put the motion on the rig's controls. The PMM is what NineSync reads to get the motion. See [Rigify Remap limitations](../manual/core/rigify-remap/index.md#limitations).

## 1. Build the rig

1. Import the PMX with mmd_tools.
2. Create a metarig and adjust it to fit the model, then click **Generate Rig**.
3. Select both armatures, click **Integrate Armatures** and choose **Rigify Operability Focused**. See [Creating a Rigify Rig from an MMD Model](../manual/core/rigify-remap/creating-rigify-rig.md).

<div class="ns-media"><strong>Screenshot</strong><span>The integrated armature with its MMD Append Rigify panel.</span></div>

## 2. Prepare the PMM

In MMD, load the model and apply the VMD to it. Save the project as a `.pmm`.

## 3. Sync

1. In NineSync, set **Source PMM** to the project you saved. Choose the integrated armature as the model's **Target**.
2. Open **Rigify Remap** and check that **Remap** is set to **Rigify focused**.
3. If you want to reuse an action, choose it in **Clip**. Use **Show Mappings** to check for bones marked missing, then click **Sync Now**.

NineSync puts the control keys in a `MMDBridge_<model>_rigify` action alongside the **Motion** clip. See [Rigify Remap](../manual/core/rigify-remap/index.md).

<div class="ns-media"><strong>Video or GIF</strong><span>The rig playing the motion, with an IK hand control selected.</span></div>

## 4. Edit and resync

Edit the control keys as you would any other Rigify animation. To import the motion in a different IK/FK mode, change the limb's switch, then use **Force Resync**. See [IK and FK](../manual/core/rigify-remap/index.md#ik-and-fk).

For details on how NineSync makes the keys, see [How Rigify Remap Works](../manual/core/rigify-remap/how-it-works/index.md).
