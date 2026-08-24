---
name: gpu-performance-evidence
description: Load this skill and follow it when establishing a GPU performance baseline, analyzing profiler data, roofline results, or hardware counters, classifying bottlenecks, or validating evidence for a claimed speedup.
---

# GPU Performance Evidence

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md) — return to overall routing and priority selection
- [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md) — load when evidence points to memory traffic, temporaries, or layout cost
- [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md) — load when peak live overlap, workspaces, allocation reuse, or rematerialization matter
- [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md) — load when capacity and allocatability differ or backing policy is material
- [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md) — load when residency, placement, movement, or oversubscription matters
- [gpu-state-reuse-eviction](../gpu-state-reuse-eviction/SKILL.md) — load when retained-state identity, validity, value, or logical eviction matters
- [gpu-persistent-state](../gpu-persistent-state/SKILL.md) — load when cross-call growth, mutation, ownership, reconstruction, or cleanup matters
- [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md) — load when exposed memory stalls or joint compute/memory ordering matters
- [gpu-kernel-execution](../gpu-kernel-execution/SKILL.md) — load when a specific hot kernel needs execution-level tuning
- [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) — load when timeline gaps, compiler behavior, or runtime overhead dominate
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load before accepting or reporting the optimization

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Performance work starts from a measured baseline and ends with a measured end-to-end result. Source inspection can generate hypotheses; it cannot by itself establish the bottleneck or prove speedup.

Use the highest-level measurement that still answers the question. First locate the expensive phase in an application timeline. Then drill into a hot kernel only when kernel-level details can change the decision. Avoid collecting every hardware counter before knowing which kernel matters.

## Baseline record

Before modifying code, identify what is known.

Record:

- **Hardware**: Target GPU or GPU family, compute capability, memory bandwidth.
- **Software**: Framework, compiler, runtime, backend (e.g., JAX/XLA, torch.compile/Inductor, CUDA, Triton).
- **Kernel purpose**: What the code computes and why.
- **Shapes**: Input shapes, dtypes, strides, layouts, alignments, batch sizes.
- **Boundary cases**: Non-divisible sizes, singleton dimensions, empty inputs.
- **Current metrics**: Runtime (median, p95), throughput, bandwidth, occupancy, kernel count, peak memory, allocation count.
- **Correctness**: Existing tests, tolerance, deterministic mode requirements.
- **Target**: Latency, throughput, memory footprint, energy, compilation time, or end-to-end wall time.

If data is missing, proceed with conservative assumptions. State which measurements would confirm or reject the optimization.

### Representative workload checklist

Do not benchmark only on random-normal inputs with a single shape. Test:

- Small, medium, target, and maximum input sizes.
- Non-power-of-2 sizes and non-divisible dimensions.
- Batch size sweeps.
- Channel/head/feature dimension sweeps.
- Different dtypes (fp32, fp16, bf16, mixed).
- Different layouts (contiguous vs non-contiguous, channel-last vs channel-first).
- Real data distributions and extreme data distributions.
- Sparse, all-zero, constant, large-value, small-value inputs.
- Training and inference paths (if the code is used for both).
- Gradient computation (if the code is differentiated).

An optimization that only wins on hand-picked shapes must not become an unguarded general default; a shape-specialized kernel behind a guard/flag in the dispatcher is acceptable when its domain is stated.

---

### Benchmark state must be explicit

Record whether each timing includes or excludes:

- compilation/JIT/autotuning;
- allocator warm-up and memory-pool initialization;
- data loading and host preprocessing;
- host↔device or device↔device transfers;
- synchronization inserted only for measurement;
- graph capture/warm-up versus graph replay;
- forward only versus forward+backward+optimizer;
- distributed collectives and synchronization;
- cache-hot versus cache-cold state.

Do not compare timings with different scopes. If one path includes compilation and another does not, report both cold and steady-state numbers separately.

## Bottleneck classification

Classify the dominant bottleneck before choosing an optimization.

Use these categories:

- Global memory bandwidth.
- Cache bandwidth.
- Memory latency.
- Arithmetic throughput.
- Matrix/tensor-core utilization.
- Launch overhead.
- Kernel count (many small launches).
- Synchronization overhead.
- Atomic contention.
- Warp, wavefront, or subgroup divergence.
- Irregular memory access.
- Layout conversion overhead.
- Intermediate materialization.
- Register pressure.
- Shared/local memory pressure.
- Low occupancy.
- Instruction dependency latency.
- Host-device transfer.
- Device-device copy.
- Communication between GPUs.
- Work imbalance.
- Compiler-generated overhead.
- Allocation/deallocation overhead.
- Capacity or allocatability failure.
- Internal or external fragmentation.
- Mapping, fault, or address-translation overhead.
- Residency miss or migration overhead.
- State lookup, invalidation, or retention interference.
- Critical-path memory stall, staging pressure, starvation, or resource-wait cycle.

