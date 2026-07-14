---
name: gpu-code-optimizer
description: Load this skill and follow it when planning, reviewing, or carrying out performance optimization for GPU compute, resource, or runtime-state workloads, especially when deciding which specialized optimization skills to load.
---

# GPU Code Optimizer

Use this as the routing and orchestration skill for GPU performance work. Preserve correctness first, remove avoidable data movement second, and optimize the measured bottleneck third. The scope includes CUDA, HIP, SYCL, OpenCL, Metal compute, Vulkan compute, Triton, MLIR-derived kernels, framework-generated kernels, tensor programs, numerical simulations, image/video compute, graph workloads, GPU resource and runtime-state management, and GPU-like accelerators.

Treat graphics rendering pipelines as a non-goal. Do not provide rasterization, shader-stage, ray-tracing, visibility, blending, frame-presentation, or visual-quality guidance. General allocation, residency, migration, state, scheduling, and compute-kernel problems remain in scope when they can be isolated from rendering-specific semantics.

Do not assume a vendor, language, framework, or bottleneck. The same source code may be launch-bound on one workload, bandwidth-bound on another, and compute-bound after fusion. Route the task to the smallest set of specialist skills that can resolve the current bottleneck.

## Scope of skill names

The skill names used throughout this suite — `gpu-code-optimizer`, `gpu-performance-evidence`, `gpu-numerical-safety`, `gpu-memory-fusion-layout`, `gpu-resource-lifetime-allocation`, `gpu-virtual-memory-fragmentation`, `gpu-memory-tiering-migration`, `gpu-state-reuse-eviction`, `gpu-persistent-state`, `gpu-memory-scheduling`, `gpu-kernel-execution`, `gpu-compiler-runtime`, `gpu-reductions-scans`, `gpu-training-autodiff`, `gpu-optimization-validation` — are conversational routing terms for this skill suite. They may be spoken to the user or to a parent agent, and may appear in pull request descriptions, issue bodies, and decision records attached to a task.

These skill names **must not** be written into the codebase under optimization. Do not put them into source comments, docstrings, identifiers, variable names, enum values, configuration keys, commit messages, branch names, tags, file names, or generated code. The optimized project has no knowledge of this skill suite; references to it in the codebase would leak an external tooling assumption into the project's own source.

## Scope of role terms

The role terms `parent`/`orchestrator` (for `gpu-code-optimizer`) and `specialist` (for the other fourteen skills) are internal to this skill suite. They describe how the skills route work to each other, not how the codebase under optimization is structured.

These role terms **must not** be written into the codebase under optimization. Do not name identifiers, types, functions, configuration keys, files, or directories `orchestrator`, `specialist`, `parent_agent`, or any close equivalent just because this skill suite uses those words. When the codebase itself needs a similar concept, use a name that matches the project's own domain vocabulary.

## Specialist map

- [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md) — baseline, profiler evidence, roofline reasoning, bottleneck classification, kernel/allocation audits.
- [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) — semantic risk classes, floating-point changes, guard conditions, tolerances, NaN/Inf and boundary behavior.
- [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md) — intermediate materialization, fusion, layout, locality, global-memory traffic.
- [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md) — logical liveness, peak overlap, transient aliasing, pooling, workspace, materialization, rematerialization.
- [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md) — allocatability, fragmentation, logical/physical contiguity, page granularity, VMM, indirection, stitching, compaction.
- [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md) — placement, residency, prefetch, offload, replication, migration, topology, oversubscription.
- [gpu-state-reuse-eviction](../gpu-state-reuse-eviction/SKILL.md) — state identity, validity, sharing, admission, retention, invalidation, logical eviction.
- [gpu-persistent-state](../gpu-persistent-state/SKILL.md) — cross-call state growth, mutation, ownership, snapshots, branches, rollback, checkpoints, cleanup.
- [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md) — joint timing of compute, allocation, mapping, movement, rematerialization, barriers, and reclamation.
- [gpu-kernel-execution](../gpu-kernel-execution/SKILL.md) — thread/workgroup mapping, tiling, matrix units, registers, shared memory, occupancy, synchronization, atomics.
- [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) — torch.compile/Inductor, JAX/XLA, Triton compilation, graph breaks, launch overhead, graphs, transfers, multi-GPU runtime.
- [gpu-reductions-scans](../gpu-reductions-scans/SKILL.md) — reductions, scans, prefix operations, recurrence, streaming state, chunk boundaries.
- [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md) — backward pass, saved tensors, recomputation, gradient reductions, training-step memory and timing.
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — representative benchmarks, acceptance gates, decision records, failure cases, final review format.

## Routing rule

