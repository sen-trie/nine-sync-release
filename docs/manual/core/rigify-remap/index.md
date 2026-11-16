# Rigify Remap

Rigify Remap transfers your PMM's motion to the controls of a Rigify rig converted with MMD Tools Append.

## Before you start

- The sync target is a Rigify rig converted with MMD Tools Append.
- The **Rigify Remap** panel only appears in the NineSync tab when such a target is present.

<!-- SCREENSHOT: Rigify Remap panel -->

## Steps

1. Set up and sync the model as in [PMM Sync](../pmm-sync/index.md).
2. Open **Rigify Remap**. Each Rigify target has its own box.
3. Keep **Rigify Remap** ticked for that model (it is on by default).
4. Select **Show Mappings** to see which Rigify control each MMD bone drives.
5. To change a mapping, select **Edit Mappings**.

## Editing mappings

- The dialog lists PMM bones that have no control first. **Only Missing** narrows the list; the search box finds bones by either name.
- Pick the **Rigify control** for each **MMD bone** with the bone picker.
- **Add Mapping** adds your own; **Remove Mapping** removes one you added; **Reset Mapping** and **Reset All To Defaults** return to the built-in table.
- A control used by two rows turns both rows red.

## Limitations

- Only bones the PMM actually moves are reported as missing.
