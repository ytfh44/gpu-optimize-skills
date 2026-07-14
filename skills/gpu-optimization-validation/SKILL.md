---
name: gpu-optimization-validation
description: Load this skill and follow it when turning GPU optimizations into reviewable patches, designing guards and fallbacks, running representative benchmarks, recording failure cases, or performing final validation.
---

# GPU Optimization Validation

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md) — load for baseline methodology and bottleneck evidence
- [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) — load for C2+ error reports and semantic acceptance
- [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md) — load when the path is used for training
- [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md) — return to orchestration when validation reveals a new bottleneck

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Treat every optimization as an experiment with an explicit hypothesis, guard domain, fallback, and acceptance criterion. The final artifact must let another engineer reproduce the claim and know when not to use the fast path.

## Representative benchmark matrix

Benchmark at least:

- small, target, and maximum sizes;
- non-power-of-two and non-divisible dimensions;
- common and worst-case layouts/strides;
- supported dtypes and precision modes;
- relevant batch/sequence/channel/head dimensions;
- real input distributions plus extreme/pathological values;
- cold and warm states where compilation/autotuning/caching matters;
- training and inference modes if both are supported;
- multiple target devices if portability is claimed.

Do not optimize only a hand-picked benchmark shape and generalize the claim to all inputs.

## Timing protocol

Use an appropriate device-side timer, framework benchmark utility, or synchronized timing method. Account for asynchronous execution. Warm up compilation, caches, allocators, and autotuners as appropriate before steady-state timing.

Report:

- sample count;
- median and a tail statistic such as p95 where latency matters;
- variance or confidence interval when noise is material;
- synchronization method;
- whether compilation/capture/autotuning is included;
- exact workload scope.

For very short kernels, measurement overhead can dominate. Prefer batched repetitions or profiler kernel timing while preserving realistic launch behavior.

## Correctness protocol

Start from a known-good reference. For exact semantic paths, compare all relevant outputs and boundary conditions. For C2+ changes, use the error-reporting contract in [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md).

Do not weaken existing tests merely to make the optimization pass. A tolerance change requires a documented numerical rationale and approval consistent with the semantic class.

## Mode-specific recommendation

Many operators have multiple execution modes with different bottlenecks:

- Training forward / backward.
- Inference batch / single request.
- Online streaming / offline.
- Prefill / decode (autoregressive).
- Long-context / short-context.
- Low-latency / high-throughput.
- Memory-constrained.
- Multi-GPU.
- CPU fallback.
- Small batch / large batch.

The best path for one mode may be the worst for another. Report which mode(s) the optimization targets, and document which modes should use the fallback.

---

## Decision record

Every optimization patch should include a short decision record:

```text
Decision:
- Problem: <what was slow / memory-heavy>
- Bottleneck: <classified bottleneck>
- Change: <concrete description>
- Optimization class: C1 / C2 / C3 / C4
- Why safe: <numerical / semantic justification>
- Guard: <conditions enabling fast path>
- Fallback: <path taken when guard fails>
- Evidence: <profiler trace / IR / benchmark that confirms>
- Result: <before → after, with metric>
- Rejected alternatives: <what else was considered and why dismissed>
- Remaining risk: <open numerical / performance concerns>
```

---

## Failure-case record

Optimization reports must include failure cases:

- Which shapes are **not** improved (or regress)?
- Which dtypes are not supported?
- Which layouts are not supported?
- Which input value ranges cause numerical issues?
- Which devices / architectures are not supported?
- Which precision modes break the fast path?
- Which batch sizes show no improvement?
- At what scale does the fallback become preferable?
- When is error too large?
- When does memory increase?
- When does compile time increase?
- When does end-to-end regress?

Failure cases define the guard conditions. Without them, the fast path will be misused.

---

## Patch strategy

When editing code:

- Make one optimization at a time when possible.
- Preserve the original path as a fallback.
- Add shape, dtype, alignment, and layout guards.
- Keep boundary handling explicit.
- Keep synchronization explicit.
- Avoid hidden global state.
- Avoid undocumented assumptions.
- Prefer readable optimized code over fragile cleverness unless the hot path demands it.
- Include comments only for non-obvious performance or correctness constraints.

---

## Review output contract

1. **Bottleneck hypothesis**: Classified bottleneck with evidence source.
2. **Evidence**: Code, profiler output, IR, byte/FLOP reasoning, or hardware counter.
3. **Optimization class**: C1 / C2 / C3 / C4 per proposed change.
4. **Numerical behavior changed?**: Yes / No, with justification.
5. **Optimization plan**: Ranked by impact, each with guard conditions.
6. **Concrete patch or pseudocode**.
7. **Guard conditions**: When is the fast path safe?
8. **Fallback path**: What runs when guard conditions are not met.
9. **Bytes saved estimate**: Intermediate tensor delta.
10. **Kernel count before / after**.
11. **Peak memory before / after**.
12. **Allocation count before / after**.
13. **Expected speedup**: Isolated + end-to-end estimate.
14. **Correctness risks**: Numerical behavior, boundary semantics, backward impact.
15. **Error statistics**: Per the error-reporting contract in gpu-numerical-safety (for C2+).
16. **Unsupported cases**: Shapes, dtypes, layouts, value ranges where fallback is required.
17. **End-to-end impact**: Full step / request / iteration time delta.
18. **Decision**: Keep / reject / behind flag, with rationale.
19. **Next bottleneck**: What to optimize after this change.
20. **Benchmark plan**: Isolated + end-to-end, shapes to test.