Start with `gpu-performance-evidence` unless the task is purely a correctness review. A performance change without a baseline is a hypothesis, not an optimization.

Always add `gpu-numerical-safety` when a proposal can change floating-point evaluation order, precision, reduction tree, mask ordering, boundary semantics, synchronization semantics, determinism, aliasing, NaN/Inf propagation, or value-domain assumptions.

Add `gpu-memory-fusion-layout` when one pipeline shows avoidable temporaries, repeated layout conversions, producer→consumer write/read pairs, elementwise chains, redundant loads, or memory-bandwidth saturation. Keep local materialization and fusion here; route cross-graph lifetime planning separately.

Add `gpu-resource-lifetime-allocation` when peak memory depends on live-range overlap, transient aliasing, pools, dynamic workspace, delayed release, or a retain-versus-rematerialize decision.

Add `gpu-virtual-memory-fragmentation` when capacity and allocatability differ, a large allocation fails despite aggregate free bytes, or the decision concerns page/block granularity, virtual contiguity, software indirection, VMM, stitching, or compaction.

Add `gpu-memory-tiering-migration` when resources may reside across device, peer, host, storage, or remote tiers, or when oversubscription, prefetch, offload, replication, migration, and thrashing determine performance. Treat the logical retention decision as an input: if the unresolved question is whether valuable state should remain in the logical cache or be deleted, route first to `gpu-state-reuse-eviction` and use tiering only for the retained state's physical residency.

Add `gpu-state-reuse-eviction` when retained runtime state needs identity, validity, mutation epochs, ownership, sharing, copy-on-write, admission, retention, invalidation, or logical eviction policy. Make this the primary skill when choosing logical deletion versus lower-tier demotion: decide whether the state remains valuable and valid first, then hand physical placement and movement to `gpu-memory-tiering-migration`.

Add `gpu-persistent-state` when state survives independent kernels, steps, requests, or sessions and its growth, mutation, snapshots, branches, rollback, checkpoints, ownership, or cleanup semantics must be defined. Keep single-algorithm chunk state in `gpu-reductions-scans`.

Add `gpu-memory-scheduling` when compute, allocation, mapping, transfers, rematerialization, barriers, and reclamation must be jointly ordered around a critical path. Keep concrete graph capture, stream, queue, and runtime mechanisms in `gpu-compiler-runtime`.

Add `gpu-kernel-execution` only after the hot kernel is known. Use it for coalescing, tiling, shared-memory reuse, register pressure, matrix-unit utilization, divergence, synchronization, atomics, or architecture-specific pipelines.

Add `gpu-compiler-runtime` when the code is generated or captured by a framework/compiler, or when the timeline shows gaps, graph breaks, recompilations, allocation churn, host-device transfers, graph replay issues, or communication stalls.

Add `gpu-reductions-scans` for any associative reduction, prefix operation, scan, recurrence, running statistic, online normalization, or chunked state update. These algorithms have distinct boundary and numerical hazards.

Add `gpu-training-autodiff` whenever gradients are required. A forward-only speedup is insufficient evidence for a training path.

Finish production-facing changes with `gpu-optimization-validation`.

## Resource and state preflight

Run these six questions when memory capacity, allocation, movement, reuse, or cross-call state is material. Do not activate every specialist when the answers are trivial.

1. **Lifetime**: When must each logical object exist, and which completion event proves its last use?
2. **Backing**: Does it require physical contiguity, virtual contiguity, or segmented access, and what is the largest allocatable extent?
3. **Residency**: Where may and must it be accessible now and next, and what authorized movement can meet the deadline within the transfer budget?
4. **Identity**: Which fields prove reusable state is semantically equal, valid, and authorized?
5. **Mutation**: How does cross-call state grow, update, version, branch, reconstruct, and become unreachable?
6. **Schedule**: Which compute and memory actions are ready, critical, overlap-safe, capacity-safe, and progress-safe?

Answer unknown questions with a measurement or a specialist handoff. Do not fill them with default paging, offload, recency eviction, reuse, or overlap assumptions.

## Mandatory sequence

1. Establish a known-correct reference and the accepted semantic/numerical contract.
2. Record the target hardware, software stack, shapes, dtypes, layouts, modes, and target metric.
3. Measure the current end-to-end path and identify the dominant cost.
4. Run the resource and state preflight when its trigger is present.
5. Select one bottleneck hypothesis and one smallest useful change.
6. Estimate what work, traffic, capacity pressure, or exposed stall the change removes and what cost it adds.
7. Classify semantic risk and define guards/fallbacks before promoting a fast path.
8. Implement or propose the change.
9. Verify that the compiler/runtime actually produced the intended lowering or mechanism.
10. Re-run correctness, isolated benchmarks, and end-to-end benchmarks.
11. Re-classify the bottleneck. Keep the change only if it improves the user's actual target metric.

