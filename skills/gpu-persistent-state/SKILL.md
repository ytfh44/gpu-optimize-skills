---
name: gpu-persistent-state
description: Load this skill and follow it when designing runtime GPU state that survives across kernels, steps, requests, or sessions, especially when growth, mutation, snapshots, branching, checkpoint placement, ownership, or reconstruction semantics differ across state objects.
---

# GPU Persistent State

## Skill navigation

- Parent router: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- Evidence: [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md)
- Logical retention: [gpu-state-reuse-eviction](../gpu-state-reuse-eviction/SKILL.md)
- Lifetime planning: [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md)
- Physical backing: [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md)
- Placement: [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md)
- Ordering: [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md)
- Validation: [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md)

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Define each logical state object before choosing its physical representation. Classify growth, mutation, ownership, sharing, version lineage, retention, reconstruction, and cleanup independently.

Persistent state here means runtime state that survives across kernels, steps, requests, or sessions. It does not mean durable storage, crash recovery, transaction logging, or database consistency.

Separate semantic requirements from buffers, allocation, residency, copying, and reclamation. A physical mechanism must not silently redefine state identity, visibility, or mutation behavior.

## State model and audit

Inventory every logical value that survives an invocation boundary.

| Field | Record |
|---|---|
| Identity | Semantic purpose, compatibility conditions, producer, consumers, crossed boundaries |
| Schema | Logical dimensions, fields, size function, representation-independent invariants |
| Growth | Growth law, bounds, zero-growth case, truncation or compaction semantics |
| Mutation | Update rule, write set, ordering, visibility boundary, alias behavior |
| Ownership | Owner, borrowers, sharers, mutation authority, isolation domain |
| Retention | Required scope, optional performance retention, expiry event, cleanup precondition |
| Versioning | Version identifier, lineage, active head, dependency epochs |
| Snapshots | Visibility, immutability, compatibility, outstanding readers |
| Branches | Fork version, isolation, active heads, cleanup, merge support or explicit exclusion |
| Rollback | Target, descendant treatment, coupled state, later writes, active readers |
| Checkpoints | Retained versions, deltas, restore compatibility, coverage, placement-independent identity |
| Reconstruction | Inputs, exact procedure, equivalence contract, cost, workspace, verification |
| Evidence | Source, measured or declared status, confidence, unresolved unknowns |

Record logical bytes separately from estimated physical bytes. Sharing, duplication, reserve capacity, metadata, alignment, and fragmentation belong to physical mechanisms.

### Classify the mutation and growth model

Do not use one storage policy for states with different semantics.

| State model | Required contract |
|---|---|
| Append-growing | Preserve prior regions unless truncation is explicit; define append unit, growth bound, zero append, visibility, and cleanup |
| Fixed-size mutable | Define update function, write set, overlapping writes, ordering, visibility, and version identity |
| Immutable snapshot | Preserve the declared version after later updates; do not assume full copy or physical sharing |
| Branched lineage | Record fork version, branch isolation, active head, branch cleanup, and merge semantics or exclusion |
| Rollback-capable | Define head movement, coupled state, descendants, readers, and post-rollback writes |
| Sparse checkpoints | Retain selected versions plus sufficient inputs or deltas for equivalent reconstruction |

Use explicit state equations where helpful:

```text
append: S(t+1) = concatenate(S(t), delta(t))
mutable: S(t+1) = update(S(t), write_set(t), delta(t))
```

The equations describe semantics, not allocation layout.

### Separate mandatory and optional retention

- **Mandatory retention** preserves program semantics because no equivalent reconstruction path exists within the allowed cost or correctness contract.
- **Optional retention** avoids future work and must compete under `gpu-state-reuse-eviction`.
- **Reconstructable state** may be discarded only when all reconstruction dependencies remain valid and available.
- **Expired state** is semantically unreachable after a defined cleanup boundary.

Do not label mandatory state as an eviction candidate. Do not keep optional state indefinitely merely because it remains valid.

### Define ownership and visibility

Identify one authority for mutation and one authority for cleanup. Multiple readers or replicas do not imply multiple writers.

Define when an update becomes visible and which version each concurrent consumer observes. Require ordering or snapshot semantics when readers overlap mutation.

Treat owner identity and isolation as semantic fields. Physical co-location never authorizes sharing.

### Define cleanup

Specify the event that makes state semantically unreachable and the conditions that must hold before physical reclamation:

- no valid owner retains the state;
- no borrower, snapshot, branch, callback, or in-flight consumer can access it;
- required descendants or rollback targets have been handled;
- pending movement and reconstruction actions have completed or been cancelled.

Delegate exact reclamation timing to lifetime planning and memory scheduling.

## Decision workflow

1. Inventory every cross-call state object.
2. Classify each object by growth, mutation, ownership, and version model.
3. Split mixed objects or declare explicit phase transitions.
4. Define identity, compatibility, visibility, lineage, retention, reconstruction, and cleanup invariants.
5. Enumerate feasible logical policies: retain current state, retain selected versions, reconstruct, or combine checkpoints with deltas.
6. Reject policies that violate snapshots, branch isolation, rollback, cleanup, or reconstruction equivalence.
7. Compare remaining policies with evidence-backed memory and runtime costs.
8. Keep unknown terms explicit and name the measurement that resolves them.
9. Hand generic admission and victim ranking to reuse/eviction.
10. Hand physical lifetime, backing, placement, movement, and timing to their specialists.
11. Validate state transitions and repeated cleanup before accepting the design.

