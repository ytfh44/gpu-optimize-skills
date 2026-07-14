---
name: gpu-training-autodiff
description: Load this skill and follow it when optimizing GPU training paths, backpropagation, saved tensors, recomputation, gradient reductions, or mixed-precision forward and backward execution together.
---

# GPU Training and Autodiff Optimization

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) — load for mixed precision, changed accumulation order, and gradient tolerances
- [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md) — load for activation memory, saved tensor layout, fusion, and recomputation tradeoffs
- [gpu-reductions-scans](../gpu-reductions-scans/SKILL.md) — load for gradient reductions, norms, scans, and recurrent backward passes
- [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) — load for AOTAutograd/compiled backward, launch overhead, and distributed runtime
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load for full training-step acceptance

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Optimize forward and backward as one program. A forward-only speedup is not enough when the training step spends more time or memory in backward, optimizer updates, gradient synchronization, or recompilation.

## Backward-pass pattern

For differentiated code, inspect forward and backward together.

Check whether backward can use: upstream gradient, anchor input/output, compact saved statistics, small parameters, cheap recomputation.

Prefer: compact saved state over full saved tensors, recompute over load when cheaper than memory traffic, fused derivative application, high-throughput contractions for weight gradients, tile-local gradient partials with compact reduction.

Do not remove saved values unless recomputation is correct for the exact dtype, mode, randomness, and numerical behavior.

### Backward mandatory testing

If the code is used for training, the optimization report must include:

- Forward correctness.
- Backward (gradient) correctness.
- Gradient tolerance relative to reference.
- Higher-order gradient (if the project requires it).
- Saved tensor count and total bytes (before vs after).
- Activation memory peak (before vs after).
- Backward kernel count (before vs after).
- Full training-step wall time (before vs after).
- Optimizer step compatibility.

Forward-only testing is insufficient to accept a training-path optimization.

---

## Required training measurements

For every training-path optimization, record before and after:

- forward wall time;
- backward wall time;
- optimizer-step wall time;
- full iteration wall time;
- activation/saved-tensor peak memory;
- temporary/workspace peak memory;
- forward and backward kernel counts;
- gradient synchronization/collective time for distributed training;
- compile/autotune cost separately from steady state.

Do not accept “forward is 20% faster” when full iteration time is unchanged or worse.

## Saved tensors versus recomputation

For each saved tensor, ask:

- is it required exactly, or can a compact statistic suffice;
- is recomputation cheaper than a global-memory load at the target shape;
- does recomputation reproduce the same randomness/dropout/mask;
- does it use the same dtype and numerical path;
- does it increase register pressure or kernel count;
- can the needed quantity be fused into a backward producer/consumer;
- does checkpointing shift peak memory enough to enable a larger batch and improve throughput?

Recomputation is not automatically cheaper. A compute-heavy matmul or expensive transcendental chain may cost more than reading a saved activation. Use byte/FLOP estimates and benchmarks.

## Gradient correctness

Test gradients against the reference using the existing project tolerance. For C2+ changes, characterize absolute/relative error and trends with depth, sequence length, batch size, and scale.

Include:

- parameter gradients;
- input gradients where required;
- zero and sparse gradient cases;
- accumulation across microbatches;
- gradient clipping/norm paths;
- loss scaling and overflow handling for mixed precision;
- higher-order gradients if the project supports them.

A forward result can look correct while backward is wrong because saved state, mask semantics, aliasing, or derivative formulas changed.

## Mixed precision

Treat storage precision, compute precision, and accumulation precision separately. Verify:

- casts are placed intentionally;
- reductions accumulate in the intended dtype;
- loss scaling and overflow detection still work;
- optimizer states retain required precision;
- denormal/flush behavior does not create silent zero gradients;
- fast math does not destabilize a sensitive derivative.

Do not silently lower precision to claim a kernel speedup.

## Fusing backward

Good candidates include:

- applying a local derivative in the producer/consumer of the gradient;
- combining pointwise gradient transforms;
- emitting compact partial parameter gradients;
- fusing dequantization/cast into a contraction input;
- reusing forward output when it is sufficient for the derivative.

Check resource pressure and saved-state requirements. A giant fused backward kernel can spill registers, reduce occupancy, or delay when gradient buckets become ready for communication.

## Distributed gradients

In data/model-parallel training, local computation and communication form one schedule. A fusion that delays a gradient tensor can reduce all-reduce overlap even if the local kernel is faster.

Track:

- bucket readiness time;
- collective duration;
- overlap fraction;
- communication precision and volume;
- extra layout conversions around collectives;
- per-rank imbalance.

Coordinate with [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) for communication/graph/runtime analysis.

## Optimizer interaction

Verify optimizer compatibility after changing gradient layout, dtype, sparsity, accumulation, or in-place behavior. Check fused optimizers, capturable optimizers, sharded optimizer states, and gradient scaling if present.

## Activation-memory accounting

Separate persistent model/optimizer state from activations, saved tensors, temporary workspaces, communication buffers, and allocator reserve. Peak memory depends on lifetime overlap, not only the sum of tensor sizes.

When a forward rewrite changes lifetimes, inspect whether:

- a tensor now lives until backward instead of dying after forward;
- fusion prevents early release of an intermediate;
- recomputation removes a saved tensor but introduces a large workspace;
- gradient accumulation keeps more buffers live across microbatches;
- a compiled graph or capture reserves stable memory pools.

Measure peak memory on the full training step, not only inside the optimized function.

## Checkpointing and recomputation strategy

Activation checkpointing trades compute for memory. Choose checkpoint boundaries around expensive-to-store regions where recomputation cost is acceptable.

Evaluate:

- bytes saved;
- extra forward work during backward;
- resulting batch-size or sequence-length opportunity;
- interaction with stochastic layers;
- communication overlap changes;
- compile/graph effects.

The right objective may be samples/sec at a larger feasible batch, not latency at a fixed batch.

## Gradient accumulation

Microbatch accumulation changes both performance and semantics of the schedule. Check:

- whether gradients accumulate in-place or through temporaries;
- accumulation dtype;
- zeroing strategy (`set_to_none`-like semantics versus explicit fills where applicable);
- synchronization frequency;
- all-reduce timing and whether communication happens per microbatch or after accumulation;
- loss scaling normalization.

A kernel optimized for one large batch may not be optimal when the same effective batch is split into many microbatches.

## Compiled autograd and graph boundaries

When using compiled forward/backward systems, inspect both graphs. A forward source rewrite can change AOT partitioning, saved tensor selection, backward fusion, or recompilation behavior.

Verify:

- whether backward is compiled or falls back to eager execution;
- number of compiled regions;
- graph breaks in forward and backward;
- recompilations caused by shape, scalar, or mode changes;
- generated kernel count for both passes;
- whether custom autograd functions or opaque ops block optimization.

Coordinate with [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) rather than assuming the compiler preserves the same partition.

## Stochasticity and reproducibility

Dropout, sampling, stochastic depth, random augmentations, and fused RNG consumption complicate reference comparisons. A fused kernel may consume random numbers in a different order even when the distribution is intended to be equivalent.

Define the required contract:

- exact RNG stream identity;
- deterministic replay for a fixed seed;
- distributional equivalence only;
- no determinism requirement.

Do not call a stochastic rewrite C1 unless the RNG sequence and outputs are truly preserved.

## Training-mode matrix

Test the modes the project actually uses:

- training with gradients;
- evaluation/inference without gradients;
- autocast on/off;
- deterministic mode on/off;
- distributed and single-device modes;
- gradient accumulation on/off;
- checkpointing on/off where supported.

A fast path can be enabled for a subset of this matrix, but the guard and fallback must make the subset explicit.

## Optimizing gradient reductions

Parameter-gradient accumulation, norm computation, clipping, and optimizer statistics often contain reductions. Use hierarchical partials and compact state where beneficial, but account for floating-point order and distributed communication.

For large parameter sets, reducing launch count can matter as much as individual reduction throughput. Fused multi-tensor optimizers or grouped reductions may help when semantics and framework support allow. Measure optimizer-step time separately.

## Failure cases specific to training

Document when the optimization is disabled or rejected, including:

- unsupported higher-order gradients;
- mutation/aliasing that breaks autograd assumptions;
- non-deterministic backward where determinism is required;
- gradient error that grows with depth or sequence length;
- extra saved state that raises peak memory;
- delayed gradient readiness that reduces communication overlap;
- optimizer incompatibility with changed layout/dtype;
- compile-time growth that outweighs runtime gain for short jobs.

## Training acceptance gate

An optimization is accepted only when:

- forward correctness passes;
- backward/gradient correctness passes;
- full iteration time improves for representative workloads;
- peak memory meets the target;
- distributed overlap does not regress materially;
- optimizer behavior remains compatible;
- failure cases and fallback conditions are explicit.
