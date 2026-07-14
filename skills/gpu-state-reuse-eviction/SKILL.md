---
name: gpu-state-reuse-eviction
description: Load this skill and follow it when identifying reusable GPU state, defining identity and validity, sharing or copy-on-write, admission, retention, invalidation, or eviction under capacity and performance constraints.
---

# GPU State Reuse and Eviction

## Skill navigation

- Parent router: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- Evidence: [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md)
- State semantics: [gpu-persistent-state](../gpu-persistent-state/SKILL.md)
- Physical backing and release: [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md)
- Physical residency: [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md)
- Ordering: [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md)
- Semantic and numerical safety: [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md)
- Validation: [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md)

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Reuse state only when it is unambiguously identified, currently valid, authorized for the consumer, and economically beneficial. Prove safety before ranking value.

Compare expected avoided work with footprint, lookup, validation, movement, maintenance, invalidation, and interference. A high hit rate does not prove a positive end-to-end result.

Treat logical invalidation, logical eviction, physical residency eviction, and physical release as distinct events. This skill owns the first two; placement and backing specialists own the latter two.

## Reuse contract and audit

Define one reuse contract for every candidate state or reusable subrange.

| Group | Record |
|---|---|
| Candidate | Logical role, producer, consumers, reuse granule, avoided work, no-reuse fallback |
| Identity | Semantic inputs, normalized parameters, dimensions, precision contract, partition coordinates, semantic version, collision handling |
| Validity | Dependency versions, captured epochs, epoch authority, completion state, invalidation events, check/use ordering |
| Ownership | Owner, namespace, isolation domain, authorized readers and writers, lifetime authority, accounting scope |
| Sharing | Allowed scope, immutability or snapshot guarantee, writable-consumer behavior, copy-on-write requirement |
| Partial reuse | Coverage representation, granule identity, per-granule validity, composition rule, missing-part fallback |
| Economics | Decision horizon, reuse probability, saved work, footprint, lookup, movement, maintenance, interference |
| Evidence | Source, workload scope, measured or inferred status, uncertainty, falsifying observation |

### Define identity semantically

Make identity keys represent logical equivalence, not storage location.

- Include every input, mode, version, layout, precision, position, or partition field that can change the result.
- Exclude addresses, allocation identifiers, physical tiers, and incidental timestamps unless they change semantics.
- Classify fields as identity, validity evidence, authorization, or metadata.
- Justify canonicalization; differently encoded values are not automatically equivalent.
- Define collision detection or use a representation with an accepted collision contract.
- Reject reuse when a required identity field is unknown.

Do not combine identity and authorization. Two objects can be semantically equal yet forbidden to share across owners or isolation domains.

### Define validity and mutation epochs

Write validity as an explicit predicate:

```text
valid(candidate, consumer, now) = identity_match
                               and dependencies_match
                               and production_complete
                               and epoch_current
                               and authorization_allows
                               and coverage_compatible
```

Capture authoritative dependency epochs when state is produced. Define reset, wrap, and concurrent-update behavior.

Invalidate on semantic change, dependency mutation, revoked access, incomplete production, or incompatible partial coverage.

Age and expiration may guide retention, but they are not correctness predicates.

Require a snapshot, lease, ordering edge, or equivalent guarantee between validation and use. Hand the concrete synchronization mechanism to `gpu-memory-scheduling` or the runtime specialist.

### Control sharing and copy-on-write

Permit shared reads only within an authorized scope and under an immutable or stable-snapshot contract.

Require a writable consumer to obtain a distinct logical version before mutation. Record whether copy-on-write is legal, what it copies, and how much it costs; delegate its physical timing and placement.

Do not infer physical deduplication from logical sharing. Separate saved logical work from saved physical bytes.

### Model partial and sparse reuse

Define the smallest reuse granule whose identity, validity, and composition are independently checkable.

For a reusable subset `A`:

```text
saved_work(A) = baseline_cost
              - [remaining_work(A) + lookup_cost(A) + compose_cost(A)]
```

Do not estimate partial value as `coverage * full_saved_work` unless measurement supports linearity.

Require a correct fallback for missing, stale, unauthorized, or incompatible granules.

## Decision workflow

1. Declare the target metric, representative workload, decision horizon, and capacity budget.
2. Enumerate reuse candidates and choose a justified granule.
3. Complete identity, validity, epoch, ownership, sharing, and coverage contracts.
4. Reject semantically unsafe or unauthorized candidates before economic ranking.
5. Measure or bound avoided work and every material cost.
6. Compare full, partial, and no reuse without assuming linear value.
7. Rank admission and retention against competing eligible state.
8. Define invalidation and logical eviction independently of physical residency.
9. Record uncertainty, fallback behavior, and the measurement that would falsify the policy.
10. Hand state mutation semantics, physical placement, and action timing to their specialists.

### Separate admission, retention, and eviction

