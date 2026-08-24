---
name: gpu-compiler-runtime
description: Load this skill and follow it when optimizing compiled graphs, fusion, graph breaks, recompilation, GPU graphs, or multi-GPU runtime behavior in systems such as PyTorch Inductor, torch.compile, JAX/XLA, or Triton.
---

# GPU Compiler and Runtime

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md) — load first to distinguish launch/runtime overhead from kernel execution cost
- [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md) — load when the compiler graph materializes buffers or layout conversions
- [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md) — load for graph-wide liveness, workspace, aliasing, or rematerialization policy
- [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md) — load for VMM policy, contiguity, page granularity, and fragmentation
- [gpu-memory-tiering-migration](../gpu-memory-tiering-migration/SKILL.md) — load for cross-tier placement, residency, and migration policy
- [gpu-memory-scheduling](../gpu-memory-scheduling/SKILL.md) — load for the joint logical order of compute and memory actions
- [gpu-kernel-execution](../gpu-kernel-execution/SKILL.md) — load when generated kernels themselves are hot
- [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md) — load when compiled backward graphs or training steps are involved
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load to separate cold compile time, warm steady state, and end-to-end results

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

A GPU application can be slow even when every individual kernel is good. The missing performance may live in graph breaks, recompilation, launch gaps, allocation churn, host-device synchronization, transfer staging, or communication.

Treat the compiler/runtime pipeline as a second program: inspect what graph was captured, what kernels were emitted, how often they launch, and how the host feeds the device.

Keep concrete compiler, capture, queue, stream, event, allocator, mapping, transfer, and communication mechanisms here. Hand logical lifetime, VMM/backing policy, tier placement, and joint memory-action timing to their specialists, then verify that the runtime can realize the selected policy.

## Framework compiler checklist

For JAX/XLA, PyTorch Inductor, TensorFlow Graph, TVM, MLIR, Triton, or OpenXLA code, check:

- **Compilation boundary**: Is `jit`, `compile`, `torch.compile`, or graph capture applied? Is the boundary where you think it is?
- **Shape polymorphism**: Are shapes static or dynamic? Dynamic shapes may cause recompilation or extra dispatch.
- **Host-side Python loops**: Are loops staying on the host and preventing fusion? Should they be `scan`, `vmap`, `while_loop`, or `fori_loop`?
- **Higher-order primitives**: Does `vmap`, `scan`, `map`, `while_loop` lower efficiently?
- **Einsum/matmul/conv lowering**: Does `einsum` actually become a `dot_general`, `cublas` call, or `triton` kernel? Check IR.
- **Reshape/transpose/permute/view**: Are these zero-cost layout reinterpretations or do they trigger copies?
- **Elementwise chain fusion**: Is the compiler fusing the chain? Check with `jax.jit(f).lower(...).compile(...).as_text()` or FX graph.
- **Graph breaks**: Does a Python construct or unsupported op break the compiled graph? A graph break splits or terminates a compiled region — it is a potential optimization boundary, not a kernel-count unit.
- **Dynamic indexing, gather, scatter**: Do these prevent fusion?
- **Backward graph**: Does autograd produce extra intermediate tensors? Check the backward HLO / FX graph.
- **Compile time vs execution time**: Separate them in benchmarks.
- **Precision config**: Is TF32, BF16, FP16, mixed precision enabled? Does the matmul precision config match your intent?
- **IR verification**: After claiming an optimization, inspect the lowered IR to confirm the change actually took effect.

---

### Graph break analysis

A graph break splits or terminates a compiled region; it is a potential optimization boundary, not a kernel-count unit. For each material graph break, inspect the resulting compiled regions and runtime timeline rather than counting breaks:

- Does the break execute GPU work or CPU-only work (e.g., logging, pure-Python bookkeeping)?
- How many compiled regions result, and what eager operators execute between them?
- What kernel-count delta is actually observed on the timeline?
- What tensors materialize across the break?
- Does the break introduce host-device synchronization?
- Does it prevent fusion or graph capture that a larger captured graph would allow?
- Is the break executed once or repeatedly inside a loop (so one source break may appear many times at runtime)?

Do not infer a kernel-count delta from the graph-break count.

## Graph capture and compilation boundaries

For graph compilers and JIT systems, identify the exact boundary of compilation. A source-level function call does not guarantee one graph, and one graph does not guarantee one kernel.

