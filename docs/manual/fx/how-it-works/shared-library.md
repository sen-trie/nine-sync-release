# Shared Node Library

Many generated node groups are the same from one effect to the next: the MMD camera, the object matrix, the conversion
from clip space back to object space, `mul(float4, float4x4)`, the HLSL helper `inv_pow`. Rebuilding them for every
effect would be slow and would fill every `.blend` with duplicates.

FX keeps them in one library file, **`mme_core.blend`**. Effects _append_ the groups they need from it instead of
building them. Most artists never open it. This page explains what is in it, how it stays correct across updates, and what
the **Core Node Library** panel buttons do.

## What the library holds

The bundled library contains these groups:

<!-- prettier-ignore -->
| Group | Purpose |
|---|---|
| **Blender to MMD matrix** | converts an object's Blender matrix to the MMD row-vector convention |
| **Camera (MMD)** | view and projection matrices and camera position from Blender's active camera |
| **Clip to object (MMD)** | converts a clip-space position back to object space |
| **Light (MMD)** | light direction and colour for effects that read the light |
| **Particles to Instances** | one instance per sprite quad (used by [particle passes](geometry-nodes-translation.md#particles-and-instance-editing)) |
| **fn getRandom [GN]** | the common `getRandom` HLSL helper |
| **fn inv_pow [GN]**, **fn inv_pow [SH]** | `inv_pow` for Geometry Nodes and for shader nodes |
| **mul(float3, float3x3)**, **mul(float3, float4x4)**, **mul(float4, float4x4)** | matrix multiplication |

Groups for the HLSL functions of an effect you import (`fn …`) and for HLSL intrinsics (`in …`) are _added_ to your own
copy of the library as you import effects. This is the **Grow Library Automatically** option: Thunder's own
helper functions, for example, are expensive to rebuild, so the library keeps them.

## Keys and versions

Each group is stored under a **key**, never just a name. The key identifies the group's _meaning_, so two files that
both contain "inv_pow" know whether it is the same group:

<!-- prettier-ignore -->
| Key | Group kind |
|---|---|
| `core:…:GN:v2` | fixed standard groups (camera, matrices, clip space) |
| `fn:<GN or SH>:<name>:<hash of the function>:v2` | an HLSL function, keyed by a hash of its definition |
| `in:<GN or SH>:<intrinsic signature>:v2` | an HLSL intrinsic |

The trailing **`:v2`** is `MME_CORE_VERSION`. Bumping it means "the groups changed shape, do not reuse old ones". The
suffix is how FX compares libraries: **never by file timestamp**.

## Where the file lives

<!-- prettier-ignore -->
| File | Role |
|---|---|
| `data/mme_core.blend` inside the add-on | the **bundled** library. **Read-only input**: the add-on never writes it |
| `mme_core.blend` in the add-on's user folder (`extension_path_user`, or Blender's datafiles folder `ninesync_fx` for a development install) | **your** library, the one FX reads and grows. Survives add-on updates |

If the user folder cannot be created, the bundled file is used read-only and no new groups can be saved.

## Staying up to date

Once per session (and before the first library use), FX compares the bundled and the user library
(`mme_library_action`):

<!-- prettier-ignore -->
| Situation | Action |
|---|---|
| Your library is missing or empty | **replace**: install the bundled one |
| The bundled version is **newer** than yours | **replace** (your old file is kept as `mme_core.blend.bak`) |
| Same version, the bundled one has groups you lack | **merge**: bundled groups win duplicates; groups only you have (for example grown from Thunder) stay |
| Same version, nothing new | **keep** |
| Your library is **newer** than the bundled one | **keep**, and read your file |

This is what makes it safe to run an older and a newer FX against the same user folder: a newer library is never
overwritten by an older add-on.

### Handling errors

- **Lock file.** Every change is done under `mme_core.blend.lock`. Two Blenders adding groups at once would otherwise lose
  one swap. A lock left by a crash expires after **120 seconds**.
- **Atomic swap.** The new library is written to a temporary file, validated (every key it promised exists at the expected
  version, nested groups intact), and moved into place. The old file reaches `.bak` first, and only a library worth
  keeping does, so a damaged file cannot replace a good backup.
- **Recovery.** If your library cannot be read, it is moved aside and the `.bak` is restored if it is good.
- **Fallback.** If anything fails, FX leaves your file alone and uses the bundled copy until Blender restarts.

## The Core Node Library panel

<!-- prettier-ignore -->
| Button / option | What it does |
|---|---|
| **Open FX Library .blend** | Opens the library file FX reads and writes. It asks first, because it may start a second Blender so your current file stays open |
| **Grow Library Automatically** (on by default) | After an import builds new shared groups, adds them to your library so later imports append them |
| **Save Shared Groups to Library** | Writes every shared effect group in the **current** file into your library |
| **Rebuild Standard Groups** | Rebuilds the standard groups (camera, matrices, clip space, common intrinsics) with this Blender version and saves them. Function groups from imported effects are kept |

<!-- prettier-ignore -->
!!! tip "When to use Rebuild Standard"
    The button rebuilds the standard groups "with this Blender version". Use it after changing Blender versions if
    effects stop building, so the library is regenerated for the Blender you are running.

## What this means for your files

- A `.blend` that uses an effect **contains the groups it uses** (they are appended). It does not depend on your
  library afterwards, so you can send the file to someone else.
- Editing a shared group in a `.blend` changes only that file's copy. **Save Shared Groups to Library** would write it
  back into the library, which affects _later imports_, never files that already exist.
- Deleting your `mme_core.blend` is safe: the next session installs the bundled one again. You lose only the groups you
  had grown, which are rebuilt on the next import.

## Related pages

- Source: [`nodes/library_store.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/library_store.py),
  [`nodes/standard_groups.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/standard_groups.py),
  [`nodes/core_library.py`](https://github.com/sen-trie/nine-sync-fx/blob/master/nodes/core_library.py)