Do not optimize for occupancy, arithmetic intensity, fusion, or vectorization blindly. Optimize the observed bottleneck. Re-classify the bottleneck after every optimization round — yesterday's bottleneck is rarely today's.

---

### Evidence hierarchy

Use an application timeline first to answer: *where is wall time spent?* Use kernel-level analysis second to answer: *why is this hot kernel slow?* Use compiler IR or generated code to answer: *did the intended lowering happen?* Use hardware counters to answer: *which execution resource limits the kernel?*

A practical sequence is:

1. End-to-end wall time and throughput/latency distribution.
2. Timeline: CPU launch gaps, kernels, copies, collectives, synchronizations.
3. Kernel ranking by total time and call count.
4. Roofline or byte/FLOP estimate for the top candidates.
5. Targeted counters: achieved bandwidth, cache behavior, occupancy/resources, matrix-unit utilization, stalls, divergence, atomics.
6. Re-measure after each material change.

On NVIDIA, Nsight Systems is typically the timeline tool and Nsight Compute the kernel/counter tool. On AMD, rocprofv3/rocProfiler-SDK and ROCprof Compute Viewer provide analogous trace and counter workflows. Framework profilers are useful for attributing kernels back to Python or graph operators. Tool names and available counters vary by version; use the current toolchain for the target environment.

## Roofline and byte accounting

Use roofline reasoning as a model, not as a decorative chart. Estimate arithmetic intensity as useful operations divided by bytes transferred at the relevant memory level. Compare the measured kernel against the memory and compute ceilings of the target device and precision mode.

For a memory-bound hypothesis:

- count required input reads and output writes;
- count large intermediate write/read pairs;
- distinguish requested bytes from actual transactions when access is poorly coalesced;
- consider cache reuse, but do not assume a cache hit without evidence;
- estimate the lower bound `time >= bytes / sustainable_bandwidth`.

For a compute-bound hypothesis:

- count the relevant arithmetic operations;
- use the throughput ceiling for the actual instruction/data type, not a marketing peak for a different precision;
- verify that the generated kernel actually uses the intended matrix/tensor/vector units;
- estimate `time >= operations / sustainable_compute_rate`.

For launch-bound paths, roofline can be the wrong abstraction. Many short kernels may each be efficient while the application remains dominated by dispatch gaps. Count launches and inspect the timeline.

## Anchor operation and data lifetime

Find the expensive operation that already touches the data. Use it as the anchor.

An anchor can be:

- Matrix multiplication.
- Convolution.
- Tensor contraction.
- Attention-like tiled computation.
- Reduction.
- Scan / prefix-sum / prefix-product.
- Stencil.
- Sort, select, or histogram phase.
- FFT-like stage.
- Batched small matrix operation.
- Image, video, or signal-processing tile.
- Physics, graph, or simulation update.
- Any dominant kernel in the profile.

Then inspect the data lifetime around the anchor.

Ask:

- Which values are already in registers, fragments, vector lanes, shared/local memory, cache, or a workgroup tile?
- Which neighboring operation consumes the anchor output immediately?
- Which neighboring operation produces an input for the anchor immediately?
- Which temporary buffer exists only because two operations are separated?
- Which reduction can emit compact partial results instead of a full intermediate buffer?
- Which layout conversion can be folded into a load, store, prologue, epilogue, or consumer read?
- Which scalar, row-wise, column-wise, channel-wise, head-wise, block-wise, or tile-wise parameter can be applied while data is already on chip?

The main pattern: move cheap memory-bound work into the lifetime of expensive tiled work.

### Do not assume Tensor Core usage

Writing code in the shape of a matmul (`Q @ K^T`) does **not** guarantee Tensor Core execution. Verify through:

- Profiler trace (NVIDIA Nsight, rocprof, JAX profiler, PyTorch profiler).
- Compiler IR (HLO, StableHLO, FX graph, Inductor IR, Triton IR, PTX, SASS).
- Precision configuration (TF32, BF16, FP16, FP8, mixed precision).
- Shape alignment to tile constraints (e.g., M/N/K multiples of 8/16/32).
- Absence of implicit casts or copies that disable the fast path.

Claiming "uses Tensor Cores" without evidence is a red flag.

