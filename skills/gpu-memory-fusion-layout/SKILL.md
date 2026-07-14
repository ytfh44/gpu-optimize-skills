---
name: gpu-memory-fusion-layout
description: Load this skill and follow it when reducing GPU global-memory traffic, intermediate tensor materialization, layout conversions, redundant copies, or when designing safe kernel and operator fusion.
---

# GPU Memory, Fusion, and Layout

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md) — load first to prove memory traffic or launch boundaries matter
- [gpu-numerical-safety](../gpu-numerical-safety/SKILL.md) — load when fusion changes order, precision, masks, or boundary semantics
- [gpu-resource-lifetime-allocation](../gpu-resource-lifetime-allocation/SKILL.md) — load when the problem is cross-graph liveness, pooling, transient aliasing, workspace, or rematerialization planning
- [gpu-virtual-memory-fragmentation](../gpu-virtual-memory-fragmentation/SKILL.md) — load when the remaining issue is physical backing, contiguity, page granularity, or fragmentation
- [gpu-kernel-execution](../gpu-kernel-execution/SKILL.md) — load when a fusion changes registers, shared memory, occupancy, or execution mapping
- [gpu-compiler-runtime](../gpu-compiler-runtime/SKILL.md) — load when a compiler may already fuse or materialize the operations
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load to measure bytes, kernel count, peak memory, and end-to-end impact

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core principle

The highest-leverage GPU optimization is often removing work rather than accelerating an instruction: eliminate a full-buffer write/read pair, avoid a temporary, fold a layout conversion into an existing load/store, or collapse a cheap operator boundary into a hot producer or consumer.

Do not fuse blindly. Fusion is beneficial only when the traffic and launches removed outweigh added register pressure, shared memory, divergence, instruction count, compilation cost, and lost reuse.

Keep this skill focused on materialization, fusion, layout, and traffic within one producer-consumer pipeline. Route cross-graph lifetime overlap, allocator reuse, transient aliasing, workspace planning, and general retain-versus-rematerialize decisions to `gpu-resource-lifetime-allocation`. Route physical allocatability and fragmentation to `gpu-virtual-memory-fragmentation`.

## Materialization audit

### Qualitative audit

Search for avoidable buffers and launch boundaries.

Look for:

- A kernel writes a buffer that the next kernel immediately reads.
- A framework operator creates a temporary tensor that has no other consumer.
- Elementwise chains after a compute-heavy kernel.
- Elementwise chains before a compute-heavy kernel.
- Bias, scale, clamp, activation, mask, residual, cast, quantize, dequantize, pack, unpack, transpose, or layout conversion next to an anchor.
- Reductions over rows, columns, channels, heads, tokens, pixels, particles, cells, bins, or graph neighborhoods.
- Expanded broadcast tensors.
- Saved backward-pass tensors that can be recomputed cheaply or replaced with compact statistics.
- Separate kernels whose only purpose is API modularity.
- Intermediate formats that are immediately converted again.
- Host-visible synchronization inserted only to sequence GPU work.

### Quantitative intermediate-tensor table (mandatory for audit)

For every intermediate tensor ≥ 1% of peak memory, fill out:

| Buffer | Shape | Dtype | Bytes | Producer | Consumer(s) | Reuse count | Removable? | Strategy |
|:-------|:------|:------|------:|:---------|:------------|------------:|:----------:|:---------|
| ... | | | | | | | | |

For each row, answer:

- Is the buffer consumed exactly once?
- Is it consumed immediately by the next kernel?
- Is it an expanded broadcast of a smaller tensor (store the compact form)?
- Is it a layout conversion intermediate (fold the conversion into the producer or consumer)?
- Does it exist only for API modularity (inline or fuse)?
- Can it be replaced by a compact statistic (tile-local partial, running state)?
- Can it be recomputed cheaply instead of stored?
- Can it be deferred to a later consumer that already reads the same data?

---

### Byte-lifetime analysis

For each large buffer, trace its lifetime from creation to last use. Classify it as:

- required external output;
- reusable input/cache state;
- transient full-size intermediate;
- expanded broadcast of a compact value;
- layout/packing conversion;
- saved state for backward;
- communication staging;
- workspace required by a library algorithm.