- **Admission** asks whether a newly produced candidate should enter the logical retained set.
- **Retention** asks whether an admitted candidate remains valuable over the next decision horizon.
- **Invalidation** removes eligibility because correctness or authorization no longer holds.
- **Logical eviction** removes a still-valid candidate because another use of the budget has greater expected value.
- **Residency eviction** moves or removes one physical copy without necessarily deleting logical retention.

Do not use one policy rule for all five decisions.

## Value model

For candidate `i` over horizon `H`, estimate:

```text
E_saved(i) = sum_r P(request_r
                    and identity_match
                    and valid
                    and authorized)
                    * work_avoided(i, r)

C(i) = E[lookup + validation + movement + maintenance + invalidation]
```

For retained set `S`:

```text
J(S, H) = sum_i_in_S [E_saved(i) - C(i)] - interference(S, H)
```

Constrain effective footprint:

```text
sum_i_in_S footprint(i) <= logical_budget
```

Include payload, metadata, indexes, duplicate versions, and charged overhead in `footprint(i)` when the policy is accountable for them.

Admit or keep a candidate only when its marginal value is positive under the stated uncertainty rule:

```text
delta_admit(i) = J(S union {i}) - J(S)
delta_keep(i)  = J(S) - J(S without {i})
```

Use value density only when additivity and granularity assumptions are justified. Interference can be nonlinear.

Do not count footprint both as a hard constraint and a priced cost unless the formulation intentionally uses both.

Reject recency-only, frequency-only, age-only, largest-first, smallest-first, or admit-everything policies unless measured workload evidence supports them.

When objective weights are absent, return a Pareto set or an unresolved ranking rather than inventing a default.

## Specialist handoffs

| This skill owns | Handoff |
|---|---|
| Logical eligibility, identity, validity, authorization, admission, retention, invalidation, and logical eviction | Keep here |
| Growth, mutation, snapshot, branch, rollback, and cleanup semantics | `gpu-persistent-state` |
| Physical backing, remapping, old-access revocation, sanitization, and release | `gpu-virtual-memory-fragmentation` |
| Physical placement, residency, migration, replication, and residency eviction | `gpu-memory-tiering-migration` |
| Lookup/mutation ordering, copy timing, invalidation propagation, and reclamation timing | `gpu-memory-scheduling` |
| Reuse changes precision, approximation, ordering, determinism, or value semantics | `gpu-numerical-safety` |
| Baseline, reuse distribution, saved-work and interference measurements | `gpu-performance-evidence` |
| Correctness, isolation, and end-to-end acceptance | `gpu-optimization-validation` |

Pass the selected logical set, value curves, validity events, isolation constraints, uncertainty, and fallback requirements. Do not prescribe a physical mechanism.

## Failure modes and counterexamples

- Under-specified identity returns incorrect state.
- Over-specified identity destroys useful reuse.
- Stale or ambiguous epochs permit invalid reuse.
- Validation followed by an unordered mutation creates a race.
- Identical computation keys are treated as authorization.
- Shared mutable aliases bypass copy-on-write.
- Age-based validity accepts stale state.
- Hit-rate-only ranking retains cheap-to-recreate state.
- Payload-only accounting hides metadata and index costs.
- Partial reuse costs more to locate and compose than it saves.
- Admission churn creates repeated movement and invalidation work.
- Logical eviction is reported as immediate physical memory release.
- Device residency is treated as a prerequisite for logical retention.
- A local saved-work estimate fails to improve the target metric.
- A familiar eviction algorithm replaces an evidence-backed value function.

## Reuse decision record

Record:

- candidate, granule, workload, decision horizon, and target metric;
- complete identity field list and deliberate exclusions;
- validity predicate, dependencies, epochs, and authorities;
- invalidation events and validation-to-use ordering requirement;
- owner, isolation scope, readers, writers, and sharing contract;
- copy-on-write requirement and delegated physical semantics;
- full or partial coverage contract;
- baseline work and exactly what reuse avoids;
- every benefit and cost term with source and uncertainty;
- logical budget, footprint, interference, and alternatives;
- formula, result, sensitivity, and rejected defaults;
- admission, retention, invalidation, or logical-eviction decision;
- fallback, handoffs, falsifier, and rollback condition.

## Acceptance gate

Keep a reuse or logical-eviction policy only when:

- identity is complete and collision-safe under the accepted contract;
- validity is mechanically checkable;
- mutation epochs have an authoritative source;
- validation-to-use ordering is guaranteed or explicitly handed off;
- ownership and isolation permit the proposed sharing;
- writable sharing has a safe copy-on-write contract;
- partial reuse preserves correctness and has positive marginal value;
- every material cost and the no-reuse alternative are included;
- the decision remains positive under conservative uncertainty;
- no default eviction rule substitutes for workload evidence;
- logical eviction makes no unsupported physical-residency claim;
- end-to-end validation shows no unacceptable correctness, isolation, footprint, latency, or throughput regression.