### Answer format when generating optimized GPU code

1. **Optimized code or pseudocode**.
2. **Optimization class** (C1–C4).
3. **Assumptions** (hardware, framework, shapes, dtypes, value range).
4. **Guard conditions**.
5. **Fallback path**.
6. **Correctness test** (forward + backward).
7. **Error statistics** (see gpu-numerical-safety).
8. **Benchmark harness or measurement instructions**.
9. **Allocation + kernel-count delta**.
10. **Remaining bottlenecks**.
11. **Failure cases** (when to use fallback).

---

Use proportionality: a quick review need not emit twenty empty sections. A production optimization claim, benchmark report, or merged fast path should include all material fields.

## Red flags

Re-evaluate when:

- Fusion introduces register spills.
- Fusion reduces useful occupancy too much.
- Added branch divergence cancels saved memory traffic.
- Added random access cancels saved memory traffic.
- A local layout change slows the next major operation.
- A microbenchmark excludes conversion, allocation, synchronization, or auxiliary reduction cost.
- A kernel benchmark improves but end-to-end runtime regresses.
- A tuned library primitive is replaced without proving composition overhead.
- Boundary cases are slower or incorrect.
- Numerical tolerances change without approval.
- Determinism changes without approval.
- The profiler does not support the bottleneck hypothesis.
- The optimization only helps shapes that are not representative.
- The error grows with sequence length or batch size (systematic bias, not random noise).
- The fast path silently produces incorrect results on edge cases (all-zero, all-one, empty, singleton, padded).
- A matmul/conv is claimed to use Tensor Cores without profiler or IR evidence.
- Shared memory is used without evidence of improved reuse, coalescing, or scheduling.

---

## Acceptance matrix

A change may be marked:

- **Keep as default** — correctness contract passes; representative end-to-end target improves; failure domain is acceptable.
- **Keep behind guard/flag** — useful fast path with narrower hardware/shape/numerical domain.
- **Keep as local micro-optimization only** — isolated kernel improves but end-to-end result is neutral; do not claim application speedup.
- **Reject** — correctness risk, end-to-end regression, excessive memory/compile cost, or unsupported bottleneck hypothesis.
- **Need more evidence** — measurement cannot yet distinguish the hypothesis from noise or confounding factors.

## Benchmark confounders

Common confounders include:

- JIT compilation or autotuning leaking into timed iterations;
- GPU clock/power state changes between runs;
- thermal throttling;
- background GPU work;
- different allocator/cache warmness;
- host scheduling noise for microsecond kernels;
- different synchronization scope;
- different data transfer inclusion;
- random inputs that trigger different sparsity or branch behavior.

Control what is practical and disclose what is not. For close results, repeat interleaved A/B runs rather than running all of A and then all of B.

## A/B comparison design

Prefer identical environments and inputs. Randomize or interleave run order when drift is possible. Compare the same metric scope and report both absolute and relative changes.

For an end-to-end path, decompose enough to explain the result:

- target phase before/after;
- new overhead introduced elsewhere;
- kernel/launch count changes;
- memory/copy changes;
- compile/capture cost changes.

A surprising result is a reason to inspect the timeline, not to discard the benchmark.

## Portability claims

Do not claim a GPU optimization is portable merely because it compiles on multiple backends. Distinguish:

- semantic portability;
- functional backend support;
- performance portability;
- architecture-specific fast paths.

For each claimed target, report the tested device family, software stack, supported shapes/dtypes/layouts, and fallback. A portable reference path plus architecture-specific guarded fast paths is often the cleanest design.

## Reproducibility bundle

For production work, preserve enough information to reproduce the result:

- commit or code version;
- device model and relevant topology;
- driver/runtime/compiler/framework versions;
- benchmark command/configuration;
- shapes, dtypes, layouts, seeds;
- environment variables that affect compilation or math modes;
- profiler trace or summary when it supports a key claim.

Do not overload the user-facing summary with all raw data; keep the evidence available and present the decisive facts.

## Regression checks

After the change, re-run:

- kernel/operator count;
- peak memory and allocations;
- copies and synchronization;
- compile/capture/autotune cost;
- key hardware counters for the new bottleneck;
- full application/request/iteration timing.

The bottleneck may move. Do not continue optimizing the old bottleneck without reclassification.

## Final sign-off

Before presenting the result, verify:

- target metric is explicit;
- baseline and measurement scope are reproducible;
- optimization class is stated;
- guard conditions and fallback are documented;
- correctness and boundary tests pass;
- C2+ error statistics are complete;
- isolated and end-to-end results are both reported where relevant;
- unsupported devices/shapes/layouts/value ranges are listed;
- compiler/runtime evidence confirms the intended transformation;
- the decision is Keep / Guarded / Micro-only / Reject / Need more evidence.