Estimate traffic removed by a proposal. For an intermediate of `N` elements and element size `s`, removing one full producer store and one consumer load saves roughly `2*N*s` bytes at the logical level, before accounting for cache effects and transaction overhead. This estimate is not proof of speedup, but it provides a falsifiable expectation.

When reuse exists, avoid deleting a materialization that multiple consumers exploit efficiently. A fused producer may force recomputation or duplicate loads in several consumers. Track consumer count and locality, not only buffer size.

## Fusion legality and cost

### Legality test

A transformation is usually safe to fuse when each output element or tile depends only on:

- The current element or tile.
- Same-index tensors.
- Broadcast scalars or vectors.
- Row, column, channel, head, block, or tile parameters.
- Small constants or coherent lookup tables.
- Tile-local partial reductions.
- Associative or monotonic streaming state.
- Values already loaded by the anchor.

A transformation is usually risky to fuse when it requires:

- Arbitrary cross-tile communication.
- Global ordering.
- Global synchronization.
- Hot global atomics.
- Large random lookups.
- Uncoalesced gather/scatter that dominates runtime.
- Heavy branch divergence.
- Large additional register state.
- Large additional shared/local memory.
- A separate algorithmic phase that dominates runtime.
- A data layout that the next major operation cannot use efficiently.

### Fusion anti-benefit checklist

Every fusion must also be checked for regressions:

- **Register count**: Did it increase? → risk of spilling.
- **Register spills**: Did the compiler spill? → check profiler or PTX/SASS.
- **Shared/local memory**: Did it increase? → risk of lower occupancy.
- **Occupancy**: Did it drop? → less latency hiding.
- **Instruction cache pressure**: Did it increase?
- **Branch divergence**: Did it increase?
- **Memory coalescing**: Did vectorised load/store break? Are stores still coalesced?
- **Cache reuse**: Did we lose the opportunity for a downstream kernel to reuse intermediate data?
- **Backward complexity**: Did fusion make the backward pass harder or more memory-intensive?
- **Compile time**: Did it increase noticeably?
- **Debuggability**: Is the fused kernel substantially harder to understand?

Keep the fusion only when the memory round-trips or launch boundaries removed outweigh these costs.

### Producer epilogue pattern

Use a producer epilogue when an anchor produces values that are immediately transformed before storage.

Candidate epilogue work: bias, scale, affine, clamp, activation, residual, mask, cast, quantize, dequantize, pack, store swizzle, local derivative, compact side-output, tile-local partial reduction.

Check: added registers, instructions, shared memory, store coalescing, vectorized store validity, alignment, boundary masks, numerical tolerance, output layout suitability for next consumer.

Prefer epilogue fusion when it removes a full write-read pair to global memory.

### Consumer prologue pattern

Use a consumer prologue when an anchor reads values that are immediately transformed after loading.

Candidate prologue work: type conversion, dequantization, unpacking, load swizzle, scale, broadcast parameter, mask, layout interpretation, cheap recomputation, coherent gather, loading compact statistics.

Check: load coalescing, cache behavior, alignment, extra register pressure, branch cost, reuse within tile, shareability across lanes.

Prefer prologue fusion when it removes a temporary input buffer or avoids a separate conversion kernel.

---

### Fusion decision record

For each proposed fusion, write:

- producer and consumer;
- temporary or boundary removed;
- logical bytes saved;
- launches removed;
- extra arithmetic;
- extra registers/shared memory expected;
- numerical class;
- guard/fallback;
- downstream layout effect;
- evidence that the compiler/runtime did or did not already fuse it.

This prevents “fusion” from becoming a generic recommendation.

## Layout strategy

Treat layout as an end-to-end contract, not a local detail.

Check:

- Which layout the dominant anchors prefer.
- Which layout the preceding and following kernels can consume.
- Whether layout conversion happens repeatedly.
- Whether an output can be stored directly in the next required layout.
- Whether a load can interpret the previous layout without materializing a conversion.
- Whether padding improves alignment or bank behavior.
- Whether vectorized access remains valid.
- Whether boundary handling gets more expensive.

Prefer one stable layout across a pipeline over repeated local conversions.

