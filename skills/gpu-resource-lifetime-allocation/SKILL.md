---
name: gpu-resource-lifetime-allocation
description: Load this skill and follow it when optimizing GPU resource lifetimes, allocation reuse, transient aliasing, pooling, workspace capacity, materialization, rematerialization, or peak live memory across a task graph.
---

# GPU Resource Lifetime and Allocation

## Skill navigation

- Parent router: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- Evidence: [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md)
- Local materialization and fusion: [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md)
- Physical backing: [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md)
- Placement: [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md)
- Cross-call state semantics: [gpu-persistent-state](../gpu-persistent-state/SKILL.md)
- Ordering: [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md)
- Training semantics: [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md)
- Validation: [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md)

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Decide when a logical resource must exist before choosing how its storage is backed or where it resides. Model liveness from semantic dependencies and completion events, then reduce peak overlap through legal release, reuse, aliasing, pooling, or rematerialization.

Do not infer lifetime from source order, enqueue order, one observed trace, or a producer-consumer naming convention. A resource remains live until every asynchronous consumer and retained alias has completed.

This skill owns logical existence, demand, and reuse eligibility. It does not own physical mapping, tier placement, cross-call state semantics, or the exact timing of memory actions.

## Resource model and audit

Build one resource inventory for the executed task graph. Include outputs, temporaries, workspaces, staging objects, retained views, and externally visible objects.

| Field | Record |
|---|---|
| Identity | Logical value, version, producer, owner, isolation domain, mutability, observable identity, escape status |
| Size | Required-size function, units, representative and maximum sizes, current capacity |
| Growth | Growth events, observed bounds, shrink behavior, retained slack |
| Alignment | Required alignment and the contract that imposes it |
| Uses | Complete consumer set, access mode, dependency edges, hidden or retained consumers |
| Lifetime | Creation frontier, first-use frontier, last-use frontier, legal release window |
| Asynchrony | Submission domain, completion evidence, transitive asynchronous descendants |
| Reconstruction | Required inputs, equivalence contract, compute cost, synchronization, workspace, variance |
| Reuse | Alias compatibility, reset requirement, preserved contents, all-schedule non-overlap proof |
| Evidence | Workload scope, source, units, measured or inferred status, uncertainty, invalidation conditions |

Treat workspace as a first-class resource. Record its size as a function of shape, algorithm, mode, and concurrency. Do not replace concurrent workspace demand with a maximum unless exclusivity is proven.

### Define lifetime as a partial-order frontier

For resource `i` with consumer set `U_i` under dependency order `≺`, define:

```text
first_frontier(i) = minimal consumers in U_i under ≺
last_frontier(i)  = maximal consumers in U_i under ≺
```

Release storage only after:

```text
release(i) succeeds join(complete(u) for u in U_i)
```

Include copies, callbacks, collectives, device work launched by a consumer, and any library operation that retains the address in `complete(u)`.

Use event or dependency evidence instead of inserting a global synchronization merely to simplify the proof.

### Separate lifetime classes

Classify each resource as one of these logical classes:

- **Required output**: must survive until an external consumer or ownership transfer.
- **Transient value**: exists only between graph operations.
- **Workspace**: capacity whose contents have no semantic lifetime after the owning operation completes.
- **Staging value**: exists to support movement or transformation.
- **Reconstructable value**: may be discarded only when equivalent reconstruction remains feasible.
- **Escaped value**: has an unknown or external consumer and cannot be safely shortened without a stronger contract.

Do not use these classes as physical allocation policies. A transient value can still require stable addressing, and a persistent logical value can move between physical allocations.

### Measure peak overlap

For feasible execution `σ`, event cut `c`, aligned logical demand `b_i(c)`, live indicator `l_i^σ(c)`, and workspace demand `W^σ(c)`:

```text
P^σ = max_c [sum_i l_i^σ(c) * b_i(c) + W^σ(c)]
```

If scheduling remains unresolved, report a bound across feasible executions instead of one false peak:

```text
P_lower = min_σ P^σ
P_upper = max_σ P^σ
```

Distinguish this logical peak from allocator reserve, physical commitment, residency, fragmentation, and driver/runtime memory.

## Decision workflow

1. Declare the target metric, workload scope, hard capacity limit, and correctness contract.
2. Enumerate every material resource and complete the audit fields.
3. Prove every consumer, alias, escape, and asynchronous completion path.
4. Derive creation, first-use, last-use, and release frontiers.
5. Compute baseline peak overlap for representative feasible executions.
6. Identify the resources present at each peak cut.
7. Generate the smallest legal alternatives: delay creation, release earlier, right-size, share workspace, alias, pool, retain, or rematerialize.
8. Reject alternatives that lack semantic, concurrency, alignment, or completion proof.
9. Recompute peak overlap, workspace, and runtime cost for each remaining alternative.
10. Return Pareto alternatives when objective priorities are absent; do not invent weights.
11. Hand physical backing, placement, state semantics, and exact action timing to their specialists.
12. Validate measured peak and end-to-end behavior before claiming improvement.

### Right-size growth and capacity

Let required bytes be `s_i(k)`, selected logical capacity be `q_i(k)`, and proven alignment be `a_i`:

```text
b_i(k) = a_i * ceil(q_i(k) / a_i)
q_i(k) >= s_i(k)
```

Treat `b_i` as an alignment-aware logical estimate, not a confirmed physical charge.

Compare growth policies with measured change cost and slack cost. Do not choose a fixed multiplicative growth factor without workload evidence.

Record zero growth, large jumps, shrinkage, maximum growth, and repeated oscillation. A policy that reduces reallocations can still regress capacity through retained slack.

### Prove aliasing and pooling eligibility

Permit two logical resources to share storage only when all conditions hold:

- their semantic and storage requirements are compatible;
- their live ranges cannot overlap under any feasible execution admitted by the policy (unconditional aliasing); OR the policy explicitly adds an ordering constraint (e.g. A_last_use → B_create) that makes a schedule-conditioned alias safe (schedule-conditioned aliasing);
- all asynchronous completion paths are proven;
- no retained view, pointer, or external owner observes the reuse;
- the new owner is authorized for the storage and no old mapping or alias can still access it;
- cross-owner reuse fully overwrites or sanitizes residual contents before exposure;
- content-preservation and initialization requirements are compatible;
- dynamic sizes remain within guarded bounds.

Schedule-conditioned aliasing is owned by gpu-memory-scheduling, which supplies the legal ordering constraint; this skill records that constraint as a precondition rather than rejecting the alias. Distinguish the two classes when reporting eligibility.

Pooling groups compatible requests; it does not prove physical efficiency. Pass size classes, alignment, demand envelope, and reuse trace to `gpu-virtual-memory-fragmentation`.

### Compare materialization and rematerialization

For each reconstructable value, compare:

- memory peak reduction, not merely the object's byte size;
- construction and input-read cost;
- input lifetime extensions;
- synchronization and launch cost;
- reconstruction workspace;
- changed schedule and contention;
- determinism and semantic equivalence;
- number and distribution of future reconstructions.

Estimate:

```text
T_reconstruct = T_construct + T_inputs + T_sync + T_workspace_effect
memory_saved  = P_baseline - P_candidate
```

Reject rematerialization when required inputs no longer exist, reconstruction changes semantics, or the new workspace recreates the peak.

## Cost model

Evaluate each feasible policy against the user's ordered objectives and hard constraints.

Record:

- peak logical bytes and uncertainty;
- physical-memory hypothesis, clearly labeled for handoff;
- allocation and release frequency;
- retained slack and workspace demand;
- added compute, traffic, synchronization, and launch cost;
- changed critical path and concurrency;
- implementation and maintenance cost when material.

Choose only from semantically feasible policies:

```text
p* in argmin J(p), p in feasible_policies
```

