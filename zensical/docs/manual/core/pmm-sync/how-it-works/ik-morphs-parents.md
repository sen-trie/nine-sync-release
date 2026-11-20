# IK, Bone Morphs and Outside Parents

The [animation conversion](animation-conversion.md) turns stored keys into Blender keys. This page covers the rest of an MMD animation: what MMD *computes* while it plays and what therefore has no keys to convert. There are three cases, IK, bone morphs and outside parents. In each, Core reconstructs the computation and stores its result as ordinary keys or constraints, so that Blender plays what MMD plays without needing MMD's evaluator.

## A pose that is not in the file

Let $P(f)$ be the pose of a model at frame $f$ as MMD displays it. The PMM stores the *inputs* to $P$: the keys of each bone and morph, the IK switches and the outside-parent bindings. MMD derives $P(f)$ from them. Copying the keys reproduces $P(f)$ only if Blender evaluates those keys the way MMD does. For plain FK keys it does. For the three cases below it does not, and each fails in its own way.

| Case | What MMD computes | Why copying the keys is not enough |
|---|---|---|
| IK | solves a chain towards an IK bone with its own algorithm | Blender's IK solver reaches the same end position but can bend the knee differently |
| Bone morph | offsets bones by a weight times a stored offset | mmd_tools' VMD import plays vertex, material and UV morphs only; bone morphs are skipped |
| Outside parent | drops a bone's own parent while it is bound to another model's bone | a bone has one parent in Blender, and there is no key for "the parent changes" |

## IK switches

MMD stores, for each IK bone, whether its IK is on at each display key. `apply_ik_keys` (`sync/ik.py`) keys the *influence* of every IK constraint aimed at that bone, and of the Limit Rotation constraint of each bone in its chain, choosing them the way mmd_tools' own IK toggle does. The keys are constant, so an IK turns off exactly on its key frame, as in MMD. Before keying, each switchable constraint is returned to its bone's saved toggle, so that keys from an earlier PMM leave nothing behind. A track that keeps every IK on produces no keys, because a rig does that by default.

## MMD leg IK

An IK switch decides *when* Blender's solver runs; it does not make Blender's solver agree with MMD's. For legs the difference is visible. Both solvers reach the ankle target, but on a fast lift the knee can land on the other side. On one pose with the foot far behind the body, the overlap between Blender's leg and MMD's was 0.57–0.80 with the constraint live and 0.90–0.96 with MMD Leg IK; this is one pose, not a general rate.

The optional **MMD Leg IK** setting therefore runs MMD's algorithm itself and stores its result as FK keys (`sync/leg_ik.py`).

### Reading the keys as MMD does

`KeyTrack.at(f)` gives a bone's location and rotation at frame $f$, evaluated from the PMM keys with MMD's own Bézier curves. Each channel is eased by `bezier_ease`, the rotation takes the shortest arc, and an undershooting curve may ease past either end (`slerp_free`). Evaluating the PMM keys directly, instead of reading Blender's F-curves, keeps the solver on MMD's definition of its input. MMD's *append* transform (付与), which hands a share of another bone's movement to this one, is included, because standard rigs use it for twist and waist-cancel bones.

### The solver

For a chain of thigh and knee, `LegChain.solve` performs one step of cyclic coordinate descent per iteration, knee first, then thigh.

The knee turns about its X axis only, by the angle that brings the ankle's direction closer to the IK bone's, clamped to the knee's limits; on the first pass a bend that points the wrong way is flipped instead of clamped. The thigh then swings by the shortest rotation from the ankle's direction to the target's. Each step is capped by the PMX's angle limit per step, taken as 2.0 radians when the rig has none.

All iterations run and the closest pass is kept. Stopping at the first pass that got no closer was found to leave a leg folded far from its target, because a capped first step can overshoot. When the PMX has a toe IK, `solve_ankle` turns the keyed ankle the shortest way so that its tip meets the toe IK bone.

Positions and rotations are computed in MMD's axes. Blender and MMD differ by an exchange of Y and Z, so a rotation crosses over by conjugating its matrix with the exchange matrix $X$:

$$R_{\text{Blender}} = X\,R_{\text{MMD}}\,X, \qquad X = \begin{pmatrix}1&0&0\\0&0&1\\0&1&0\end{pmatrix}$$

