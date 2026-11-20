# Animation Conversion

This page follows one model's keys from the parsed project into Blender actions, and then the scene-level tracks: camera, light, visibility and audio. The parts of MMD's playback that are computed rather than stored are on [IK, Bone Morphs and Outside Parents](ik-morphs-parents.md).

## Keys that mean something only relative to a model

A PMM bone track is a sequence of keys $(f, \mathbf{t}, \mathbf{q}, c)$: a frame $f$, a location $\mathbf{t}$, a rotation quaternion $\mathbf{q}$ and four Bézier curves $c$. Two things keep such a key from being used in Blender as it is.

The first is *identity*. A key does not say which Blender bone it moves. It belongs to the $n$-th bone of the PMX, whose name is stored in the PMM, possibly cut short, and may differ from the name the Blender rig carries after its own PMX import. The second is *representation*. A key is relative to the bone's rest pose, in MMD's axes and units, and its curve $c$ shapes the motion *into* the key from the one before. A Blender F-curve stores one value per channel in the bone's own basis, with a pair of handles that shapes each segment.

Core does not reimplement the second conversion. mmd_tools already turns VMD motion into Blender F-curves, handles included, and its users expect exactly that result. Core therefore builds a **temporary VMD** from the PMM keys (`build_vmd`) and runs the mmd_tools importer on it (`run_importer` in `sync/mmd_tools_link.py`). The conversion of axes, units and handles is mmd_tools', and it is exact to the extent that mmd_tools is. What Core must get right is everything *around* that call: which bones receive which tracks, at which scale and on which frames.

Not every part goes through the temporary VMD. Motion and shape keys do. Model visibility and the light are keyed directly, and the camera uses a VMD of its own. Where Core works on Blender data itself (bone morphs, outside-parent keys, the leg solver, restoring your keys) it uses the slot-aware helpers in `common/animation.py`. Since Blender 5 an action holds a *slot* for each animated ID and a channel bag for each slot, so these helpers (`iter_fcurves`, `find_fcurve`, `bind_slot`) look only at the curves of the slot bound to the owner in question. This matters when one action is shared by several IDs, as it can be after a remap.

**Who owns which clip.** A resync replaces an old clip by remapping its users to the new one and then deleting it, so two owners must never both claim the same old clip as their source. A remap that took over a strip can leave two shape-key owners playing one clip. In that case `import_model` assigns the clip to a single owner, the primary shape-key owner if there is one, and gives every other owner a separate clip.

## Identity: bones and morphs

A VMD holds bone names in 15 bytes of Shift-JIS. A PMM bone name longer than that, or one containing a character cp932 lacks, reaches the importer cut, and two bones that share a prefix would then be indistinguishable. `vmd_bone_table` builds the table the importer looks names up in. It holds the PMX's original bone names, the same key mmd_tools' own table uses, and, for each bone whose name a VMD cannot hold, an *alias* made of the start of the name and the bone's PMX index, provided no other bone has the same cut name. `build_vmd` writes the alias for those tracks, so the importer finds them. A bone that still cannot be told apart (`cut` in the plan's report) is listed in the Inspector, and its keys are not applied.

The plan uses the same table to count what will arrive (`map_bones`): the tracks that are animated, the tracks that match, and the keys that are lost because no bone matches. This is the number of lost keys the **PMM Motion Inspector** shows.

Morphs are matched by `resolve_morph_names` in this order: the exact name, then the English name, then a unique cp932 prefix match for names the PMM stored truncated. A morph that resolves to nothing is reported together with the names Blender does have, which is the usual cause of "this morph does nothing".

## Scale

Let $s$ be the import scale handed to the importer. With **Auto Scale From Model**, Core takes the first usable enabled target and sets

$$s = 0.2 \cdot d_{\text{root}}$$

where $d_{\text{root}}$ is the display size of the model's root empty, from which mmd_tools' own import scale can be read back. Otherwise $s$ is the manual **Scale** (0.08 by default).

mmd_tools writes bone locations in the armature's own units, so a rig whose object is scaled, such as a Rigify conversion enlarged to MMD units, would receive locations that many times too large. `model_scale` compensates for this:

$$s_{\text{model}} = \frac{s}{k}, \qquad k = \frac{\lvert S_x\rvert + \lvert S_y\rvert + \lvert S_z\rvert}{3}$$

where $S$ is the scale of the armature's world matrix. For an unscaled armature $k = 1$ and $s_{\text{model}} = s$. Because $k$ is a mean, the correction is exact only for uniform scale.

The camera is the exception. Its interpolation matches MMD only at $s = 1.0$, which is why Sync warns about any other import scale while camera sync is on.

## Frame rate

MMD plays at 30 fps. Let $f$ be a PMM frame, $r$ the retime factor and $f'$ the frame in the scene. When **Retime to Scene FPS** is on and the scene rate $R$ differs from 30,

$$r = \frac{R}{30}, \qquad f' = \operatorname{round}(r \cdot f)$$