## Quick execution checklist

Before the detailed analysis below, use this short checklist to stay on track:

1. Confirm correctness baseline and tolerance.
2. Record target GPU, framework, dtype, shape, layout.
3. Record current runtime, kernel count, memory peak.
4. Find the largest intermediate tensor.
5. Find the largest lifetime overlap and failed or expensive memory action when relevant.
6. Find the most frequent kernel/operator boundary.
7. Find the dominant anchor operation.
8. Prioritize removing full-buffer write/read pairs or exposed memory stalls.
9. Fuse cheap transforms into producer epilogue or consumer prologue when local fusion is the right layer.
10. Label every non-trivial rewrite with its **optimization class** (see gpu-numerical-safety).
11. Every fast path or resource policy must have **guard conditions** and a **documented fallback**.
12. Confirm the optimization actually happened via profiler, compiler IR, allocation trace, or runtime trace.
13. Benchmark isolated path **and** end-to-end path.
14. Keep only changes that improve the user's real target metric.

---

## Proportionality rule

For quick code reviews, small snippets, or early design feedback, apply the mandatory checks conceptually and report only material findings. For production patches, benchmark claims, numerical rewrites, or user-requested optimization reports, include the full guard conditions, error statistics, kernel-count audit, allocation audit, failure cases, and decision record.

---

## Primary objective

Minimize avoidable GPU work that does not contribute directly to the final result.

Prioritize these reductions:

1. Global memory reads and writes.
2. Intermediate tensor or buffer materialization.
3. Kernel launches and graph/operator boundaries.
4. Layout conversions, packing, unpacking, transposes, gathers, and scatters.
5. Redundant computation.
6. Synchronization, atomics, and serialization.
7. Host-device transfers and device-device copies.
8. Register spills, shared/local memory pressure, and occupancy loss.

The best optimization is usually not a faster instruction. It is removing a memory round trip, a temporary buffer, a launch boundary, or a synchronization point.

---

## Non-negotiable constraints

Preserve program semantics unless the user explicitly accepts a change.

Do not silently change:

- Floating-point precision.
- Accumulation order beyond accepted tolerance.
- Boundary behavior (especially inclusive/exclusive semantics for scan, mask, prefix, and window operations).
- NaN, Inf, denormal, overflow, underflow, signed-zero, saturation, or rounding behavior.
- Determinism.
- Atomic ordering.
- Memory visibility.
- Synchronization requirements.
- Tensor layout contracts.
- Aliasing behavior.
- In-place update semantics.

Treat performance claims as hypotheses until measured. Do not use tolerance relaxation to mask bugs (see gpu-numerical-safety).

---

## Optimization priority ladder

Use this order as a default, then override it when measurements disagree:

1. Remove unnecessary full-buffer materialization and transfers.
2. Reduce peak live overlap, unsafe over-retention, and avoidable rematerialization or movement.
3. Repair allocatability, residency, and scheduling stalls when evidence shows they are limiting.
4. Remove avoidable launch/operator boundaries around cheap work.
5. Fuse cheap transforms into a producer epilogue or consumer prologue when resource cost remains acceptable.
6. Replace full intermediates with compact partials or algorithm-local streaming state.
7. Stabilize pipeline layout and improve coalescing/locality.
8. Reduce runtime dispatch, allocation, transfer, and graph-break overhead.
9. Improve matrix/tensor/vector unit utilization where the kernel is compute-bound or underutilized.
10. Reduce synchronization, atomics, and communication serialization.
11. Tune tile sizes, workgroup mapping, registers, shared memory, and occupancy.
12. Specialize common shapes only with explicit guards and a correct fallback.

This ladder is not a law. A 3 µs launch-bound kernel and a 3 ms bandwidth-bound kernel require different actions. A profiler can move any item to the top.

## Architecture neutrality

Use architecture-specific mechanisms only after identifying the target device and validating their prerequisites. Examples include asynchronous global→shared copies, tensor-memory engines, matrix instructions, warp/wave/subgroup collectives, distributed shared memory, or vendor graph runtimes. Treat these as optional implementations of general patterns, not universal assumptions.

Do not equate source-level constructs with hardware execution. A matmul-shaped expression does not prove matrix-unit use. A fused graph does not prove one kernel. A shared-memory tile does not prove better locality. A higher occupancy percentage does not prove higher throughput. Verify each claim with profiler data, compiler IR, generated code, or hardware counters.

## Working with incomplete evidence

Do not block useful work merely because a full profiler trace is unavailable. Separate what is known from what is inferred.