### Small-matrix matmul warning

When a matmul, convolution, or contraction operates on very small dimensions (e.g., 64×64 or smaller), the bottleneck is **frequently** launch overhead, runtime dispatch, memory traffic, synchronization, or insufficient grid parallelism rather than raw FLOPs. This is an empirical tendency, not a hard rule keyed to the matrix size.

For small matrices, tile tuning should **not** be assumed to be the first optimization lever. First determine whether launch/dispatch overhead, memory traffic, insufficient parallelism, library dispatch, or kernel execution dominates. The following remain valid candidates when profiler evidence shows meaningful kernel-level headroom:

- Batching multiple small operations together.
- Fusing the small matmul into a larger kernel.
- Reducing operator boundaries around the matmul.
- Using grouped GEMM, batched GEMM, split-K, or sliced-K.
- Changing layout so small tasks become large contiguous tasks.
- Persistent scheduling to amortize dispatch and prologue cost.
- Selecting a different library algorithm when the heuristic chose a suboptimal kernel for this shape corner.

**Rule: matrix dimensions alone do not classify the bottleneck.** A 64×64 GEMM may be launch-bound, bandwidth-bound, compute-relevant, or dominated by library dispatch depending on batch, K, fusion, dtype, hardware, and library path.

---

### Small matrix and tiny-kernel nuance

Small matrix operations often have low arithmetic work per launch, so dispatch, batching granularity, memory traffic, and surrounding operator boundaries can dominate. Do not turn this into a fixed size rule. A 64×64 GEMM can be launch-bound, bandwidth-bound, or compute-relevant depending on batch count, fusion, reuse, data type, hardware, library path, and whether many matrices are grouped into one launch.

Before concluding a small GEMM is or is not worth kernel-level tuning, **record** the following from a profiler trace — do not infer any of it from the matrix size alone:

- M, N, K, and dtype;
- batch / group count;
- kernel count and dominant kernel duration;
- CTA count and SM utilization;
- achieved matrix-pipe / tensor-core utilization;
- launch gap and total launch overhead;
- current library / kernel dispatch path;
- whether split-K, sliced-K, grouped GEMM, or a persistent strategy is in use;
- the GEMM's share of end-to-end request time.

Then verify the bottleneck hypothesis:

- whether grouped/batched GEMM reduces dispatch cost;
- whether the operation can be fused into a larger producer or consumer;
- whether data layout causes copies or prevents a library fast path;
- whether the library call is already close to the end-to-end optimum;
- whether tile tuning, split-K, sliced-K, grouped execution, persistent scheduling, or library algorithm selection changes the measured hot path rather than only a microbenchmark.

#### Small-GEMM eval

Given: a 64×64×8192 FP16 GEMM occupies 35% of request time; tensor-core utilization is high but only a few CTAs run and most SMs are idle.

Expected analysis considers: split-K, sliced-K, grouped GEMM, persistent scheduling, library algorithm selection, and fusion of neighboring operations. It does **not** conclude "this is 64×64, so do not tune the kernel."

## Kernel-count audit

Before and after every optimization, record:

| Metric | Before | After |
|:-------|-------:|------:|
| Kernel launches | | |
| Operator / graph-node count | | |
| Fusion groups | | |
| Device allocations | | |
| Host-device synchronizations | | |
| Device-device copies | | |
| Graph breaks (framework compile) | | |
| Command-buffer or graph replay success | | |
| Dominant kernel median time | | |
| Dominant kernel time % of total | | |

Many GPU programs are not bound by any single kernel. They are bound by having too many small kernels. Without a kernel count, you are guessing about launch overhead.

---

## Allocation audit

Record before and after:

- Temporary buffer count and total bytes.
- Peak device memory.
- Allocator call count.
- Memory pool hit rate.
- Extra workspace buffers introduced.
- Implicit copies (reshape/transpose that materialize).
- Host staging buffers.
- Saved tensors for backward (count and total bytes).
- In-place update status (preserved or broken).
- Memory fragmentation risk.

A kernel microbenchmark that looks faster but increases peak memory or allocation count has not passed the real test.

---

## Conditional resource and state evidence

Collect these fields only when the corresponding trigger is material. Do not burden an ordinary hot-kernel task with every resource-management audit.