`basis_quaternion` then expresses the solved rotation in each bone's own basis, through its rest orientation, which is the same crossing mmd_tools makes when it imports a VMD.

### What is stored

For each frame in the chain's span, the solved thigh, knee and ankle rotations are written as keys, one per frame, replacing the keys the importer made. Frames on which the PMM switches the IK off keep the keyed FK pose, and a frame whose solve fails numerically keeps its keyed pose, so one bad frame does not cost the whole leg. Finally `silence_constraint` sets the constraint's influence to 0 over those frames. Blender's solver does not keep a pose it is handed; it would solve the knee again on its own.

<!-- prettier-ignore -->
!!! note "Scope and limits"
    This is a **reconstruction** of MMD's loop and an **approximation** of its result: the solver follows the structure of MMD's algorithm, not its source. It applies to two-bone chains on a knee that bends about X only (`find_leg_chains`). Foot IKs of one bone, and rigs that do not follow mmd_tools' setup, stay with Blender's solver. The replaced thigh and knee keys cost one key per frame of the chain's span.

## Bone morphs

A bone morph offsets a set of bones by a stored location and rotation, scaled by the morph's weight. mmd_tools stores those offsets but does not play them from a VMD, so `apply_bone_morphs` bakes them into the bones' keys. Let $w_k(f)$ be the weight of morph $k$ at frame $f$ and $(\mathbf{t}_k, \mathbf{q}_k)$ its offset for a given bone. Starting from the bone's keyed location $\mathbf{t}(f)$ and rotation $\mathbf{q}(f)$, evaluated from its F-curves,

$$\begin{aligned}t'(f) &= t(f) + \sum_k w_k(f)\, t_k\\ q'(f) &= q(f) \otimes \operatorname{slerp}\bigl(1, q_k, w_k(f)\bigr) \quad \text{for each } k \text{ in turn}\end{aligned}$$

The rotation is applied morph by morph. As with any chain of rotations the result depends on the order, which follows the morph list. The weights come from `WeightTrack`, which is linear between keys and held beyond the first and last, as MMD plays them.

The baking runs after the importer and the leg solver, so it adds to whatever they produced. It writes one key per frame over the span of the bone's keys and of the morph keys, and keeps each rotation on the same side as its neighbours (`keep_continuous`), so that a straight line between keys does not unwind a turn.

