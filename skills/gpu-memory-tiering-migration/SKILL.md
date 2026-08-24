---
name: gpu-memory-tiering-migration
description: Load this skill and follow it when placing or moving GPU resources across device memory, peer devices, host memory, storage, or remote tiers, including residency, prefetch, offload, replication, migration, and oversubscription.
---

# GPU Memory Tiering and Migration

## Skill navigation

- Parent router: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- Evidence: [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md)
- Physical backing: [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md)
- Logical retention: [gpu-state-reuse-eviction](../gpu-state-reuse-eviction/SKILL.md)
- Ordering: [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md)
- Validation: [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md)

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Choose placement and movement from measured capacity, topology, working-set, and transfer evidence. Treat device, peer, host, storage, and remote memory as candidates with directional costs, not as one universal speed ranking.

Do not assume asynchronous movement is hidden. A transfer is beneficial only when capacity relief or future access savings exceeds exposed movement, staging, contention, consistency, and prediction-error costs.

Treat data classification, permitted destinations, and movement authorization as feasibility constraints. Performance evidence cannot authorize a tier or path that the resource's ownership and protection contract forbids.

This skill decides where a logical object should reside and which movement actions are permitted. `gpu-memory-scheduling` decides their exact order and overlap.

## Tier and residency audit

Build one tier inventory for the deployment topology.

| Tier field | Record |
|---|---|
| Capacity | Physical capacity, safe capacity, reserve, staging peak, fragmentation margin |
| Access | Direct access semantics, registration or setup requirements, failure behavior |
| Performance | Directional latency distribution, sustainable bandwidth, variance, concurrency limit |
| Topology | Direct or staged paths, intermediate nodes, shared links, contention domains |
| Accounting | Owner, replicas, dirty bytes, metadata, placement granularity |
| Policy | Data classification, permitted destinations, authorized movers and readers, required protection and sanitization |
| Evidence | Measurement method, workload scope, concurrency, confidence, timestamp |

Do not substitute rated link bandwidth for measured sustainable bandwidth under representative contention.

### Working-set inventory

For each resource or resource class, record:

- bytes and residency granularity;
- logical lifetime and retention requirement;
- current authoritative owner and valid replicas;
- next-use distribution and deadline;
- reuse distance and access count;
- read, write, and dirty-byte volume;
- reconstruction alternative and cost;
- transfer slack and staging demand;
- prediction confidence and fallback;
- data classification, permitted tiers and paths, movement authority, isolation, required protection, consistency, and failure-recovery requirements.

Model the active working set over time. Total allocated bytes do not identify the bytes that must be resident in the next decision window.

### Define a residency state machine

Use explicit logical states when movement can overlap execution:

- `unknown`
- `absent`
- `capacity-reserved`
- `inbound`
- `resident-valid`
- `resident-authoritative-dirty`
- `replicated-valid`
- `outbound`
- `stale-or-invalid`
- `failed-or-reconciling`

Require these invariants:

- reserve destination capacity before admitting inbound movement;
- authorize the destination, path, mover, and intended readers before reserving or copying data;
- publish validity only after confirmed completion;
- permit reads only from a valid version;
- maintain one authoritative dirty owner unless an explicit consistency protocol permits otherwise;
- preserve a recoverable owner or rollback path during movement;
- preserve required protection in transit, at rest, and during staging, then sanitize released copies when the contract requires it;
- invalidate, revoke, and sanitize incomplete destination or staging copies after cancellation or failure as required by the protection contract;
- release reservations and reconcile ownership after cancellation or failure.

Express transition preconditions and postconditions here. Delegate exact events, queues, and ordering to the scheduling and runtime specialists.

### Audit migration quality

Track:

- movement bytes by source, destination, and direction;
- demand misses and exposed stall time;
- on-time, late, and unused prefetch bytes;
- writeback and reload bytes;
- post-eviction reacquisition rate;
- promotion-demotion reversals;
- residence time before reversal;
- peak staging memory;
- per-link utilization and contention;
- median and tail latency effects.

Use byte-weighted prediction metrics:

```text
prefetch_precision = useful_prefetched_bytes / prefetched_bytes
miss_coverage      = avoided_miss_bytes / baseline_miss_bytes
movement_amplification = all_movement_bytes / useful_accessed_bytes
```

Guard zero denominators and report the raw byte counts with each ratio.

## Decision workflow

