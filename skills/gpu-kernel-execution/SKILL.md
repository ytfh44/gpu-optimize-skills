---
name: gpu-kernel-execution
description: Load this skill and follow it when optimizing GPU kernel thread mapping, coalesced memory access, tiling, shared memory, registers, occupancy, synchronization, or atomic operations.
---

# GPU Kernel Execution

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md) — load first to identify the hot kernel and limiting resource
- [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md) — load for dataflow, coalescing, layout, and fusion decisions around the kernel
- [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) — load when reordering reductions, using fast math, or changing precision
- [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) — load when the kernel is compiler-generated or graph/runtime overhead dominates
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load for before/after counters and end-to-end acceptance

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Tune execution resources only after the hot kernel and its bottleneck are known. “Increase occupancy,” “use shared memory,” “increase tile size,” and “use Tensor Cores/MFMA” are not goals by themselves. Each is a mechanism that can help one bottleneck and hurt another.

## Compute checklist

Optimize arithmetic only after memory and materialization have been audited.

Check: matrix/tensor-core eligibility (verify via profiler/IR), dot-product eligibility, vector instruction eligibility, tile shape, instruction mix, loop unrolling, invariant hoisting, common subexpression reuse, approximate math acceptability, FMA behavior, accumulation dtype, instruction dependency chains, pipeline utilization, compiler-generated spills, fast path for common shapes.

### Library primitive replacement review

Before replacing cuBLAS, cuDNN, rocBLAS, MIOpen, oneDNN, CUTLASS, FlashAttention, Triton tuned kernels, or vendor FFT/graph libraries, prove that:

- The library primitive itself is **not** the bottleneck — the composition overhead around it is; or
- The current shape is a poor fit for the library primitive; or
- The pipeline's layout conversion cost exceeds the library benefit; or
- A custom kernel can eliminate full-buffer materialization that the library cannot avoid; or
- A custom kernel can fuse a critical epilogue/prologue that the library cannot fuse; or
- The library call granularity is so small that launch overhead dominates.

Otherwise, do not replace a mature library primitive.

---

## Parallelism mapping

Map work to the hardware execution model.

Check: warp/wavefront/subgroup/SIMD-lane coherence, workgroup/block size, per-thread work, tile ownership, tail handling, load balance, divergence, predication, persistent scheduling, grid-stride loops, cooperative groups/subgroup collectives, work stealing for irregular workloads, specialization for common sizes.

Prefer simple mappings unless profiling shows scheduling or imbalance cost.

---

### Mapping questions

Choose the work decomposition by answering:

- What is the natural output tile or independent work item?
- Which dimension should neighboring lanes traverse for coalesced access?
- Which data is reused within a warp/wave/subgroup, workgroup/block, or across workgroups?
- What is the tail behavior for non-divisible dimensions?
- Are branches coherent within the hardware execution group?
- Is there enough grid-level work to occupy the device?
- Does per-thread work expose instruction-level parallelism without causing spills?

Prefer simple ownership rules that make memory access and boundary masks obvious. Complex persistent or work-stealing schedules should be justified by measured imbalance or dispatch overhead.

## Occupancy and resource pressure

Occupancy is a tool, not the goal.

Check: register count, register spills, shared/local memory per workgroup, resident workgroups, resident warps/waves/subgroups, memory latency hiding, tensor-core/matrix-unit saturation, instruction-level parallelism, cache pressure, achieved vs theoretical occupancy.

A fused kernel can be worse if it saves memory traffic but causes spills, reduces useful occupancy, or harms scheduling.

---

High occupancy is neither necessary nor sufficient for high performance. Compute-bound matrix kernels may intentionally use many registers and shared memory to maximize reuse. Memory-latency-bound kernels may benefit more from additional resident warps. Use occupancy as a diagnostic constraint and correlate it with stall reasons and achieved throughput.

When changing tile size or fusion scope, record:

- registers per thread/lane;
- shared/local memory per block/workgroup;
- active blocks/workgroups and warps/waves;
- spills/local-memory traffic;
- achieved occupancy and stall reasons;
- instruction count and dependency chains.

A larger tile can increase arithmetic intensity while reducing parallelism. The optimum is shape- and architecture-dependent.

## Synchronization and atomics

Reduce ordering cost where correctness allows.

Check: unnecessary barriers, barrier scope, global synchronization, stream/queue synchronization, host-visible synchronization, atomic contention, privatization opportunities, subgroup reductions, workgroup reductions, hierarchical reductions, lock-free alternatives, determinism requirements.

Prefer hierarchical aggregation over hot global atomics.

---

Use the narrowest synchronization and visibility scope that preserves correctness. Avoid a device-wide or host-visible synchronization when a workgroup, stream/queue event, or dependency edge suffices.

For atomics, estimate contention. Hierarchical aggregation often wins:

