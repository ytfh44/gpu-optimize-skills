---
name: gpu-memory-scheduling
description: Load this skill and follow it when jointly scheduling GPU compute, allocation, mapping, transfers, prefetch, offload, rematerialization, barriers, or reclamation to minimize critical-path stalls and bound memory pressure.
---

# GPU Memory Scheduling

## Skill navigation

- Parent router: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- Evidence: [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md)
- Lifetime planning: [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md)
- Placement: [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md)
- Runtime mechanisms: [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md)
- Validation: [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md)

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Represent compute and memory actions in one dependency graph, then choose when legal actions run to minimize exposed stalls and bound memory pressure. A dataflow graph defines a partial order, not one mandatory total order.

Do not assume that asynchronous submission creates useful overlap. Verify readiness, independent execution resources, contention, staging lifetime, and critical-path effect.

This skill owns logical timing policy. `gpu-compiler-runtime` owns concrete capture, stream, queue, event, allocation, mapping, and framework mechanisms.

## Dependency graph and audit

Build a typed graph `G = (V, E)` that includes every material action.

Use node kinds:

- `compute`
- `allocation`
- `mapping`
- `transfer`
- `prefetch`
- `offload`
- `rematerialization`
- `barrier`
- `reclamation`

Do not impose a fixed order among node kinds. Add edges only when semantics, lifetime, capacity, or measured runtime constraints require them.

### Node and edge fields

| Scope | Record |
|---|---|
| Node | Semantic key, kind, guard, inputs, outputs, aliases, readiness, duration distribution, deadline, resource demand, capacity delta, fallback, evidence, confidence |
| Edge | Producer, consumer, type, object, lag, scope, evidence |
| Object | Size, legal placement, aliases, creation readiness, last readers, workspace, staging interval, reclamation condition |
| Overlap | Allowed and forbidden peers, independence proof, contention estimate, earliest and latest start |
| Graph | Critical path, exposed stalls, peak pressure, pressure-time, tail distribution, maximum wait, wait-cycle result |

Use edge types:

- `data-ready`
- `storage-ready`
- `ordering`
- `lifetime-hold`
- `barrier`
- `capacity-wait`

### Required invariants

- Require allocation, mapping, and valid contents before use.
- Tie prefetch and offload to real consumers, capacity windows, and deadlines.
- Require rematerialization inputs before execution and equivalent outputs before consumption.
- Insert barriers only for semantic rendezvous that explicit edges cannot express.
- Reclaim only after all readers, aliases, transfers, and protecting barriers complete.
- Record capacity acquisition, hold, and release so resource waits remain auditable.
- Reject unexplained precedence cycles and induced resource-wait cycles.

### Audit the baseline schedule

Record:

- actual start and finish times;
- ready time and queue wait;
- exposed transfer and rematerialization stalls;
- allocation and mapping delays;
- workspace and staging lifetimes;
- memory pressure by capacity domain;
- overlap and contention pairs;
- barriers and global synchronization;
- median, tail, and worst observed completion;
- starvation or long-wait events;
- runtime deviations from the expected order.

Use one representative timeline scope. Do not compare a cold run with a warm replay or mix isolated durations with end-to-end critical-path claims.

## Decision workflow

1. Declare the target metric, objective order, capacity limits, deadlines, and fairness requirements.
2. Build the complete typed dependency graph for the baseline path.
3. Attach measured or bounded duration, contention, and pressure evidence.
4. Find the precedence critical-path lower bound and the realized critical chain.
5. Locate exposed stalls, avoidable waits, excessive staging lifetimes, and pressure peaks.
6. Generate legal alternatives by moving ready actions within their windows.
7. Compare retain, move-away-and-back, and rematerialize choices when all are semantically legal.
8. Reject alternatives that violate readiness, capacity, lifetime, progress, or tail constraints.
9. Pass the policy to the runtime specialist for a feasible mechanism mapping.
10. Recompute the schedule after any inserted runtime constraint or unsupported assumption.
11. Measure the realized order and accept only end-to-end improvement.

### Compute readiness and slack

For node `i`:

```text
ready_i(t) = predecessors_complete
             and guard_enabled
             and allocation_ready
             and mapping_ready
             and required_capacity_available
```

Let `r_i` be earliest readiness, `s_i` start, `f_i` finish, and `d_i(S)` duration under concurrent set `S`:

```text
r_i = max(release_i, max_j[f_j + lag_ji])
f_i = s_i + d_i(S), with s_i >= r_i
```

For required finish `LF_i`:

```text
LS_i = LF_i - d_i(S)
slack_i = LS_i - r_i
overlap_window_i = [r_i, LS_i]
```

Do not schedule from a negative or uncertain window without a fallback.

### Distinguish critical path and contention

Compute the precedence lower bound:

```text
CP_dependency = max_path sum(node_duration + edge_lag)
```

Use the scheduled end time and realized critical chain for performance claims. The precedence path omits serialization, queueing, and shared-resource contention.

Model contention only from evidence:

```text
d_i(S) = d_i_isolated * kappa_i(concurrent_set)
```

