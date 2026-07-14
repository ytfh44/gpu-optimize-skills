---
name: gpu-virtual-memory-fragmentation
description: Load this skill and follow it when diagnosing GPU memory allocatability failures, internal or external fragmentation, virtual-to-physical mapping, sparse or page-backed resources, virtual contiguity, compaction, stitching, or page-granularity tradeoffs.
---

# GPU Virtual Memory and Fragmentation

## Skill navigation

- Parent router: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- Evidence: [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md)
- Logical lifetime: [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md)
- Placement: [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md)
- Access-path execution: [gpu-kernel-execution](../gpu-kernel-execution/SKILL.md)
- Runtime mechanisms: [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md)
- Validation: [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md)

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Decide how already-required logical resources obtain addresses and physical backing. Separate virtual reservation, backing commitment, current residency, and allocatable extents before diagnosing a failure or selecting a mechanism.

Total free bytes do not prove that a request is allocatable. Measure the request's size, alignment, contiguity, permission, pool, and granularity constraints against the actual shape of eligible free space.

Treat logical retention and target tier as inputs. This skill may audit residency because it affects feasibility, but it does not decide whether a resource should exist or where it should live.

## Backing model and audit

Use exact API and allocator definitions. Do not assume all systems account for these quantities in the same way.

- **Reserved**: virtual address space held for a logical range without necessarily supplying backing.
- **Committed**: backing obligation or capacity charge under the active API contract.
- **Resident**: backing currently present and accessible at the execution location.
- **Requested**: payload bytes requested by the logical resource.
- **Charged**: bytes consumed after rounding, metadata, and mechanism-specific granularity.
- **Eligible free**: free backing that satisfies the request's pool, permission, alignment, and placement constraints now.
- **Largest allocatable extent**: largest request that a specific mechanism can satisfy in the captured state.

Never report unqualified `free memory`. Separate free virtual space, allocator-free backing, commitment headroom, cached bytes, reclaimable bytes, and immediately eligible bytes.

Do not assume `resident <= committed <= reserved`. Sparse mappings, aliases, overcommit, and different accounting domains can break that ordering.

### Required backing audit

| Field | Record |
|---|---|
| Scope | Device, context, allocator, pool or heap, API/runtime version, timestamp |
| Request | Bytes, alignment, permissions, address stability, contiguity contract, concurrency state |
| Isolation | Owner and trust domain, old-mapping revocation, residual-content overwrite or sanitization contract |
| Capacity | Reserved, committed, resident, requested, charged, cached, reclaimable, eligible-free bytes |
| Extents | Physical and virtual extent counts, distributions, and largest aligned extents |
| Granularity | Allocation block, mapping page, commitment, alignment, relocation, and compaction units |
| Capability | Page sizes, mapping limits, remapping, faulting, relocation, segment-count limits |
| Cost | Reserve, commit, map, unmap, fault, translation, indirection, synchronization, compaction |
| Evidence | API query, allocator trace, profiler, counter, probe, or documented constraint |

Capture all quantities from one reproducible state. Ratios from different timestamps, pools, or accounting domains are not a valid fragmentation diagnosis.

### Classify fragmentation

Define internal fragmentation as charged bytes that do not hold requested payload:

```text
internal_bytes = sum_i(charged_i - requested_i)
internal_ratio = internal_bytes / sum_i(charged_i)
```

Use the ratio only when the denominator is positive and charges are comparable.

Define external fragmentation relative to one eligibility domain. For eligible extents `e_i`:

```text
F = sum_i usable(e_i)
L = max_i usable(e_i)
external_ratio = 1 - L / F
```

Treat this ratio as a diagnostic, not an allocation guarantee. Alignment, page count, permissions, address-space limits, and per-allocation limits still apply.

Measure physical and virtual extent domains separately.

### Establish the contiguity contract

Classify the consumer contract before choosing a mechanism:

- **Physical contiguity required**: one physical extent must satisfy the request.
- **Virtual contiguity required**: one contiguous virtual range may map multiple physical extents.
- **Segmented access permitted**: consumers can follow software metadata across extents.

Do not preserve a contiguity requirement merely because the current implementation happens to use one pointer. Do not remove it without checking every consumer and external interface.

## Decision workflow

1. Declare the target metric, workload scope, and non-negotiable address constraints.
2. Reproduce the failure or pressure in a controlled allocator state.
3. Capture the required audit fields from the same snapshot.
4. Establish the physical, virtual, or segmented contiguity contract.
5. Classify the cause as true capacity exhaustion, commitment limit, virtual-space fragmentation, physical external fragmentation, internal fragmentation, or another constraint.
6. Measure or bound the largest allocatable extent for every feasible mechanism.
7. Compare direct backing, changed granularity, virtual stitching, software indirection, and compaction only when prerequisites hold.
8. Include setup, steady-state, tail, metadata, translation, and synchronization costs.
9. Select against declared objectives; return Pareto alternatives when priorities are missing.
10. Re-run the failing request, representative workload, and end-to-end benchmark.

### Compare backing mechanisms

