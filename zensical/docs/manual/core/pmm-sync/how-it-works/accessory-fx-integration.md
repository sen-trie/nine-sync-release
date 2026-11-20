---
hide:
  - toc
---

# Accessory and FX Integration

A PMM lists accessories: a `.x` path, a track of transform and visibility keys, and the model and bone each one is attached to. It does not list the effects MME applied to them; those assignments live in a separate `.emm` file that MME saves beside the project. Building the accessory and its effect in Blender is FX's work, and reading the PMM is Core's. This page describes how the two meet without depending on each other. [How the parts fit together](../../../index.md#how-the-parts-fit-together) shows where this hand-over sits among the other components.

## Two add-ons, one parser

FX needs the parsed accessory keys, the parent bindings and the project's retimed timeline. It must also work without Core, and Core must work without FX. If either imported the other, it would be unusable alone, and the combined and standalone installs would behave differently.

## The hook registry

The add-ons therefore share only a registry, kept in `bpy.app.driver_namespace["ninesync_hooks"]`. That dictionary belongs to the Blender process rather than to either add-on, and it is not saved in `.blend` files. The registry is defined by `hooks.py` (`API_VERSION = 1`), a file kept byte-identical in both repositories; it is the only contract between them.

The registry holds one table per kind of hook (`post_sync`, `clean` and `report`), keyed by owner, plus a `core` marker and a `shared` dictionary. Each add-on registers its own callbacks under its own owner id, and creates the registry on first use, so neither depends on the other being loaded first. If the registry's `api_version` differs from the one an add-on speaks, the hooks are skipped and the reason is logged: a mismatched pair degrades to "no accessories" instead of failing the sync. `fx_installed()` is true when FX has registered a `post_sync` callback, which is how Core knows whether to show its notice about accessories. In a combined install both components use the same registry, registered once.

## What Core hands over

When the models, camera and light are done, Core builds a context object and calls the `post_sync` hooks. The context is built *after* retiming, so FX sees exactly the timeline Core used.

| Field | Meaning |
|---|---|
| `scene` | the Blender scene being synchronized |
| `project` | the retimed `PmmProject`, including `accessories` with their keys |
| `pmm_path` | the PMM file's path |
| `targets` | the Blender objects assigned to each PMM model, by model key |
| `unit` | the import scale |
| `retimed` | `True`: keys are already in scene frames |
| `integrated`, `core_version` | `integrated` is `True` when Core makes the call; `core_version` is Core's version |
| `progress(fraction, text)` | report progress inside the hook's own slice of the bar |
| `cancelled()` | `True` once the user has pressed Esc |

A field is never removed or renamed without raising `API_VERSION`. `targets` holds Blender objects, and FX copies the PMM path and the model links into its own settings (`mirror_context`), so that it never reads Core's data structures after the call.

### How Core runs the hooks

For `post_sync`, Core does not call `hooks.run`. The sync runs the hooks itself, as part of its own generator (`hook_steps` in `sync/hook_phase.py`), so that Esc can be heard in the middle of a hook.

- A hook that returns a **generator** is advanced one step per tick. Each step may be `None`, a text, a fraction or `(fraction, text)`. The fraction is placed inside the hook's slice of the progress bar, and the text is shown as the current stage. Between steps Core checks for a cancel.
- A hook that returns a plain value runs inside one tick.
- The **result** is normalized. A plain integer is the imported count, `None` counts for nothing, and a dict may carry `imported`, `failed` and `warnings`, each optional and checked. A malformed result or field costs a warning in the sync summary, never the whole result.
- `clean` and `report` hooks do not use this runner and keep the ordinary registry call.

FX detects a Core that can drive generators (`hasattr(ctx, "cancelled")`) and returns its generator only to that Core; an older Core receives the plain integer result.

### Cancellation and failure

Esc is cooperative. Core honours it at the yield after each step of the generator, and FX also checks `cancelled()` between accessories, so Esc is heard between accessories and between effect passes. It is not heard in the middle of one pass build, so a long build or import can take a while to yield. When a cancel arrives, Core closes the generator, which runs the hook's `finally` blocks (FX uses them to write its pending library batch and release its state), and the rest of the sync is skipped. Work already applied stays; it belongs to the same undoable sync ([errors, cancellation and undo](index.md#errors-cancellation-and-undo)).

A hook that raises is logged with its traceback, counted as failed and kept in the summary, and it does not stop the next owner's hook. Unless the user cancelled, the sync then continues to the audio. FX's own entry point catches failures and returns `{"imported": 0, "failed": 1, "warnings": [...]}`, so the summary reports an accessory or effect failure apart from a model failure.

During an integrated sync, Core owns Blender's progress display and FX starts none of its own; FX's standalone operators draw theirs. FX also batches its writes to the [shared node library](../../../fx/how-it-works/shared-library.md#how-building-uses-the-library) during the sync. An effect whose rebuild fails can keep its previous build, and the sync outcome says so ("the previous build is kept").

### Internal frame stepping

Core steps through frames for its own work: the outside-parent solver, root-motion conversion, Rigify remaps, the mmd_tools links and the exports. FX has a frame-change handler that updates effect passes for the frame you are looking at, and running it for every internal step would waste work and could change the scene. While it steps, Core therefore sets a scoped marker in the registry's `shared` dictionary, `shared["internal_frames"]` (`internal_frames()` in `sync/frames.py`). The marker is a depth counter, so stepping loops can nest, and a `finally` releases it on an exception or a cancel.

FX's frame handler returns early while the marker is above zero. FX's own bake-only evaluation is exempt, because it needs the handler. The marker is cleared when Core unregisters or the registry is rebuilt, and it is looked up again on exit, because a file load replaces the registry while an operator may still be running.

The marker is one of two pieces of shared state in API 1. The other is Core's published `import_scale`, which FX uses as the default scale of its manual accessory import. It is present only while Core's **Set Import Scale** preference is on, is read from the preferences each time it is published rather than remembered, and is published again on registration and after every file load.

## What FX does with it

FX's `post_sync` callback calls `sync_accessories`. For each accessory it chooses an effect file by the rules in [Which `.fx` file is used](../../../fx/import.md#which-fx-file-is-used).

Matching an accessory to its `.emm` slot needs care, because MME numbers accessories in *draw order*, not by their index in the PMM. FX therefore matches by path. An absolute path must equal the file's path; a relative one, which MME writes for files inside the MMD folder, must match as a whole-component suffix. The MMD folder itself is recorded nowhere, so FX infers it from the files that both the PMM and the `.emm` list. Several copies of one file are paired in (draw order, index) order, and a file name that only one slot and one accessory have is the last resort. A plain accessory with no effect keeps its plain mesh.

### Accessory keys and bake rechecks

FX keys each accessory's transform and visibility from the PMM and records on the accessory root what it wrote (the source keys, the settings, the action and a digest of it), so that your edit to those keys can be told from the PMM's. The digest became slot-aware when Blender 5 actions gained slots; a record from before that change is adopted as it stands and rewritten, so existing accessories are not mistaken for freshly edited ones.

At the end of the effect phase FX also rechecks every baked effect it touched, because animation that Core wrote can make a bake stale ([the bake signature](../../../fx/how-it-works/cache.md#the-bake-signature)).

## Cleaning and reporting

The `clean` hook asks FX to remove the accessories and effects it created. The `report` hook adds FX's section to Core's support report: versions, settings and each effect pass.

## Limitations

The hand-over goes one way and happens once per sync, after the models, camera and light. FX cannot ask Core for more data afterwards, so anything missing from the context, such as the contents of a section Core failed to read (recorded in `accessory_error`), is unavailable to FX. The contract is versioned by `API_VERSION` rather than negotiated, so two add-ons with different versions skip the hooks and report no accessories instead of attempting a partial exchange. The trade is deliberate: it keeps the add-ons independent, at the cost of an integration that works fully or not at all. Whether the effect FX builds looks like MMD's is covered in the [FX documentation](../../../fx/index.md#limitations).