Check:

- graph breaks or unsupported operators;
- guards and recompilation causes;
- static versus dynamic shape behavior;
- Python/data-dependent control flow;
- device synchronization caused by scalar extraction or host reads;
- compilation cache behavior;
- autotuning cost and cache invalidation;
- forward/backward partitioning;
- whether fusion was legal but rejected by a cost model;
- whether a library call, custom op, or opaque primitive blocks fusion.

In PyTorch compiler workflows, use current profiler/logging facilities to identify compiled regions, graph breaks, guards, and recompilations. Logging names and internals can change by version; prefer the documented diagnostics for the installed release. In JAX/XLA-style workflows, inspect the lowered StableHLO/HLO or executable representation and distinguish Python tracing/compilation from repeated device execution.

## Compiler verification

Do not claim a compiler optimization because the source “looks fusible.” Confirm one or more of:

- operator/node count changed;
- fusion groups changed;
- generated kernel count changed;
- the intermediate allocation disappeared;
- the intended dot/convolution/library primitive lowering is present;
- graph breaks or recompilations decreased;
- generated Triton/LLVM/PTX/ISA or other backend code reflects the change.

A compiler may already perform the optimization, making a manual rewrite redundant. It may also refuse fusion due to aliases, dynamic shapes, layout constraints, resource pressure, or unsupported control flow.

## Launch overhead and GPU graphs

GPU performance often fails outside the kernel.

Check: kernel launch count, graph capture/command-buffer reuse, compilation overhead, allocation overhead, temporary buffer allocation, host-device copies, device-device copies, stream/queue overlap, event synchronization, runtime dispatch overhead, framework graph breaks, shape polymorphism overhead, autotuning overhead, data residency across calls.

Do not optimize a kernel in isolation if end-to-end runtime is dominated by launch, allocation, transfer, or graph breaks.

---

GPU/command graphs can reduce repeated CPU launch overhead when the workload is sufficiently static. Before graphing, verify the timeline shows launch gaps or CPU dispatch as a meaningful cost.

Typical graph prerequisites include stable operation structure and, depending on the runtime, stable shapes, parameters, and memory addresses. Captured execution must not depend on host-side work that disappears during replay. Keep inputs in stable buffers and update contents through supported copy/update patterns when required.

Do not graph a region merely because many kernels exist. A few long-running kernels with high device utilization may gain little. Graph capture also introduces warm-up, capture constraints, memory-lifetime requirements, and debugging complexity.

## Synchronization audit

Search for hidden host/device barriers:

- scalar extraction from device tensors;
- `.cpu()`/host copies in the critical loop;
- blocking memcpy or queue flush;
- debug checks that synchronize every iteration;
- allocator behavior that forces synchronization;
- stream/default-stream interactions;
- distributed collectives followed by premature waits.

Preserve correctness by replacing broad synchronization with explicit dependency edges, events, streams/queues, or graph dependencies where supported.

## Allocation and memory-pool behavior

Repeated allocation/free can become visible at small kernel scales and can fragment memory. Prefer reuse or framework memory pools when lifetime is regular. But do not keep large buffers alive indefinitely if peak capacity is the limiting target.

Track:

- allocation count per iteration/request;
- peak live bytes;
- reuse/pool hit behavior where visible;
- graph-capture memory requirements;
- workspace stability across shapes;
- hidden copies caused by contiguity/layout conversion.

Use this section to diagnose the runtime mechanism and capture constraints. Route graph-wide liveness, transient alias eligibility, workspace sharing, and rematerialization policy to `gpu-resource-lifetime-allocation`. Route capacity-versus-allocatability, page granularity, virtual contiguity, stitching, or compaction to `gpu-virtual-memory-fragmentation`.

## Host↔device and device↔device transfers

Minimize transfers across lower-bandwidth boundaries and overlap them with compute when the hardware/runtime supports it. Overlap requires actual independence and appropriate pinned/page-locked or device-accessible staging where applicable.

Do not introduce extra copies just to make an API asynchronous. Measure the total path, including staging and synchronization. Unified/managed memory can simplify programming but may incur migration; profile page movement and prefetch behavior for oversubscribed workloads.

Route the choice of target tier, residency policy, prefetch/offload trigger, replication, and migration to `gpu-memory-tiering-migration`. Keep API capability, registration, mapping, queue submission, and synchronization implementation here.