| Mechanism | Backing effect | Address effect | Principal costs |
|---|---|---|---|
| Direct extent | Uses one eligible physical extent | Usually exposes one range | Extent availability, alignment, rounding |
| Virtual stitching | Maps separate physical extents | Exposes one virtual range | Reservation, mapping, synchronization, faults, translation |
| Software indirection | Retains separate extents | Exposes segmented logical access | Lookup, metadata, kernel or access-path changes |
| Compaction | Relocates backing to enlarge extents | May preserve or update addresses | Copies, stalls, temporary headroom, pointer safety |
| Smaller granularity | Improves fit and reduces rounding | Increases mapping count | Metadata, faults, translation pressure |
| Larger granularity | Reduces mapping count | Coarsens allocation and residency | Internal waste, harder extent availability |

No row is a default. Select a mechanism only after confirming capability, compatibility, and measured break-even behavior.

### Bound allocatability

For mechanism `m`, define:

```text
L_alloc(m) = sup { S | feasible(m, S, captured_state) }
```

Check the mechanism-specific constraints:

- Direct backing requires a charged request that fits one eligible physical extent and an eligible address range.
- Virtual stitching requires enough individually allocatable backing units, a virtual reservation, and supported mapping counts.
- Software indirection requires an acceptable segment count and compatible consumers.
- Compaction requires safe relocation, temporary headroom, and a predicted post-compaction extent.

Verify the bound with reproducible allocation probes where safe. A successful small probe does not prove the maximum, and a failed probe does not by itself prove fragmentation.

## Cost model

Record memory overhead:

```text
memory_overhead = rounding_slack
                + mapping_or_segment_tables
                + allocator_metadata
                + temporary_compaction_bytes
```

Record amortized runtime cost:

```text
T_amortized = setup_and_periodic_cost / observed_reuse
            + T_fault
            + delta_T_translation
            + delta_T_indirection
            + delta_T_allocator
```

Report cold setup, steady state, and tail behavior separately. Do not assume mapping cost scales linearly with page count or that a larger page improves translation without counter evidence.

Choose only feasible mechanisms:

```text
m* in argmin J_target(m)
subject to allocation, correctness, concurrency, and budget constraints
```

Do not invent objective weights. Label model-only results as hypotheses and state the allocation probe or end-to-end measurement that would falsify them.

## Specialist handoffs

| Question | Handoff |
|---|---|
| Should the logical resource be retained, released, aliased, or reconstructed? | `gpu-resource-lifetime-allocation` |
| Which tier should supply the backing and when should residency change? | `gpu-memory-tiering-migration` |
| Does segmented access or indirection change the measured hot kernel? | `gpu-kernel-execution` |
| Which API, allocator, capture, or synchronization mechanism implements the policy? | `gpu-compiler-runtime` |
| Which evidence distinguishes capacity, fragmentation, and runtime overhead? | `gpu-performance-evidence` |
| Does the selected mechanism improve the real target safely? | `gpu-optimization-validation` |

Pass exact request constraints, same-snapshot measurements, capability limits, candidate costs, and unresolved assumptions. Do not pass a conclusion that exceeds the evidence.

## Failure modes and counterexamples

- Aggregate free bytes conceal an insufficient largest extent.
- Allocation failure alone is called fragmentation.
- Cached or reclaimable bytes are treated as immediately eligible.
- Virtual contiguity is confused with physical contiguity.
- Virtual stitching is claimed to create a larger physical extent.
- A virtual-memory mechanism is claimed to eliminate internal fragmentation or mapping limits.
- Software indirection changes the access contract or regresses the hot path.
- Compaction violates pointer stability, synchronization, or temporary-headroom limits.
- Remapping or recycling leaves an old mapping valid or exposes residual contents across isolation domains.
- Smaller pages are assumed to be better despite metadata and translation costs.
- Larger pages are assumed to be better despite rounding and extent costs.
- Different pools, permissions, or snapshots are combined into one ratio.
- Setup-only timing hides faults, translation tails, or remapping stalls.
- A backing choice silently changes logical retention or tier placement.
- A conventional allocator policy replaces a measured workload comparison.

Reject a mechanism when its prerequisites, relocation safety, segment compatibility, or tail cost cannot be established. Keep it as a hypothesis when a targeted probe can resolve the uncertainty.

## Decision record

Record:

- target metric and workload scope;
- environment, allocator, pool, and capability matrix;
- exact meanings of reserved, committed, resident, and every free quantity;
- request size, alignment, permissions, and contiguity contract;
- owner, isolation domain, old-mapping revocation, overwrite, and sanitization requirements;
- same-snapshot extent and granularity data;
- internal and external fragmentation calculations;
- measured or bounded `L_alloc` for each candidate;
- setup, steady-state, tail, metadata, and temporary costs;
- selected mechanism and evidence-backed rejected alternatives;
- logical-policy and placement inputs held fixed;
- assumptions, uncertainty, falsifying measurements, and fallback;
- validation result and calibrated claim.

## Acceptance gate

Keep a backing or fragmentation change only when:

- all memory quantities have explicit definitions and one evidence scope;
- the failure is classified without confusing capacity and allocatability;
- physical, virtual, and segmented contiguity requirements are proven;
- the target request fits a measured or defensibly bounded allocatable extent;
- page or block granularity has an evidence-backed choice;
- mapping, fault, translation, indirection, synchronization, and compaction costs are included when applicable;
- remapping or recycling revokes old access and prevents residual-content exposure across isolation domains;
- logical retention and target tier remain unchanged unless their specialists approve a change;
- the failing allocation succeeds across representative states;
- correctness, concurrency, and address-stability contracts pass;
- end-to-end metrics improve or the required capacity target is met within accepted cost;
- missing evidence leaves a hypothesis, not an overconfident recommendation.