Because the weights are now part of what the keys contain, they are part of the motion fingerprint ([source fingerprints](incremental-sync.md#source-fingerprints)): changing a bone morph's weight re-runs the **Motion** clip, not only the **Shapekey** clip.

## Outside parents

MMD lets the animator change what a bone is parented to over time. At each display key, a bone's outside-parent slot is in one of three **states** ([how the PMM stores them](parsing.md#the-intermediate-representation)):

| State | Meaning in MMD | What Core produces |
|---|---|---|
| Normal | the bone keeps its own skeletal parent | nothing; the bone's own keys play |
| Released | the bone is detached from its parent and placed in the model's own frame (the "ground" or model-frame release) | solved keys, for a bone that has a parent |
| Bound | the bone's own parent is dropped and its keys are read in another model's (or its own model's) bone frame | a Child Of constraint for a bone without a parent, solved keys for a bone with one |

A binding, a release and a return to normal parenting each take effect **on the frame of the key that switches it**, not a frame later.

### The switch frame

MMD does not blend between two bone keys that sit under different states. Where two keys of the same bone straddle a change, the first key's value is held until the switch frame, and from that frame on the second key's value is used. The importer would blend them, so `hold_across_changes` makes the first key constant and keys the second key's values, also constant, on the switch frame.

Take a bone keyed at frames 0, 40 and 100. The display track releases it into the model's frame at frame 40, binds it to a hand at frame 70, and returns it to normal parenting at frame 130:

| Frames | State | What plays |
|---|---|---|
| 0 to 39 | normal | the bone's own key from frame 0, held; it does not blend towards the key at 40, which belongs to the released state |
| 40 to 69 | released | the key at 40, placed in the model's frame, from frame 40 on |
| 70 to 129 | bound to the hand | the key's values read in the hand's frame, from frame 70 on; the key at 100 does not blend backwards across the switch |
| 130 and later | normal | the bone's own parent again, from frame 130 |

Earlier versions delayed a release by a frame after its key. That rule was removed when a frame-by-frame comparison with MMD 9.32, on switches in both directions, showed that the switch lands on the key's own frame.

### Where a bound bone goes

Let $M_{\text{posed}}$ be the world matrix of the parent bone as posed, $R_p$ and $R_b$ the rest *rotations* of the parent and of the bound bone, and $B(f)$ the bound bone's own local keys as a matrix. MMD's bone axes are the world's axes, while a PMX bone has its own rest roll, so both rolls must be removed. `bound_matrix` expresses the desired world transform of the bound bone as

$$M_{\text{want}}(f) = M_{\text{posed}}(f)\, R_p^{-1}\, R_b\, B(f)$$

with no rest offset added: the key is the placement *relative to the parent bone*, in the parent's posed frame. A bone released into the model's frame uses its rest head instead: its placement is the armature's world matrix, a translation to the bone's rest head, its own rest roll and its key.

How $M_{\text{want}}$ is realized depends on whether the bone has a parent of its own.

**A bone without a parent** receives one Child Of constraint on the parent bone, keyed on and off at the binding's key frames with constant interpolation. Its inverse matrix is composed in the *armature's rest space*: the inverse of the parent bone's rest rotation, times the bound bone's rest rotation, times the inverse of the bound bone's rest matrix. Scale inheritance is off. Because the inverse is built in armature space rather than world space, the live placement follows `bound_matrix` and stays right when the armature's root object is moved or rotated. The constraint stays live, so if the parent model's motion changes later, the bone follows without being solved again.

**A bone with a parent** cannot be handled by a constraint, since a constraint cannot remove the bone's own parent chain. For each frame on which the binding is on, the solver computes the *desired world pose* $M_{\text{want}}$ and divides out the bone's rest transform under its *evaluated ordinary parent chain*, the bone's own parent as posed at that frame; the result is the local location and rotation to key. For a bone released into the model's frame, the desired pose is the release pose described above. These solved keys are fixed samples: they do not follow later changes to the parent's motion until the next sync, which is why a parent's motion edit must resync the dependent model ([outside parents as a source](incremental-sync.md#outside-parents-a-source-outside-the-model)).

A binding whose parent model has no Blender target, or whose parent bone is missing from that rig, is skipped with a warning naming the model or the bone, and the bone keeps its own keys. A bone bound to another bone of the *same* armature is supported, as long as the parent bone exists and is not the bound bone itself.

### Bound runs and bulk curve writing

The solver samples whole frames in each **bound run**: the consecutive frames from the key that switches a binding on to the key that switches it off, or to the model's last frame. It does not write one `keyframe_insert` per frame. Around each run:

- the bone's *own* pose is keyed on the frame before and the frame after the run, read from its curves before anything is written, so that its own motion plays right up to the switch and again from the frame the binding ends, and the solved values do not bleed into the neighbouring segments;
- the key before a run and the run's last key are held until the next frame, because MMD switches on the frame;
- the solved frames inside a run are merged into the existing curves in bulk (`merge_linear_keys`) with **linear** interpolation, and the new keys get auto-clamped handles. Each rotation is chosen on the same side as the previous frame's, so a straight line between samples does not unwind a turn.

The first two solved frames of each bone are still keyed with `keyframe_insert`, because only those can reshape the handles of the keys next to the run. The interior keys are linear and carry their own handle values, which differ from those an earlier writer stored one frame at a time. Nothing evaluates those handles inside a solved span, and the evaluated curves agree to within float noise, but the stored handles should not be read as identical to older output.

<!-- prettier-ignore -->
!!! note "What is reproduced is the evaluated pose"
    The solve reproduces the pose Blender *evaluates* from the rig. It does not run MMD's own evaluator, so a rig that evaluates differently from MMD (a different IK result, or constraints that move the bone after Core's keys) reproduces that rig's result.

### Solver evaluation

The solver needs the evaluated pose at each solved frame, and that means changing frames. A frame change in a full production scene evaluates every object in it, every mesh deformation included, so the solver first tries to evaluate a smaller scene.

1. **Dependency closure.** `solve_closure` collects the objects the solved poses can depend on: the armature being solved, the parent armatures, each object's parent, the targets of object and bone constraints, the targets of modifiers and the objects read by drivers, repeated until nothing new is reached. Only armatures, empties and meshes are accepted.
2. **Isolated scene.** When the closure can be shown to be complete and to evaluate the same on its own, the solver creates a temporary scene (`NineSync_solve`) holding only those objects, copies the home scene's frame-rate settings and steps that scene. It needs no window, so it also works in background mode.
3. **Full-scene fallback.** When the closure meets something it cannot reason about, the solver evaluates the full scene instead. The triggers are a scripted driver that is not a simple expression, a driver that reads anything other than objects, a simulation or scene-time modifier (cloth, soft body, fluid, particles, Geometry Nodes and similar), rigid-body or rigid-body-constraint data on an object *in the closure*, and an object type outside the supported set. Physics objects that the closure never reaches do not count and can stay in the scene.

Either way the *evaluated* copies of the objects are read, not the originals. Afterwards the temporary scene is deleted and the home scene's frame is restored, both in a `finally`, so a failure still cleans up. Every internal frame change is wrapped in the [internal-frame marker](accessory-fx-integration.md#internal-frame-stepping), so that FX does not mistake it for you scrubbing the timeline.

### Session solve cache

A forced resync imports the same VMD and would evaluate every bound frame again. The solve cache (`sync/solve_cache.py`) lets a solve whose inputs are unchanged be reused.

- **Key.** A content hash of the solve's jobs and frame spans; the Blender version and the scene's time settings; and, for every object of the dependency closure, its animation (curves and handles), NLA layout, drivers, constraints, modifiers, rest poses and *unanimated* transforms. A transform channel that nothing animates is held, and changing it moves the solve, so it is part of the key.
- **Verification.** Before a stored solve is used, up to six frames are evaluated again: the ends of each job and some in between. They must agree with the stored values to within $10^{-6}$; a solve that does not agree is rejected and computed again in full.
- **Size and lifetime.** The cache holds at most eight solves and drops the oldest first. It lives in memory for the session only, is not saved in the `.blend`, and is cleared when a file is loaded and when Core is unregistered.
- **Conservative misses.** When the closure cannot be established (the full-scene fallback) there is no key, and nothing is stored or reused. Anything the key does not cover can only cause a miss or a rejection by the spot check, never a wrong reuse.

The cache is separate from the patching of Rigify actions ([Baking a Remap](../../rigify-remap/how-it-works/baking.md)), which has its own signature and reuse rules.

## What it costs

The leg solver costs $O(N_{\text{frames}} \cdot I)$ per chain, where $I$ is the iteration count: 40 by default, taken from the PMX when it carries one, and capped at 255. Bone-morph baking costs $O$(frames × affected bones × morphs per bone). Solved outside-parent keys need a frame change for every frame in the union of all binding spans, which makes them the slowest of the three on long bindings; the isolated scene, the bulk writes and the solve cache exist to reduce that. Constraints cost nothing per frame at sync time. Core logs the time of each phase and the solver's counters (frame changes, keys written, cache hits) to `NineSyncLog` ([timing summary](index.md#the-timing-summary)).

### A measured example

The component report (`tests/perf/CORE_OPTIMIZATION_RESULTS.md` in Core) measured these changes with headless Blender 5.3.0 and mmd_tools 4.5.14 on a corpus of 18 projects: five cold syncs per project and build, each in a fresh process, reported as medians. The baseline is Core at commit `961bfe3` (the `v0.9.0` tag). On the one project with outside parents onto mapped models (3,347 solved frames), a cold sync went from 16.540 s to 7.021 s, and a forced resync from 21.311 s to 2.571 s once the cache hit: 1.7 s in the importer and 14 ms for the solve from the cache, its six verification frames included. Most of the other 17 projects changed by a few percent, from the faster parse alone.

These figures belong to that comparison on that corpus and promise nothing for another project. They also answer a different question from the later MMD 9.32 release check, which asked whether the pose matches MMD's. That check **deliberately changed what the solver does** relative to the baseline (the edge keys, the switch-frame rule and the armature-space inverse described above), so the final solver is not output-equivalent to the baseline. Sparse re-solves of unchanged frames, leaving rest-only tracks out of the temporary VMD, and an experimental FK-only evaluator were investigated and did not ship.
