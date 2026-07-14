---
name: gpu-reductions-scans
description: Load this skill and follow it when optimizing GPU reductions, scans, prefix operations, recurrences, streaming state, tile-local partials, or their boundary semantics.
---

# GPU Reductions and Scans

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) — load for reduction order, floating-point error, masks, and boundary semantics
- [gpu-memory-fusion-layout](../gpu-memory-fusion-layout/SKILL.md) — load to remove full-size intermediates or fuse compact partials
- [gpu-persistent-state](../gpu-persistent-state/SKILL.md) — load when state survives independent invocations and needs ownership, mutation, snapshots, reconstruction, or cleanup semantics
- [gpu-kernel-execution](../gpu-kernel-execution/SKILL.md) — load for subgroup/workgroup reductions, synchronization, and resource tuning
- [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md) — load when the reduction participates in backward or gradient accumulation
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load for boundary matrices, error trends, and performance acceptance

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

Reductions, scans, prefix operations, and recurrences are not ordinary elementwise kernels. Their performance is governed by state size, associativity, dependency depth, cross-tile combination, synchronization, and numerical order. Optimize the algorithmic decomposition before tuning block sizes.

## Scan, prefix, and recurrence specialization

For programs containing scan, prefix sum, prefix product, running state, sequential recurrence, or streaming update:

- **State size**: Is the scan state a scalar, vector, matrix, or larger? The cost of storing and combining state grows with state size.
- **Global vs chunked**: Does the scan run over the full sequence or can it be split into chunks?
- **Intra-chunk parallelism**: Within a chunk, can the scan be replaced with a matmul, triangular solve, or block operation?
- **Inter-chunk state**: Does the inter-chunk state carry only the minimum needed to resume?
- **Associative combine**: If the update is associative, can you use `associative_scan` instead of sequential `scan`?
- **Streaming state**: Does the algorithm only need a compact running state instead of a full array of per-step states?
- **Lowering**: Does the scan lower into multiple kernel layers? Does it create large intermediate buffers? Does it prevent fusion?
- **Sequential fallback**: For low-latency online inference, is a sequential path still available?

### Inclusive / exclusive boundary rules

Scan, prefix, causal mask, attention mask, stencil, sliding window, convolution boundary, padding, and halo exchange operations have non-trivial inclusive/exclusive semantics.

Tests must cover:

- Length 0, length 1, length 2.
- First element, last element.
- Chunk / block / tile boundaries.
- Non-divisible lengths.
- Padding regions.
- All-false mask, all-true mask.
- Empty window, single-element window, maximum window.

Do not rely on comments alone to define boundary semantics. Test them.

### Chunk / block / tile boundary tests

For any chunked or tiled algorithm, test:

- `size < block_size`
- `size == block_size`
- `size == block_size + 1`
- `size` not a multiple of `block_size`
- One block, two blocks, many blocks
- Last block incomplete
- Block size = 1, block size = 2, typical block size, maximum block size
- Misaligned addresses and lengths
- Padded and masked lengths

---

## Tile-local partial reduction

Use tile-local partials when a reduction crosses tile boundaries.

Process:

1. Accumulate local partials in registers, vector lanes, fragments, shared/local memory, or subgroup state.
2. Store the smallest useful partial result.
3. Combine partials in a lightweight kernel or an existing later reduction.
4. Avoid full-size intermediate tensors.
5. Avoid atomics when privatized partials are practical.
6. Use atomics only when contention is low or the cost is dominated elsewhere.
7. Preserve numerical requirements.

Good candidates: row/column sums, norms, max/min, log-sum-exp, mean/variance, histogram bins with privatization, block-level counts, tile statistics, gradient reductions, loss reductions, sparse/graph neighborhood reductions with bounded locality.

---

## Streaming state

Use streaming state for operations that can be updated incrementally.

Keep this section scoped to state carried within one algorithm, invocation, or explicitly chunked execution. If the state survives independent calls, acquires an external owner or retention scope, supports snapshots or branches, or needs cleanup beyond the algorithm boundary, route its contract to `gpu-persistent-state`.

Candidate state: running sum, max/min, log-sum-exp, norm, mean, variance, count, histogram, prefix state, online normalisation statistics.

Process:

1. Define the smallest state that preserves correctness.
2. Update the state tile by tile.
3. Store compact state only when needed.
4. Combine states with an associative or numerically controlled rule.
5. Reconstruct final outputs only where necessary.

---

## Choose the decomposition

Use these questions:

1. Is the combine operation truly associative under the required semantics, or only mathematically associative over real numbers?
2. Does the user require deterministic order?
3. Is the state compact enough to carry between chunks?
4. Can a hierarchical tree reduce global synchronization?
5. Can an online formulation avoid storing all intermediate states?
6. Does the consumer need every prefix value, only the final aggregate, or a sparse subset?
7. Can the reduction be fused into the producer or consumer without unacceptable resource pressure?

