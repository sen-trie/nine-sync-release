# PMM Sync

PMM Sync imports MikuMikuDance (`.pmm`) animation into Blender through mmd_tools. Run **Sync Now** again after editing the project in MMD.

- [PMM Reading and Writing](reading-and-writing.md)
- [Synchronization](synchronization.md)
- [Accessories and Effects in a PMM Sync](accessories-and-effects.md)
- [How PMM Sync Works](how-it-works/index.md)

## Using PMM Sync

### One-Click Setup

For a new scene, set **Source PMM** in the **NineSync** tab and select **One-Click Setup**. It reads the PMM, imports every model the project uses that is not in the scene yet with mmd_tools, links each one to its row and runs **Sync Now**. With FX installed, the accessories and effects follow in the same sync. Without a Source PMM, it asks for a file first. The button is shown until a PMM model is linked.

- **Scale.** Models are imported at scale 1.0 while **Sync Camera** is on, because that is the only scale at which the camera's interpolation matches MMD. Otherwise they use the **Set Import Scale** preference when it is on, or else the **Scale** in **Options** (0.08 by default). A model already in the scene at another scale is named in a warning, since its motion will not line up.
- **Finding the models.** Each PMX is looked for at the path saved in the PMM, then by file name in the PMM's folder and up to four folder levels below it. A model that is not found, or that mmd_tools cannot import, is named in a warning and the rest of the setup continues.
- A project that uses the same PMX twice gets two imports, one per row.

<!-- SCREENSHOT: NineSync main panel with a PMM loaded -->

### Setting up by hand

1. Import the project's PMX models with mmd_tools. If you see a scale warning, use **Import at Scale 1.0 From Now On** and re-import the models.
2. Set **Source PMM** in the **NineSync** tab.
3. Refresh **PMX Models**. Tick each model to sync and choose its Blender **Target**.
4. To [check what will change](synchronization.md#reading-preview), select **Preview**. Select **Sync Now** to import. **Esc** cancels and **Ctrl+Z** undoes the sync. See [If something goes wrong](synchronization.md#if-something-goes-wrong).

### What to expect

- Motion and morphs go into separate NLA clips. Choose existing actions in **Motion** and **Shapekey**, or leave the fields empty to create clips.
- **Retime to Scene FPS** preserves playback speed when the scene uses a different frame rate. See [Retiming](synchronization.md#retiming).
- Accessories sync with FX installed. Eligible MMD Tools Append rigs show a [Rigify Remap](../rigify-remap/index.md) panel.

## Re-syncing and Force Resync

**Sync Now** skips unchanged clips. Use **Force Resync** in the **PMM Motion Inspector** to replace a clip with the MMD version. The Inspector also shows how many animated bones and morphs match your target. See [What happens to your edits](synchronization.md#what-happens-to-your-edits) and [Reading a PMM](reading-and-writing.md#reading-a-pmm).

## Options explained

| Panel | Option | What it does |
|---|---|---|
| Options | Auto Scale From Model / Scale | Use the first enabled model's import scale or set one manually. |
| Options | UV Morphs | Animate UV offsets in material nodes. |
| Options | Sync Model Visibility | Apply model visibility to meshes in the viewport and render. |
| Options | Sync Model Constraints | Apply outside-parent bindings between models. |
| Options | MMDBridge Physics (Experimental) | Layer an MMDBridge-baked VMD over the PMM clip. See [Retiming](synchronization.md#retiming). |
| Model row | MMD Leg IK | Match MMD's knee bend by baking thigh and knee keys every frame in the PMM range. Off by default. |
| Camera & Light | Sync Camera / Sync Light | Import camera and light animation. |
| Camera & Light | Sync Constraints / Follow Bone Rotation | Follow the model and bone in each camera key, with optional bone rotation. |
| Audio | Sync Audio / Audio File | Add PMM audio or a file you choose to the sequencer at frame 0. |

Expand **MMD Values (current frame)** under **Camera & Light** to see the current values.

## Limitations and troubleshooting

- See the [Compatibility Matrix](../pmm-create/compatibility.md) for supported features.
- If models are missing, refresh **PMX Models** after setting **Source PMM**.
- Use **Support Report** to copy a report. Find `NineSyncLog` in Blender's Text Editor. See [Reporting and Triage](../../../triage.md).
- **Clean** removes NineSync-generated data and keeps your own actions, clips and shape keys.