| Trigger | Required evidence |
|---|---|
| Lifetime/allocation | Resource sizes and growth, alignment, complete consumers, first/last-use frontiers, asynchronous completion, workspace, peak overlap, reconstruction cost |
| Backing/fragmentation | Reserved, committed, resident, requested, charged, eligible-free bytes, largest allocatable extent, internal waste, extent distribution, mapping/fault/translation cost |
| Tiering/migration | Tier capacity, directional bandwidth/latency/topology, working set, next-use distribution, transfer/staging bytes, exposed stalls, late or unused prefetch, reversals, movement amplification |
| Reuse/eviction | Identity fields, validity predicate, mutation epoch, owner/isolation domain, valid-hit probability, work avoided, footprint, lookup, movement, maintenance, and interference |
| Persistent state | Growth law, mutation model, version lineage, ownership, retention scope, checkpoint coverage, reconstruction cost, cleanup boundary |
| Memory scheduling | Typed dependencies, readiness, critical path, exposed stalls, overlap windows, contention, staging lifetime, pressure-time, tail latency, starvation and resource-wait evidence |

Use the same snapshot and workload scope for related memory quantities. Aggregate free bytes, nominal bandwidth, hit rate, overlap duration, and average latency are insufficient on their own.

Separate measured, modeled, inferred, and assumed values. Every modeled policy needs a falsifying measurement before it becomes a finding.

---

## Profiling source of truth

Every performance claim must cite its evidence source:

| Evidence tier | Source |
|:-------------|:-------|
| **Profiler trace** | Kernel duration, count, copy, sync, launch overhead. |
| **Compiler IR** | Fusion confirmation, dot lowering, layout conversion, graph break. |
| **Roofline / byte-FLOP** | Bottleneck classification (memory vs compute vs launch). |
| **Benchmark** | Wall-time improvement (isolated + end-to-end). |
| **Memory profile** | Peak memory, allocation count, saved tensors. |
| **Hardware counters** | Occupancy, bandwidth, cache hit, tensor-core utilization, stall reasons. |
| **Correctness test** | Error statistics, tolerance compliance. |

Classify every performance claim by epistemic strength — direct observation > derived measurement > analytical model > inference > assumption — and do not promote a claim past its weakest link. A profiler or counter result is still a measurement, not ground truth: collection can change the experiment.

### Measurement validity

Required for any finding that relies on a profiler, counter, or replay-based metric:

- collection mode (trace / sampling / replay);
- replay count and whether Range / Application Range Replay preserved concurrency;
- deterministic across replays, or variance noted;
- profiler overhead and whether it altered the timed path;
- direct metric vs one derived from other counters;
- multi-pass artifacts: metrics gathered across different replay passes may disagree or read out-of-range for short kernels, variable workloads, or spin/concurrent behavior.

Treat such numbers as hypothetical until validated against an end-to-end timing.

---

## End-to-end priority rule

If an isolated kernel or ops-level benchmark accelerates but end-to-end wall time does **not** improve, the change cannot be claimed as a performance improvement. It is a local micro-optimization at best.

Report performance hierarchically:

1. Single-kernel time.
2. Operator-level time.
3. Module-level time.
4. Full forward step time.
5. Full training iteration time (forward + backward + optimizer).
6. Full inference-request time.
7. Memory peak.
8. Compile time.
9. Allocation/transfer time.

Many optimizations make a local kernel faster while increasing compile time, adding layout conversions, increasing backward cost, reducing fusion, or raising memory peak — causing end-to-end regression. Judge by the user's target metric.

---

## Evidence-driven rejection rule

Reject an optimization direction when the profiler, IR, benchmark, or byte/FLOP analysis does **not** support the bottleneck hypothesis.

Common evidence-free traps:

- Tuning occupancy without evidence that occupancy is the bottleneck.
- Changing tile sizes without profiling.
- Replacing a library primitive without proving composition overhead.
- Introducing shared memory without evidence it helps.
- Blindly fusing all adjacent kernels.
- Assuming Tensor Cores are used because the code contains a matmul.
- Assuming memory bandwidth is the bottleneck without a roofline check.
- Assuming launch overhead is the bottleneck without a kernel count.

Optimization must be driven by evidence. Without evidence, state the hypothesis and what measurement would test it. Do not implement the hypothesis as fact.

---

## Deliverable from this skill

Return a concise bottleneck statement with:

- target metric and workload scope;
- baseline numbers and measurement method;
- dominant phase/kernel/operator;
- bottleneck class with evidence;
- one ranked next experiment;
- the measurement that would falsify the hypothesis.

When a resource or runtime-state trigger applies, also name the primary decision layer: lifetime, backing, residency, logical reuse, state semantics, or scheduling. Do not collapse them into a generic “memory issue.”

Then jump to the specialist skill that matches the evidence. Do not jump directly to low-level tuning merely because a GPU kernel exists.