`retime_project` applies this to every key of every track, to the play range and to the accessory keys. It does so *before* the plan is built and before FX is called, so that Core and FX see the same timeline. Rounding can map two keys onto one frame, and `retime_keys` then keeps the later one; very dense keys may therefore merge at low scene rates.

Scaling a camera cut the same way would turn it into a blend: two keys one frame apart would become two keys $r$ frames apart, with interpolation between them. For the tracks that mean *switches* (the display track, IK keys, outside-parent keys, the camera and the light) Core holds cuts. A cut is a pair of keys exactly one frame apart whose neighbours are both more than a frame away; its second key is placed on the frame after the first, so the cut stays a cut. A run of three or more keys a frame apart is a baked track, such as a camera keyed on every frame, and is scaled like any other.

The converse limit holds as well. Because $f'$ is an integer, motion keyed between two frames of the source is not interpolated at the finer rate: retiming preserves the *timing* of the keys, not detail between them.

## Morphs

Vertex and material morphs travel through the temporary VMD like bones. Three kinds do not, and Core adds them after the importer (`sync/morph_keys.py`, `uv_morphs.py`).

**Group morphs** are expanded to their leaves, with a depth limit that guards against cyclic groups, and the leaf weights are summed per shape key, so that each shape key receives its combined weight.

**UV morphs** move texture coordinates, which a shape key cannot do. For each animated UV morph Core writes the per-vertex UV offsets into a mesh attribute and adds a shape key, named with the `MMDUV_` prefix, that carries the morph's *weight*. In each affected material it then chains `attribute × weight` additions in front of the base texture's vector input, with the weight driven from the shape key. Morph animation thus moves the texture by the same weight that drives the other morphs. This is a reconstruction in the material, not a Blender UV feature, and it works only for materials that have a base colour texture. An unchanged setup is kept rather than rebuilt, because a rebuild costs a pass over the vertices and makes EEVEE recompile every patched material.

**Bone morphs** are baked into the keys of the bones they move ([bone morphs](ik-morphs-parents.md#bone-morphs)).

MMD plays morph weights with linear interpolation between keys and holds the first and last values beyond the keyed range. Core's `sample_morph_many` and the bone-morph `WeightTrack` do the same.

## Visibility

MMD shows or hides a whole model; Blender hides individual objects. `apply_visibility` therefore keys `hide_viewport` and `hide_render` on *every* mesh of the rig, with constant interpolation, since MMD has no fade. One action with one slot is shared by all the meshes and plays from its own NLA track on each, so your active action is never replaced and still plays on top. A display track that never hides the model removes any earlier NineSync visibility animation and leaves the meshes shown.

## Camera and light

The camera takes the temporary-VMD route. `import_camera` builds a VMD from the camera keys (`build_scene_vmd`), and the importer animates an mmd_tools camera rig. The camera is not baked into keys on every frame; older notes that speak of a "camera bake" mean this path.

A key bound to a model's bone stores a look-at $z$ equal to the distance, and MMD counts it once: the eye orbits the bone at that distance and looks at it. `bound_look_at` removes the duplicate, which would otherwise add the same offset twice.

A key's parent is MMD's *follow* binding. `apply_follow` adds one Child Of constraint on the rig root for each followed bone. Its influence is keyed to 1 on the camera keys that use that bone and to 0 elsewhere, held constant, which reproduces MMD's per-key parent. Rotation follows **Follow Bone Rotation**. With it off the constraint carries the bone's position only. With it on, the constraint's inverse matrix is the inverse of the bone's rest *rotation* alone, because a PMX bone's own rest roll must not be inherited. Scale is never inherited.

This is a different mechanism from the one for bones. A *bone* bound to another model's bone is solved by its own code, and a parentless bone gets a constraint with a different inverse ([outside parents](ik-morphs-parents.md#outside-parents)).

The light is keyed directly. For each key its colour is keyed, and its location is set to the key's direction with the axes exchanged and negated, `−(x, z, y)`. Segments are linear, except between keys one frame apart, which are held.

## Audio

`import_audio` adds the PMM's audio as a sound strip at frame 0, where MMD plays it. Because projects move between machines, the file is searched for in a fixed order: the **Audio File** override, the path stored in the PMM, then the PMM's own folder, including `Audio` and `BGM` subfolders. A strip that already points at the same file is left alone, so a manual repositioning survives.

## What the conversion costs

The leg solver, bone-morph baking and the optional Rigify remap work across frames, so long, dense projects spend more time in these stages. The heaviest is the outside-parent solve, which steps frames internally and writes its curves in bulk ([solver evaluation](ik-morphs-parents.md#solver-evaluation)); the marker that tells FX those steps are not your frame changes is described under [internal frame stepping](accessory-fx-integration.md#internal-frame-stepping). Core records the time of each phase in `NineSyncLog` ([timing summary](index.md#the-timing-summary)).