1. Declare the target metric, capacity objective, latency constraints, and workload scope.
2. Inventory all relevant tiers and directional paths.
3. Build the working-set and residency-state records.
4. Reproduce the baseline misses, transfers, stalls, and capacity pressure.
5. Enumerate no movement, promotion, demotion, prefetch, offload, migration, and replication alternatives.
6. Reject actions that violate capacity, ownership, validity, destination policy, authorization, protection, isolation, or recoverability.
7. Estimate directional transfer, staging, contention, consistency, and prediction-error costs.
8. Compare each action with the no-movement alternative under uncertainty.
9. Define triggers, hysteresis, minimum dwell, cancellation, fallback, and rollback conditions.
10. Hand readiness windows and transfer constraints to `gpu-memory-scheduling`.
11. Measure the realized path and reclassify the bottleneck.

### Capacity and oversubscription

For tier `i`:

```text
C_safe(i) = C_physical(i) - C_reserve(i) - C_fragmentation(i) - C_staging(i)
excess_i(t) = max(0, planned_residency_i(t) - C_safe(i))
```

Derive reserve and fragmentation margins from measured variance and backing evidence. Do not invent a universal safety fraction.

Treat transient oversubscription as feasible only when scheduled outbound movement or reclamation completes before the capacity deadline.

### Directional path cost

For resource `x` on link `e`, measure the *realized* per-hop cost, not the nominal isolated latency:

```text
T_e(x) = L_e + bytes_e(x) / B_effective(e) + Q_e
```

where `Q_e` is only the queueing/staging component observable on that link; it does not by itself capture cross-link contention, registration, mapping, or multi-hop dependency.

For a multi-hop path, `max_e T_e` and `sum_e T_e` are useful **structural reference points only when the per-hop costs are measured under compatible conditions**. They are **not** universal lower and upper bounds once queueing, shared-link contention, staging dependencies, retries, or pipelining alter the costs:

```text
max_e T_e <= T_path <= sum_e T_e + T_setup
  (valid only under no-shared-contention, no-staging-dependency, no-retry, no-pipelining assumptions)
```

With pipelining, `T_path` may approach the slowest stage rather than the sum. With shared or serially-staged links, it can approach or exceed the naive sum. Prefer measured path time, and model the realized path explicitly:

```text
T_path_realized = T_setup
               + T_dependency_wait
               + T_queue
               + T_copy_pipeline
               + T_sync
```

where `T_copy_pipeline` is computed from topology and the actual overlap achieved, not from a single-hop nominal figure.

### Transfer budget and exposed cost

For window `W`:

```text
U(e, W) = sum_a bytes(a, e) / [B_sustainable(e) * W]
```

Set the allowed utilization from workload headroom, not a fixed constant.

Estimate exposed movement. Distinguish three quantities — they are not interchangeable:

- `T_transfer_isolated`: copy/migration latency measured alone, with no competition. Baseline data only.
- `T_transfer_realized`: actual transfer completion time, including queueing, staging, registration, mapping, shared-link contention, bandwidth interference, source readiness, destination-capacity wait, synchronization, and multi-hop path dependency. This is the quantity to schedule against.
- `T_exposed`: how much the transfer delays the critical consumer's readiness — the end-to-end quantity that matters.

Define the consumer's readiness with and without the move:

```text
consumer_ready_without_move = R0
consumer_ready_with_move    = R1
T_exposed = max(0, R1 - R0)
```

For planning-phase estimates only, approximate the exposed time and label it as an estimate:

```text
T_exposed_est ≈ max(0, T_transfer_realized - usable_slack)
```

`T_exposed_est` is not a measured value; confirm it against `T_exposed` once the path is realized.

Reject an offload or prefetch when `T_exposed` (or `T_exposed_est` under a verified schedule) shows the inactive interval is shorter than the measured round trip and the affected consumer is critical, unless a different schedule creates enough verified slack.

## Cost model

Evaluate actions as value relative to no movement:

- **Prefetch value**: expected on-time miss cost avoided minus transfer, unused bytes, staging, and contention.
- **Migration value**: expected future access savings minus movement, writeback, capacity opportunity, and consistency.
- **Replication value**: locality benefit minus copy, holding capacity, update, invalidation, and interference.
- **Offload value**: capacity-relief value minus writeout, expected reload, exposed latency, and contention.