### Final reduction only

For sums, maxima, norms, statistics, or gradients that need only the final result, prefer hierarchical partials over full-size intermediates. Keep local partials in registers or shared/local memory, write one compact result per tile/workgroup, then combine.

### Full prefix output

When every prefix value is required, decide between sequential, hierarchical scan, and chunked scan based on sequence length, state size, and latency target. A hierarchical scan may increase work but shorten dependency depth. A sequential path may still be best for tiny sequences or low-latency streaming.

### Recurrence with compact state

If the recurrence can be represented by a compact state or associative transform, carry only that state across chunks. Avoid materializing per-step state unless a later consumer requires it.

## Online algorithms

Online formulations can reduce memory traffic by combining statistics in one pass. Examples include running max/sum formulations for stable softmax-like normalization, online mean/variance combinations, and streaming log-sum-exp.

Treat online reformulations as numerical changes unless bitwise identity is proven. Their value comes from fewer passes and smaller intermediates, but their error behavior must be measured across lengths and extreme values.

## Boundary contract

Explicitly define:

- inclusive or exclusive scan;
- initial value/identity element;
- behavior for length 0 and 1;
- chunk carry-in and carry-out;
- padded elements and masks;
- last partial block;
- segmented resets;
- NaN handling for min/max-like reductions;
- tie behavior where indices are returned.

Write tests around every block/chunk threshold, not only typical sizes.

## Synchronization strategy

Reduce synchronization scope hierarchically. Prefer subgroup/warp/wave collectives for data that fits the execution group, then workgroup/block exchange, then global combination.

Global atomics can be effective when contention is low or the number of partials is small. They can be disastrous when many lanes contend on the same location. Measure contention and determinism requirements before choosing atomics.

## Numerical order

Parallel trees change accumulation order. For floating-point sums/products, report error growth against the reference over sequence length and scale. Pairwise or tree reductions can sometimes be *more* accurate than naive sequential accumulation, but they are still semantically different if the reference order matters.

Products and cumulative products deserve extra caution because underflow/overflow compounds with length. Division-based reformulations can create Inf or NaN near zeros. Load [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) for any such rewrite.

## Segmented and irregular reductions

Segmented reductions add a second problem: work imbalance and boundary discovery. A segment may contain one element or millions.

Choose among:

- one workgroup per segment for regular medium segments;
- multiple workgroups plus a second-stage combine for long segments;
- packing many short segments into one workgroup;
- persistent/work-queue scheduling for highly irregular distributions.

Measure the real segment-length distribution. An algorithm optimized for the mean can fail badly on a long tail.

Preserve segment boundaries exactly. Empty segments, repeated offsets, and the last segment are common failure cases.

## Hierarchical combine design

For large reductions, define the hierarchy explicitly:

1. lane/thread-local accumulation;
2. subgroup/warp/wave combine;
3. workgroup/block combine;
4. grid/global combine.

At each level decide whether the state fits registers, requires shared/local memory, or must be written to global memory. Keep the partial state as compact as possible.

The best hierarchy depends on reduction width, number of independent reductions, state size, and target architecture. A separate second-stage kernel is often cheap when the partial buffer is tiny, but it is not free for microsecond-scale workloads.

## Softmax-like normalizers

Softmax and log-sum-exp combine a maximum reduction with a sum of exponentials. Numerically stable online algorithms can merge passes and avoid materializing intermediate arrays. The key state is typically a running maximum plus a rescaled running sum.

When applying an online formulation:

- prove the state-combine rule;
- classify the floating-point change;
- test very large positive/negative logits;
- test all-masked rows and empty effective domains;
- define mask semantics before exponentiation;
- verify tails and row lengths around tile boundaries.

The performance goal is fewer global-memory passes and compact state, not merely fewer source lines.

## Autotuning axes for reductions and scans

Useful parameters include elements per thread, workgroup size, vector width, tile/chunk length, number of stages, and whether to use one-pass atomics or multi-stage partials.

Benchmark across reduction lengths. The best strategy for 32 elements can differ completely from 1 million elements. Guard specialized paths by size ranges instead of pretending one configuration is universal.

## Performance evidence

Measure:

- input bytes read and output/partial bytes written;
- number and size of partial buffers;
- kernel stages and launches;
- synchronization/atomic time;
- occupancy/resource usage;
- end-to-end consumer impact.

A faster reduction kernel can still regress the pipeline if it emits a layout or partial format that forces an expensive conversion later.

## Acceptance gate

A reduction/scan optimization must pass:

- semantic boundary tests;
- numerical error characterization for changed order;
- representative lengths including non-divisible tails;
- isolated and end-to-end timing;
- the algorithm-local versus cross-call state boundary is explicit;
- failure-case documentation and fallback rules.