### Layout change reverse-impact check

Any reshape, transpose, permute, view, flatten, unflatten, batch-merge, or head-merge operation must be checked for downstream and backward impact:

- Did the change save a local copy but force a downstream copy?
- Does the new output layout match the next anchor's preferred input layout?
- Does the backward pass introduce extra transposes?
- Does gradient accumulation require a different layout?
- Do parameter gradients need extra reduction or copying?
- Are saved backward tensors in a suitable layout?
- Did the layout change break vectorized load/store?
- Did the layout change break coalescing?
- Did the layout change increase bank conflicts?
- Does the layout change affect the external API contract?

Layout is a pipeline contract. Do not optimize locally and break globally.

---

### Stable pipeline layout

Choose layout from the perspective of the pipeline's dominant anchors, not a single operator. A local transpose may speed one kernel while forcing another transpose before the next major operation.

Prefer:

- one stable layout across several operators;
- direct store into the next consumer's preferred layout when legal;
- load-time interpretation or swizzle when cheaper than materialization;
- shape padding only when the resulting extra work is smaller than the alignment/vectorization benefit;
- explicit layout contracts at API boundaries.

Measure backward impact for training paths. A forward layout optimization can introduce gradient transposes, scatter/gather patterns, or extra saved buffers.

## Global-memory access

Optimize global memory first when memory traffic dominates.

Check: coalesced loads/stores, alignment, vectorized transactions, unit-stride inner loops, redundant loads, read-only data paths, constant/uniform data paths, cache locality, shared/local memory reuse, bank conflicts, padding, prefetching, asynchronous copy (e.g., `cp.async`, TMA), write combining, avoided write-allocate, boundary mask overhead.

Do not use shared/local memory unless it increases reuse, improves coalescing, reduces redundant loads, or enables better scheduling.

---

### Coalescing is architecture-aware but general

The exact transaction size and lane grouping vary across architectures, but the general rule is stable: neighboring lanes should access compact, aligned regions when the algorithm permits. Measure actual transaction efficiency or achieved bandwidth where tools expose it.

Do not contort data into a coalesced access pattern if the conversion cost is larger than the benefit. Consider whether the layout can be changed once upstream rather than repeatedly transformed at each kernel.

## On-chip reuse

Use shared/local memory, registers, fragments, or cache only when they reduce redundant global traffic, improve coalescing, enable a necessary exchange, or support a better schedule.

Before adding shared/local memory, answer:

- How many global loads does it eliminate per tile?
- How many times is each loaded value reused?
- Does the access pattern introduce bank conflicts?
- Does the larger allocation reduce residency enough to hurt latency hiding?
- Can register tiling achieve the same reuse with lower synchronization cost?
- Does an asynchronous copy pipeline help on the target architecture, or is the kernel too small to amortize it?

## Producer epilogue and consumer prologue

The preferred fusion points are operations that already touch the data.

**Producer epilogue candidates:** bias, scale, activation, clamp, residual, mask, cast, quantize/dequantize, packing, store swizzle, compact side statistics.

**Consumer prologue candidates:** dequantization, unpacking, type conversion, load swizzle, scale, broadcast parameters, masks, coherent gather, cheap recomputation.

Keep the operation close to the data lifetime. Avoid creating a new full-size intermediate merely to preserve an API boundary.

## Allocation and peak-memory impact

A faster fused kernel can still be a regression if it increases workspace, fragments the allocator, or forces a second live copy of a large tensor. Track peak live bytes, temporary count, allocator calls, and workspace requirements. For memory-constrained workloads, memory capacity is part of the target metric, not a secondary detail.

Use these measurements to judge the local fusion. Do not turn this section into a global allocator plan. If the decision depends on nonlocal consumers, asynchronous last-use proof, all-graph peak overlap, pool sizing, physical extents, or cross-call retention, hand the audit to the matching resource-management specialist.

## Acceptance gate

Keep a memory/fusion/layout change only when:

- the intended intermediate, conversion, or launch is actually removed;
- correctness and numerical contracts pass;
- resource pressure does not erase the gain;
- peak memory does not regress beyond the accepted target;
- end-to-end timing improves for representative modes and shapes.
