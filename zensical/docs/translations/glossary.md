# Translation Glossary

Shared terms for everyone translating NineSync: the Blender interface of Core, FX and the combined extension, this documentation, and the README files. One glossary covers all three, so a term reads the same everywhere. How the catalogs work is in the [Developer Guide](https://github.com/sen-trie/nine-sync-release/blob/main/DEVELOPER_GUIDE.md#translations).

## Never translate

Keep these exactly as written, including case:

- File formats and extensions: PMM, PMX, VMD, `.pmm`, `.pmx`, `.vmd`, `.x`, `.fx`, `.fxsub`, `.emm`, `.blend`, HLSL.
- Product and project names: NineSync, MikuMikuDance (MMD), MikuMikuEffect (MME), mmd_tools, Blender, Rigify, EEVEE, Cycles.
- Effect parameter names and MME annotations: `Tr`, `Si`, `XYZ`, `Rxyz`, `CONTROLOBJECT` and the like, and every name that comes from an effect file.
- Names that come from the user's data: models, bones, morphs, accessories, objects, materials, effect and texture files.
- Names of generated Blender data: node groups, nodes and sockets inside generated Geometry Nodes and shader trees, collection names such as `MMD_Accessories`, and the `MMDBridge_` action prefix. Saved projects depend on them.
- Inside generated Geometry Nodes passes, these stay English because they are saved in the `.blend` and the add-on finds them by name: the frames **Edit Source Mesh**, **Edit Final Geometry** and **Edit Particle Instances**, the group **Edit Particle Points**, and modifier inputs such as **Enable Instance Editing**, **Particle Mesh**, **Transparency Order** and **Geometry Node Editing (viewport only)**. The same words in panels and tooltips are translated; when you translate them there, mention the English node name the user will see in the node editor.
- Third-party effect names (Nuke2, Thunder, SvDOF) and creator names.
- Commands, code, file paths, URLs and keyboard shortcuts.

## Terms

Where Blender already translates a word (Bake, Cache, Pass, Geometry Nodes), use **Blender's own translation** so NineSync matches the rest of the interface. Blender's catalog wins for identical text in any case.

| English | Meaning in NineSync | Japanese (draft) |
| --- | --- | --- |
| Accessory | an MMD `.x` prop placed in the project | アクセサリ |
| Bake | storing a pass's per-frame result on disk so playback does not re-evaluate it | ベイク |
| Cache | stored conversion results reused on the next import (pre-cull cache, bake data) | キャッシュ |
| Core | the PMM Bridge add-on | Core (keep) |
| Effect | an MME `.fx` file and what NineSync builds from it | エフェクト |
| Effect Controls | the panel of an accessory's effect parameters | エフェクトコントロール |
| FX | the FX Importer add-on | FX (keep) |
| Geometry Nodes | Blender's node system that runs translated vertex shaders | ジオメトリノード (Blender's term) |
| Incremental sync | re-importing only what changed in the PMM | 差分同期 |
| Outside parent | MMD's per-key parent from another model or bone | 外部親 (MMD's term) |
| Pass | one technique pass of an effect, built as its own node tree | パス |
| PMM Create | writing a Blender scene as a PMM project | PMM Create (feature name, keep) |
| PMM Sync | importing and updating a PMM project in Blender | PMM Sync (feature name, keep) |
| Pre-cull | removing geometry that can never be visible, at build time | 事前カリング |
| Preview | the dry run that lists what a sync will do | プレビュー |
| Rigify Remap | driving a Rigify rig from MMD motion | Rigify Remap (feature name, keep) |
| Sync | one run of PMM Sync | 同期 |
| Transparency Order | how see-through copies of an effect mesh are drawn | 透過順序 |

Feature names (PMM Sync, PMM Create, Rigify Remap, FX Import) stay in English in the interface so that they match the documentation and support threads. Keep placeholders (`%s`, `%d`, `{name}`), line breaks and trailing colons.