## Multi-GPU runtime

For multi-GPU programs, inspect communication as part of the dataflow.

Check: sharding layout, collective placement, communication volume, communication precision, compute-communication overlap, extra transposes before collectives, extra gathers after collectives, redundant replication, peer-to-peer transfer path, host staging, synchronization between devices, load balance across devices.

Do not fuse across a boundary if it delays communication overlap or increases communication volume.

---

### Communication overlap

Treat collectives as part of the critical path. Ask:

- can gradients/activations be communicated in smaller readiness buckets;
- can communication overlap useful compute without delaying a later dependency;
- does fusion postpone the moment a buffer becomes ready and therefore reduce overlap;
- do layout conversions occur immediately before/after collectives;
- is communication volume larger than algorithmically necessary;
- is work balanced across ranks/devices;
- does a synchronization wait for all devices when only a subset dependency is required?

A local kernel speedup can regress distributed training if it destroys overlap or increases communication pressure.

## Shape strategy and specialization

Dynamic shapes create a trade-off between specialization quality and compilation/recompilation cost. Choose deliberately among:

- fully static shapes for maximum specialization and graph reuse;
- a small number of shape buckets for stable serving workloads;
- symbolic/dynamic compilation for broad shape coverage;
- eager or reference fallback for rare outliers.

Measure the distribution of real shapes before choosing. A highly specialized kernel that recompiles for every request can lose to a less specialized stable graph. Conversely, making every dimension dynamic can block constant propagation, vectorization, layout specialization, or autotuning opportunities.

Record which dimensions are truly variable and which can be normalized by padding, bucketing, batching, or API contracts. Include the padding cost in end-to-end measurements.

## Compiler optimization versus algorithmic optimization

Compilers are good at many local transformations: pointwise fusion, common subexpression elimination, buffer reuse, layout propagation, and some reduction fusion. They generally cannot be assumed to discover every algorithmic reformulation.

When a compiler-generated graph remains slow, ask whether the missing change is:

- a graph-capture problem;
- a cost-model choice;
- a backend code-generation problem;
- a library dispatch issue;
- an algorithmic reformulation that changes the graph itself.

Do not fight the compiler with source rewrites until the missing transformation is identified. Sometimes the correct fix is to expose a pattern the compiler recognizes; sometimes it is to use a tuned primitive; sometimes it is to write a custom kernel.

## Triton and autotuning discipline

For Triton or other tile-level DSLs, separate correctness parameters from performance parameters. Typical performance axes include block/tile dimensions, number of warps/waves, pipeline stages, vector width, and architecture-specific matrix instruction choices.

Autotune only over configurations that are legal for the shape, dtype, layout, and target architecture. Cache results with enough environment identity to avoid reusing a configuration across incompatible devices or compiler versions.

Avoid enormous search spaces by first using profiler evidence and resource estimates to eliminate obviously bad regions. Benchmark with representative shapes, not only one canonical matrix.

Inspect generated code when a high-level configuration behaves unexpectedly. Compiler IR, backend IR, PTX/ISA, and resource reports can reveal extra layout conversions, spills, scalarized memory operations, or an unexpected library fallback.

## Runtime queueing and overlap

A healthy GPU timeline is not necessarily a single uninterrupted bar. Useful overlap can involve copies, compute, and collectives on different engines or streams/queues.

Check whether operations are independent before attempting overlap. Then verify:

- dependencies are represented explicitly;
- default-stream or global synchronization is not serializing work;
- staging buffers remain alive until consumers finish;
- copy engines and peer paths exist on the target system;
- overlap improves the critical path rather than merely moving work off the main stream.

Overlapping two operations that contend for the same saturated resource may not improve wall time. Measure the critical path.

When the decision requires jointly ordering compute, allocation, mapping, transfer, rematerialization, barriers, and reclamation, load `gpu-memory-scheduling`. This skill should return which concrete mechanisms are supported, what constraints they insert, and the realized order; it should not silently replace the scheduling policy with a convenient queue order.

## Runtime acceptance

Report separately:

- cold start/compile/autotune time;
- warm steady-state latency/throughput;
- graph capture cost and replay performance;
- launch count and GPU idle gaps;
- transfer volume and overlap;
- distributed communication time and overlap;
- end-to-end request or iteration time.

A compiler/runtime change is successful only when the relevant user-facing metric improves under the deployment mode that matters.