### Design snapshots and branches

Define snapshots by logical version and visibility. Do not require a full copy unless the semantic or physical cost model chooses one.

For a branch, record:

- parent version and branch identifier;
- shared immutable ancestry;
- branch-local mutation authority;
- whether sibling writes are invisible;
- cleanup and descendant behavior;
- merge semantics or an explicit statement that merge is unsupported.

For rollback, specify whether descendants become invalid, remain readable snapshots, or move to a detached lineage. Update every coupled state object atomically under the declared contract.

### Design sparse checkpoints

For checkpoint set `Q` and target version `t`, estimate equivalent reconstruction:

```text
R_Q(t) = min over compatible q in Q, q <= t:
         seed_cost(q)
       + sum_{j=q+1..t} apply_cost(j)
       + verify_cost(t)
```

Do not assume the nearest checkpoint is cheapest. Compatibility, delta availability, movement, and workspace can change the result.

Do not describe runtime checkpoints as durable or crash-recoverable.

## Cost model

Compute logical live bytes:

```text
B_logical(t) = sum_{v in logically_live(t)} size(v, t)
```

Do not infer physical bytes from this expression.

Compare feasible policies `P` using the declared objective:

```text
cost(P) = w_memory * peak_logical_bytes(P)
        + w_update * E[update_cost(P)]
        + w_reconstruct * E[reconstruction_cost(P)]
        + w_cleanup * E[cleanup_cost(P)]
        + w_latency * E[latency_effect(P)]
```

Derive weights from the user's objective. If priorities are absent, return Pareto alternatives instead of inventing weights.

Include version metadata, snapshot maintenance, branch divergence, checkpoint creation, reconstruction workspace, and cleanup tails when material.

Retain optional state only when expected avoided reconstruction exceeds holding, maintenance, and cleanup costs under uncertainty.

## Specialist handoffs

| This skill defines | Handoff |
|---|---|
| Logical values, versions, lineage, visibility, ownership, and permitted sharing | `gpu-virtual-memory-fragmentation` chooses physical backing and addresses; `gpu-memory-scheduling` orders copies and synchronization |
| Mandatory and permitted retention | `gpu-state-reuse-eviction` chooses admission, ranking, and logical eviction |
| Semantic expiry and cleanup precondition | `gpu-resource-lifetime-allocation` and `gpu-memory-scheduling` reclaim safely |
| Growth requires virtual reservation, segmented backing, page granularity, or compaction | `gpu-virtual-memory-fragmentation` chooses the physical backing mechanism |
| Valid reconstruction and discardability | `gpu-memory-tiering-migration` chooses placement and movement |
| Cost terms and missing evidence | `gpu-performance-evidence` measures them |
| Invariants and edge cases | `gpu-optimization-validation` performs acceptance |

Do not let downstream physical choices mutate the state contract without returning for reclassification.

## Failure modes and counterexamples

- Append-growing state has no bound, quota, termination rule, or explicit risk decision.
- Reserved capacity is mistaken for logical state size.
- A fixed-size object hides an expanding version history.
- Mutable aliases violate an immutable snapshot.
- A branch update becomes visible to a sibling.
- Rollback moves one head but leaves coupled state inconsistent.
- Reconstruction omits a dependency, delta, ordering rule, or compatibility check.
- A checkpoint cannot restore the claimed target version.
- Cleanup runs while a reader, branch, or movement remains active.
- Cleanup never runs after the final owner releases state.
- Logical sharing is counted as physical savings without evidence.
- Mandatory state becomes evictable without an equivalent reconstruction path.
- A runtime checkpoint is claimed to provide durability or crash recovery.
- One paging, growth, snapshot, or checkpoint policy is applied to every state model.
- A performance claim relies only on design inspection.

## State contract record

Record:

- state purpose and crossed runtime boundaries;
- identity, compatibility, schema, and size function;
- growth law, bounds, and phase transitions;
- mutation model, write order, and visibility;
- owner, mutation authority, isolation, and sharing rules;
- required and optional retention scopes;
- expiry event and cleanup precondition;
- version lineage and active head;
- snapshot, branch, merge, and rollback rules;
- checkpoint set and reconstruction contract;
- reconstruction equivalence, cost, workspace, and validation;
- logical costs and clearly labeled physical assumptions;
- evidence, confidence, unknowns, and falsifiers;
- selected policy, rejected alternatives, and specialist handoffs.

## Acceptance gate

Keep a persistent-state design only when:

- every cross-call object has an explicit state contract;
- every growth law has a bound or an explicit unbounded-growth decision;
- mutation visibility, ownership, and isolation are unambiguous;
- snapshots remain immutable under later writes;
- branches isolate writes as declared;
- rollback covers coupled state and descendants;
- sparse checkpoints reconstruct every promised target equivalently;
- cleanup is safe under repeated invocation and outstanding sharers;
- mandatory and optional retention remain distinct;
- logical and physical costs remain distinct;
- unknowns produce experiments, not default mechanisms;
- no generic eviction algorithm is embedded here;
- durable storage, crash recovery, and database consistency remain out of scope;
- all unresolved physical choices have named handoffs and validation evidence.