1. private/register partials;
2. subgroup/warp/wave reduction;
3. block/workgroup partials;
4. one or a small number of global atomics.

But extra stages can hurt tiny workloads. Measure the actual contention and launch cost.

## Coalescing and vectorized memory access

Map adjacent lanes to adjacent addresses when possible, and keep the fastest-varying program dimension aligned with the memory layout. Verify actual transaction efficiency rather than relying only on indexing appearance.

Vectorized loads/stores can reduce instruction overhead and improve transaction efficiency when alignment and bounds permit. They can also create misalignment penalties, over-fetch, or complicated tail handling. Guard vectorized paths by alignment and shape, and keep a scalar/masked fallback.

For strided, gathered, or sparse access, ask whether a one-time upstream layout transformation can make many downstream accesses regular. Do not repeatedly transpose or pack at every operator boundary.

## Tile design

Choose tile size by balancing:

- data reuse and arithmetic intensity;
- grid-level parallelism;
- register footprint;
- shared/local-memory footprint;
- synchronization count;
- tail waste for irregular dimensions;
- matrix-unit tile constraints where relevant.

Larger tiles increase reuse but can reduce the number of resident workgroups and worsen tails. Smaller tiles increase parallelism but may reload data and increase scheduling overhead. Use resource reports and benchmarks rather than a universal tile size.

For 2D/3D problems, define ownership of loads, compute, and stores explicitly. Ensure every loaded element has enough reuse to justify staging. If a tile is loaded once and used once, shared/local memory may only add an extra copy and barrier.

## Divergence and predication

Branch divergence matters when lanes in the same execution group take long, different paths. Short conditions may be compiled to predication and be cheap. Do not rewrite readable control flow into branchless arithmetic without evidence.

Common divergence sources include irregular graph degree, variable-length sequences, sparse masks, and boundary-heavy tiles. Possible responses include work reordering, bucketing similar tasks, separate specialized kernels, or persistent scheduling. Each adds overhead and may change data locality.

## Autotuning discipline

Autotune only after establishing a correct baseline and a stable benchmark. Search dimensions that correspond to real resource trade-offs: tile sizes, lane/workgroup count, pipeline stages, split factors, vector widths, or algorithm variants.

Record the target device and shape domain for the winning configuration. A configuration tuned on one GPU generation, dtype, or matrix aspect ratio may regress elsewhere. Keep a portable default and guarded specializations where appropriate.

## Matrix-unit verification

Do not infer matrix/tensor-unit use from source syntax. Verify through profiler counters, generated ISA, compiler IR, or known library dispatch. Check:

- supported dtype/precision mode;
- operand alignment and tile shape requirements;
- accumulation type;
- implicit casts or layout conversions;
- fallback paths for unsupported shapes;
- whether a library kernel already provides the optimal path.

On NVIDIA this may involve Tensor Core instruction families; on AMD it may involve MFMA/WMMA-style matrix instructions. Terminology and exact constraints vary by architecture generation.

## Small-kernel and small-matrix behavior

Tiny kernels frequently expose fixed costs: launch/dispatch, synchronization, parameter setup, and poor amortization of memory latency. Common responses are batching, grouping, fusion, or graph replay. However, do not impose a hard dimension cutoff. A small matrix repeated thousands of times in a grouped launch is different from one standalone GEMM.

Tune tile sizes only when the kernel itself is a meaningful part of end-to-end time and the profiler shows execution-level headroom.

## Asynchronous data movement and pipelining

Modern GPUs may support architecture-specific mechanisms for overlapping global-memory movement with compute, such as asynchronous global→shared copies or tensor-memory engines. Use them only when:

- the target architecture supports the mechanism;
- the kernel has a repeated tiled producer/consumer structure;
- there is enough independent work to overlap transfer latency;
- memory ordering and synchronization are explicit;
- added staging buffers do not collapse occupancy;
- profiling shows latency or data movement is a limiting factor.

A typical multi-stage pipeline:

1. issue load/copy for tile `i+1`;
2. compute tile `i` from a completed stage;
3. retire/reuse stage `i-1` only after consumers finish;
4. synchronize with the architecture's required barrier/proxy semantics.

Do not copy architecture-specific barrier code mechanically between GPU generations or vendor stacks. Treat it as an implementation of a producer-consumer pipeline whose correctness must be re-established for the target memory model.

## Shared/local memory

Use shared/local memory when reuse or exchange justifies it. Check alignment, bank conflicts, vector width, broadcast behavior, and whether an extra copy is actually cheaper than direct cached global loads.

Padding can eliminate systematic bank conflicts but increases memory footprint. Measure both the conflict reduction and resulting occupancy impact.

## Kernel-level acceptance

A kernel change is accepted only after:

- correct results across tails and boundary shapes;
- no unplanned semantic/numerical change;
- generated code and counters support the intended mechanism;
- isolated speedup survives end-to-end measurement;
- resource usage and unsupported cases are documented.