Unknown `kappa` keeps overlap hypothetical. More concurrent work can lengthen the critical path.

Measure realized pairwise overlap:

```text
overlap(i, j) = max(0, min(f_i, f_j) - max(s_i, s_j))
```

Overlap duration is not saved time.

### Bound pressure and staging

For capacity domain `m`:

```text
P_m(t) = live_object_bytes_m(t) + workspace_m(t) + staging_m(t)
P_peak_m = max_t P_m(t)
P_m(t) <= capacity_m - declared_reserve_m
```

Track:

```text
staging_lifetime = release_time - acquire_time
staging_pressure_time = staging_bytes * staging_lifetime
```

An earlier prefetch can hide latency yet increase peak pressure enough to block other work. Optimize both effects.

### Prove reclamation readiness

For object `b`:

```text
reclaim_ready(b) = max(last_reader_finish,
                       last_alias_use_finish,
                       last_transfer_finish,
                       last_protecting_barrier_finish)
```

Do not reclaim on submission completion or on one stream's progress when another consumer remains.

## Cost model

Compare feasible alternatives under the declared objective:

```text
choice in {retain, transfer_away_and_back, rematerialize}
```

Include:

- exposed transfer or reconstruction time;
- setup, mapping, and synchronization;
- contention and lost overlap;
- staging and workspace pressure;
- critical-path change;
- median and tail latency;
- capacity relief and opportunity cost;
- starvation and progress risk.

Return Pareto alternatives when weights or lexicographic priorities are absent.

Track liveness:

```text
wait_i = start_i - ready_i
acyclic(precedence_edges union induced_resource_wait_edges)
```

Require a declared wait bound when starvation guarantees matter. Otherwise state that no bound is established.

Explicitly reject these defaults without evidence:

- prefetch as early as possible;
- maximize overlap;
- offload the largest object first;
- rematerialize whenever isolated compute looks cheap;
- insert a global barrier for convenience;
- reclaim immediately without considering churn;
- assume bandwidth, reserve, priority, or tail quantile;
- treat a local action improvement as an end-to-end improvement.

## Specialist handoffs

| Owner | Boundary |
|---|---|
| `gpu-resource-lifetime-allocation` | Defines legal live ranges, aliases, reconstruction eligibility, and safe release conditions |
| `gpu-memory-tiering-migration` | Defines legal locations, source/destination domains, and movement policies |
| This skill | Defines readiness, start/finish windows, legal overlap, deadlines, and capacity release |
| `gpu-compiler-runtime` | Selects concrete capture, stream, queue, event, synchronization, mapping, and transfer mechanisms |
| `gpu-performance-evidence` | Supplies durations, contention factors, pressure traces, and tail distributions |
| `gpu-optimization-validation` | Confirms correctness, progress, and user-facing outcomes |

Give the runtime specialist the typed graph, readiness predicates, deadlines, resource demands, capacity limits, overlap permissions, fairness requirements, and fallback. Require it to return feasibility, inserted constraints, realized ordering, overhead, and deviations.

## Failure modes and counterexamples

- A hidden dependency reads unallocated, unmapped, invalid, or reclaimed data.
- Premature prefetch increases staging lifetime or peak pressure without target benefit.
- Concurrent execution creates contention and lengthens the critical path.
- Offload round trips become exposed or consume required staging capacity.
- Rematerialization delays a consumer or duplicates unnecessary work.
- A broad barrier serializes independent work or creates a wait cycle.
- Reclamation precedes a use or retains capacity far beyond a justified window.
- Speculative work repeatedly bypasses demand or reclamation work.
- Held capacity and pending dependencies create deadlock.
- Policy text mandates concrete streams, queues, or capture mechanisms.
- Central tendency improves while the declared tail target regresses.
- Evidence covers only one local event or unrepresentative workload.

## Schedule decision record

Record:

- status: hypothesis, policy-selected, runtime-feasible, measured, accepted, or rejected;
- workload, environment, target metric, objective order, constraints, and tail quantile;
- graph snapshot and changed nodes or edges;
- baseline critical path, stalls, pressure, tail, wait, and liveness results;
- alternatives and rejection evidence;
- selected logical timing policy;
- cost inputs, sources, confidence, and unresolved unknowns;
- projected, runtime-feasible, and measured results as separate fields;
- mechanism mapping returned by the runtime specialist;
- lifetime, capacity, starvation, and deadlock proofs;
- falsifying measurement, fallback schedule, residual risks, and gate outcomes.

## Acceptance gate

Keep a memory schedule only when:

- every material action and dependency appears in the graph;
- every cost has evidence, a defensible bound, or an explicit unknown marker;
- readiness, aliasing, barriers, reconstruction, and reclamation preserve correctness;
- peak pressure remains within declared capacity and reserve;
- runtime mechanisms can realize the policy without invalidating assumptions;
- the combined precedence and resource-wait graph permits progress;
- declared starvation and tail bounds hold;
- realized contention and overlap match the decision model closely enough;
- the user-facing target improves under representative conditions;
- the decision record separates policy, mechanism, projection, and measurement.