Require task-supplied weights or a declared lexicographic order. Return the Pareto set when those inputs are missing.

Treat estimates as experiment-ranking tools. Accept a claimed gain only when it exceeds measurement uncertainty and satisfies the capacity target.

## Specialist handoffs

| This skill supplies | Handoff |
|---|---|
| A local producer-consumer materialization or fusion candidate | `gpu-memory-fusion-layout` decides fusion, layout, and on-chip data-lifetime changes |
| Logical demand envelope, compatibility, alias and pool candidates | `gpu-virtual-memory-fragmentation` chooses backing, granularity, mapping, and fragmentation controls |
| Lifetime windows and required availability | `gpu-memory-tiering-migration` chooses placement and movement policy |
| Escaped cross-call object and required retention interval | `gpu-persistent-state` defines identity, ownership, mutation, snapshots, and cleanup |
| Legal creation, reconstruction, and release windows | `gpu-memory-scheduling` chooses exact ordering and overlap |
| Gradient requirements, saved-value legality, randomness, or training-mode reconstruction | `gpu-training-autodiff` establishes training semantics before this skill plans eligible lifetimes |
| Missing baseline or uncertain cost | `gpu-performance-evidence` defines the next measurement |
| Candidate policy, guards, and predicted deltas | `gpu-optimization-validation` performs final acceptance |

Do not let a downstream physical mechanism silently extend, shorten, or merge logical lifetimes.

## Failure modes and counterexamples

- Enqueue order masquerades as completion evidence.
- One observed execution masquerades as all-schedule non-overlap.
- A scalar timestamp hides multiple terminal consumers.
- A retained view or escaped pointer outlives the proposed release.
- Raw payload bytes omit alignment, growth slack, workspace, or staging.
- Unproven exclusivity uses `max`; unproven concurrency uses `sum`.
- Object size masquerades as peak-memory savings.
- Pooling retains excessive capacity or introduces contention.
- Rematerialization ignores input lifetimes, synchronization, or workspace.
- Aliasing changes observable identity or in-place behavior.
- Recycled storage exposes residual contents or remains reachable from a previous isolation domain.
- A global barrier makes an unsafe plan appear safe while regressing the critical path.
- Logical savings are reported as committed or resident savings without evidence.
- A familiar allocator strategy replaces workload-specific analysis.
- Missing evidence silently becomes a default constant or threshold.

When any required consumer, size bound, completion edge, or reconstruction contract is unknown, report the plan as blocked on that fact or provide a bounded hypothesis. Do not promote it as safe.

## Decision record

Record:

- target metric, workload scope, hard constraints, and correctness contract;
- audited resource set and excluded objects;
- dependency and asynchronous completion model;
- size, growth, alignment, and workspace evidence;
- first-use and last-use frontiers;
- baseline and candidate peak-overlap scenarios;
- alias, pool, and release proofs;
- materialization and reconstruction alternatives;
- predicted memory and runtime deltas with uncertainty;
- physical assumptions delegated to other specialists;
- guards, fallback, invalidation conditions, and falsifying measurement;
- rejected alternatives and reasons;
- disposition: measured finding, guarded policy, rejected, or need more evidence.

## Acceptance gate

Keep a lifetime/allocation policy only when:

- every object has a complete consumer set or an explicit blocking unknown;
- every release, alias, or reuse has an asynchronous last-use proof;
- every cross-owner reuse proves authorization, old-access revocation, and complete overwrite or required sanitization;
- every dynamic size and growth path is guarded or represented in the model;
- alignment, workspace, staging, and peak overlap are included;
- materialization alternatives preserve semantics and include reconstruction costs;
- logical demand is not confused with physical allocation or residency;
- no backing, tier, cross-call, or scheduling decision is smuggled into this skill;
- representative measurements confirm the expected peak reduction;
- end-to-end latency or throughput stays within the accepted target;
- guards, fallback, failure cases, and remaining uncertainty are explicit.