Use compatible units or a declared objective order. Do not add latency, bytes, and failure risk with invented weights.

When future access savings per use is positive, a break-even estimate can rank experiments:

```text
N_break_even = [T_move + C_consistency + C_contention + C_capacity]
               / [access_cost_current - access_cost_target]
```

Treat the result as a hypothesis. Use sensitivity analysis when future access probability or link cost is uncertain.

Select only actions that remain beneficial under conservative uncertainty and fit every capacity and transfer budget.

### Control prediction error and thrashing

Use separate promotion and demotion thresholds. Derive hysteresis and minimum dwell from measured amortization and reversal behavior.

Fall back to conservative demand placement or no movement when prediction confidence drops. Do not deepen speculation simply because a previous trace was predictable.

Reject a policy when movement amplification, late prefetches, unused bytes, or rapid reacquisition erase the predicted benefit.

## Specialist handoffs

| Handoff | Contract |
|---|---|
| `gpu-virtual-memory-fragmentation` | Required capacity, granularity, legal backing paths, mapping needs, and fragmentation risk |
| `gpu-state-reuse-eviction` | Treat its selected logical set, retention value, validity, eviction eligibility, dirty obligations, and reconstruction alternatives as required inputs; do not derive them here |
| `gpu-memory-scheduling` | Source, destination, mode, earliest start, readiness deadline, dependencies, transfer budget, and completion conditions |
| `gpu-performance-evidence` | Missing path measurements, transfer attribution, prediction metrics, and falsifying experiment |
| `gpu-optimization-validation` | Residency invariants, workload matrix, predicted outcomes, and rollback criteria |

Do not infer physical feasibility from logical desirability. Do not prescribe exact movement ordering in the residency policy.

## Failure modes and counterexamples

- Nominal capacity fits while reserve, staging, or fragmentation causes exhaustion.
- Rated bandwidth hides setup, asymmetry, queueing, or shared-link contention.
- An asynchronous call is assumed to create overlap.
- Prefetch arrives late or remains unused.
- Dirty movement creates writeback amplification.
- Replication consumes more capacity or update traffic than it saves.
- A multi-hop route bottlenecks on an intermediate link.
- A faster destination or intermediate path is prohibited by data classification, authorization, or protection requirements.
- Movement steals bandwidth from the primary workload.
- Prediction noise causes promotion-demotion oscillation.
- Failed movement leaves ambiguous ownership or stale replicas.
- Cancellation or rollback leaves readable partial copies, stale mappings, or unauthorized staging data.
- Coarse granularity transfers mostly unused bytes.
- Mean throughput improves while tail latency violates the target.
- Logical cache eviction is confused with physical residency eviction.
- A fixed tier order, threshold, or recency rule substitutes convention for evidence.

## Residency decision record

Record:

- objective, workload scope, capacity and latency constraints;
- resource class, current owner, replicas, and residency state;
- candidate tiers, paths, actions, and no-movement alternative;
- size, granularity, dirty bytes, staging, and reserve requirements;
- directional path measurements and shared contention domains;
- working-set, next-use, reuse, and prediction evidence;
- formula inputs, units, source, confidence, and sensitivity;
- consistency, invalidation, cancellation, and failure-recovery contract;
- data classification, permitted destinations and paths, movement authority, protection, and sanitization contract;
- trigger, hysteresis, minimum dwell, and rollback condition;
- scheduling constraints without exact ordering;
- rejected alternatives and falsifying measurements;
- disposition: measured finding, guarded policy, rejected, or unresolved.

## Acceptance gate

Keep a placement or migration policy only when:

- every relevant tier is evaluated or excluded with evidence;
- safe capacity includes reserve, fragmentation, and peak staging;
- directional paths satisfy transfer budgets under representative concurrency;
- residency transitions preserve ownership, validity, isolation, and recovery;
- every destination, path, mover, and reader is permitted and required protection survives transfer, staging, residency, and release;
- cancellation, rollback, and fallback revoke stale access and sanitize incomplete or released copies when required;
- prediction quality survives representative and stress workloads;
- measured hysteresis and dwell prevent thrashing;
- movement amplification stays below the measured break-even limit;
- the selected action beats no movement after uncertainty and contention;
- exact ordering remains delegated with sufficient readiness constraints;
- end-to-end targets improve without unacceptable capacity or tail regression;
- missing evidence produces a hypothesis or rejection, never a default offload or prefetch claim.