When evidence is incomplete:

- state the current bottleneck hypothesis;
- identify the code or dataflow facts that support it;
- avoid numerical speedup claims;
- propose the smallest measurement that could confirm or reject it;
- keep recommendations reversible and preserve the reference path.

Static inspection can still find obvious waste: a full-size tensor that is written once and immediately consumed, an unconditional host synchronization inside a loop, a repeated transpose pair, or a clearly redundant copy. Treat these as strong optimization candidates, but still measure before claiming performance impact.

Use estimates to rank experiments. For example, removing a `N`-element temporary with one producer store and one consumer load saves roughly `2*N*element_size` logical bytes. Amdahl-style reasoning can bound the maximum end-to-end benefit of accelerating a phase. These calculations guide effort; they do not replace measurement.

## Stop conditions

Stop optimizing the current path when one of these is true:

- the target metric is met;
- the remaining hot path is already near an appropriate hardware or algorithmic ceiling;
- expected gain is smaller than measurement noise or engineering/maintenance cost;
- the next optimization requires an unacceptable semantic compromise;
- the bottleneck moved outside the scope of the code under review;
- a mature library/compiler path already matches or exceeds the custom alternative.

Do not keep tuning because a lower-level knob exists. The objective is the user's target metric, not maximum complexity.

## Implementation workflow

1. Verify correctness baseline.
2. Measure performance baseline (kernel count, memory peak, runtime, allocation count).
3. Identify the dominant bottleneck.
4. Audit memory traffic and intermediate materialization (intermediate-tensor table, the intermediate-tensor audit in gpu-memory-fusion-layout).
5. Run the six-question resource and state preflight when triggered.
6. Select the anchor operation or dominant resource-state decision.
7. Find producer-epilogue, consumer-prologue, lifetime, backing, residency, reuse, state, or scheduling candidates at the measured layer.
8. Find tile-local partial-reduction and layout-conversion candidates when applicable.
9. Estimate saved bytes, reduced peak, avoided movement or stalls, and added work.
10. Estimate added registers, local memory, metadata, staging, synchronization, contention, and branch cost.
11. Implement the smallest useful change.
12. **Classify the optimization** (C1–C4; see gpu-numerical-safety).
13. **Add guard conditions** and document the fallback.
14. Run correctness tests (forward + backward if applicable).
15. Report error statistics (see gpu-numerical-safety).
16. Benchmark (isolated + end-to-end).
17. Re-classify the bottleneck using gpu-performance-evidence.
18. Keep the change only if it improves the user's target metric.
19. Record the decision (see gpu-optimization-validation).
20. Repeat on the next bottleneck.

---

## Default optimization priorities

Use this ranking unless measurements show otherwise:

1. Remove full-buffer intermediate materialization (see gpu-memory-fusion-layout).
2. Reduce peak live overlap or reconstructable retention when capacity is limiting (see gpu-resource-lifetime-allocation).
3. Fuse cheap work into producer epilogues or consumer prologues (see gpu-memory-fusion-layout).
4. Replace full intermediates with compact tile partials or algorithm-local streaming state (see gpu-reductions-scans).
5. Remove redundant layout conversions (see gpu-memory-fusion-layout).
6. Improve memory coalescing and locality (see gpu-memory-fusion-layout).
7. Repair measured allocatability, migration, reuse, or scheduling stalls with the matching specialist.
8. Reduce launch count and runtime overhead (gpu-performance-evidence, gpu-compiler-runtime).
9. Improve tensor/matrix/vector unit utilization (see gpu-kernel-execution).
10. Reduce synchronization and atomics (see gpu-kernel-execution).
11. Tune tile size, occupancy, registers, and shared/local memory (see gpu-kernel-execution).
12. Specialize for common shapes with safe fallbacks (see gpu-numerical-safety).

---

## Completion gate

Before presenting a production optimization, route through [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md). For C2+ numerical changes, also route through [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md). For training, route through [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md). For resource or runtime-state policies, include only the applicable lifetime, backing, residency, reuse, state-contract, and scheduling acceptance fields.

## Final check

Before presenting the result, verify:

- The change addresses the user's actual performance target.
- The optimization class is stated.
- Guard conditions and fallback are documented.
- Correctness is verified (forward + backward if training).
- Error statistics are reported (for C2+).
- Both isolated and end-to-end benchmarks support the improvement.
- Framework-specific assumptions are stated, not hidden.
- Resource and state claims distinguish logical lifetime, physical backing, residency, logical reuse, mutation semantics, and scheduling when applicable.
- Failure cases and remaining bottlenecks are listed.
- A measurement plan is included so the claim can be independently verified.
