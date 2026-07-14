# GPU Resource and State Management Routing Evaluations

Use these cases to test routing and behavior without exposing the expected answer to the agent under test. Give a routing agent only the raw prompt and `gpu-code-optimizer`. Give a behavior agent only the raw prompt and the expected primary skill. Do not include the remaining fields in the test prompt.

## Evaluation contract

For every case, record:

- the selected primary skill;
- any secondary skills and the trigger that justified each one;
- the facts the agent requested or measured;
- the alternatives it compared;
- the conditions under which it would reject its preferred option;
- the acceptance evidence it required.

Fail a case when the agent assumes that paging, offload, least-recently-used eviction, reuse, virtual contiguity, transfer overlap, or proactive migration is beneficial without workload evidence.

## Direct lifetime and allocation planning

**Raw user prompt**

> A task graph creates several large temporary buffers and a variable workspace. The peak exceeds device capacity even though most values are consumed far apart in time. Plan a safe memory reduction without changing numerical results.

**Expected primary skill:** `gpu-resource-lifetime-allocation`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-memory-scheduling`, `gpu-optimization-validation`; add `gpu-training-autodiff` only if the graph includes gradients.

**Must inspect:** size, growth rule, alignment, owner and isolation domain, first use, last use, consumers, aliasing constraints, overwrite or sanitization requirement, reconstruction cost, workspace demand, and peak overlap.

**Forbidden assumptions:** all temporary buffers can alias; cross-owner reuse is authorized or automatically sanitized; every value is cheap to reconstruct; nominal live bytes equal allocatable capacity.

**Pass condition:** produce a resource inventory and a lifetime/allocation plan that distinguishes release, reuse, aliasing, retention, and rematerialization, with guards for dynamic lifetimes.

## Direct virtual backing and fragmentation diagnosis

**Raw user prompt**

> The runtime reports several gigabytes free, but a new contiguous allocation fails after a long sequence of differently sized allocations and frees. Diagnose the failure and compare remedies.

**Expected primary skill:** `gpu-virtual-memory-fragmentation`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-resource-lifetime-allocation`, `gpu-compiler-runtime`, `gpu-optimization-validation`.

**Must inspect:** reserved, committed, resident, and free bytes; largest allocatable extent; size and alignment distribution; internal waste; free-extent distribution; mapping granularity; owner and isolation domain; old-mapping revocation; overwrite or sanitization contract; allocation trace.

**Forbidden assumptions:** total free bytes imply allocatability; compaction is free; virtual mapping removes all fragmentation; remapping revokes every old access or clears residual contents automatically; the allocator is the only cause.

**Pass condition:** separate capacity pressure from internal and external fragmentation, then compare reuse, size classes, compaction, virtual stitching, and changed object lifetimes using measured costs.

## Direct tiering and migration planning

**Raw user prompt**

> A workload oversubscribes device memory. Some resources have long inactive intervals and can live on peer, host, or storage tiers. Design placement and movement policies that protect end-to-end latency.

**Expected primary skill:** `gpu-memory-tiering-migration`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-memory-scheduling`, `gpu-virtual-memory-fragmentation`, `gpu-optimization-validation`.

**Must inspect:** tier capacity, bandwidth, latency, topology, concurrency, resource working set, next-use distribution, dirty state, data classification, permitted destinations and paths, movement authorization, required protection, transfer volume, and tail stalls.

**Forbidden assumptions:** lower tiers are interchangeable or all permitted; transfers always overlap; replication is free; high average bandwidth prevents tail stalls; a faster path is authorized or sufficiently protected.

**Pass condition:** produce a residency state machine and traffic budget with explicit prefetch, offload, migration, replication, fallback, and thrashing conditions.

## Direct state reuse and eviction planning

**Raw user prompt**

> Repeated requests may reuse previously computed runtime state, but state validity depends on configuration, owner, position, layout, and mutation history. Define safe sharing, admission, and eviction.

**Expected primary skill:** `gpu-state-reuse-eviction`

**Allowed secondary skills:** `gpu-persistent-state`, `gpu-memory-tiering-migration`, `gpu-performance-evidence`, `gpu-optimization-validation`.

**Must inspect:** identity fields, validity predicate, mutation epoch, owner and isolation domain, shareability, expected reuse, saved work, footprint, lookup cost, movement cost, and interference cost.

**Forbidden assumptions:** address equality proves semantic identity; a hit always has positive value; immutable prefixes imply mutable suffixes can be shared; least-recently-used is optimal.

**Pass condition:** define a reuse safety contract and a value function that can reject unsafe or low-value retention independently of physical residency decisions.

## Direct persistent state design

**Raw user prompt**

> A runtime maintains several cross-call states: one grows by appending immutable history, one is fixed-size and updated in place, and one supports immutable snapshots and branches. Design their state contracts and cleanup boundaries.

**Expected primary skill:** `gpu-persistent-state`

**Allowed secondary skills:** `gpu-state-reuse-eviction`, `gpu-resource-lifetime-allocation`, `gpu-memory-tiering-migration`, `gpu-optimization-validation`.

**Must inspect:** growth law, mutation model, ownership, retention scope, version or epoch, branch and snapshot semantics, reconstruction cost, cleanup boundary, and concurrency rules.

**Forbidden assumptions:** every state should use the same paging or checkpoint policy; append-only and in-place mutable objects share the same identity rules; runtime persistence implies durable storage.

**Pass condition:** classify each state independently and define legal transitions, snapshots, branching, rollback, reconstruction, and cleanup without introducing crash-recovery claims.

## Direct memory scheduling

**Raw user prompt**

> A legal task graph has several possible execution orders. Transfers, rematerialization, mapping, and reclamation can overlap some compute, but the current order creates stalls and a high memory peak. Build an execution plan.

**Expected primary skill:** `gpu-memory-scheduling`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-resource-lifetime-allocation`, `gpu-memory-tiering-migration`, `gpu-compiler-runtime`, `gpu-optimization-validation`.

**Must inspect:** dependency edges, readiness, critical path, overlap windows, staging lifetimes, transfer and compute contention, barrier placement, queue capacity, tail latency, starvation, and deadlock risks.

**Forbidden assumptions:** every topological order is performance-equivalent; nominal overlap means physical overlap; more concurrency is always better; early prefetch cannot raise peak memory.

**Pass condition:** produce a dependency-correct schedule that quantifies exposed stalls, peak-memory effects, resource contention, and a fallback when runtime readiness differs from prediction.

## Free bytes are sufficient but allocation fails

**Raw user prompt**

> Monitoring says the device has enough aggregate free memory, yet a large aligned buffer cannot be allocated. Should I evict more state?

**Expected primary skill:** `gpu-virtual-memory-fragmentation`

**Allowed secondary skills:** `gpu-resource-lifetime-allocation`, `gpu-state-reuse-eviction`, `gpu-performance-evidence`.

**Must inspect:** largest allocatable extent, alignment, physical and virtual contiguity requirements, reserved versus committed bytes, and allocator free lists.

**Forbidden assumptions:** more logical eviction is required; aggregate free bytes satisfy the request; the failed request requires physical contiguity.

**Pass condition:** diagnose allocatability before recommending retention changes and state which evidence would distinguish fragmentation from true capacity exhaustion.

## Software indirection versus virtual contiguity

**Raw user prompt**

> A dynamically growing logical array can use a software block table or one contiguous virtual range backed on demand. Compare them for existing kernels and changing object sizes.

**Expected primary skill:** `gpu-virtual-memory-fragmentation`

**Allowed secondary skills:** `gpu-resource-lifetime-allocation`, `gpu-compiler-runtime`, `gpu-kernel-execution`, `gpu-optimization-validation`.

**Must inspect:** kernel address assumptions, indirection frequency, mapping latency, page size, translation behavior, reservation limits, growth prediction, and fallback support.

**Forbidden assumptions:** either design is universally superior; virtual contiguity implies physical contiguity; software indirection has negligible kernel cost.

**Pass condition:** compare both designs across mapping overhead, kernel compatibility, fragmentation, address stability, and portability, then leave the result conditional on measured workload traits.

## Reject an unhideable offload

**Raw user prompt**

> A large value could be offloaded after use and fetched before its next consumer, but the inactive interval is shorter than the measured round trip and the consumer is on the critical path. Should we still offload it?

**Expected primary skill:** `gpu-memory-tiering-migration`

**Allowed secondary skills:** `gpu-memory-scheduling`, `gpu-resource-lifetime-allocation`, `gpu-performance-evidence`.

**Must inspect:** inactive interval, transfer latency distribution, bandwidth contention, critical-path slack, memory relief, and reconstruction alternative.

**Forbidden assumptions:** asynchronous transfer is hidden; capacity relief automatically justifies latency; peak bandwidth predicts completion time.

**Pass condition:** reject or tightly guard the offload unless another schedule, tier, compression, or rematerialization option creates sufficient measured slack.

## Unpredictable access defeats proactive migration

**Raw user prompt**

> Resource accesses depend on data discovered during execution. A predictor often prefetches the wrong resources and evicts soon-needed ones. Improve residency behavior.

**Expected primary skill:** `gpu-memory-tiering-migration`

**Allowed secondary skills:** `gpu-memory-scheduling`, `gpu-state-reuse-eviction`, `gpu-performance-evidence`.

**Must inspect:** predictor precision and recall, miss penalty, wasted bytes, eviction regret, demand fallback, hysteresis, and thrashing rate.

**Forbidden assumptions:** proactive migration remains beneficial; the last access predicts the next one; larger prefetch depth is safer.

**Pass condition:** quantify prediction failure and compare conservative admission, demand-driven fallback, bounded speculation, or no migration.

## Mutation epoch invalidates reuse

**Raw user prompt**

> Two state objects have matching shapes and content-derived keys, but one was mutated after the key was computed. A lookup returns the stale object. Define the fix and the proof obligation.

**Expected primary skill:** `gpu-state-reuse-eviction`

**Allowed secondary skills:** `gpu-persistent-state`, `gpu-numerical-safety`, `gpu-optimization-validation`.

**Must inspect:** mutation epoch, key construction, invalidation propagation, alias ownership, in-flight readers, and stale-hit observability.

**Forbidden assumptions:** shape and old content key remain sufficient; a cache hit is harmless; copying the pointer creates isolation.

**Pass condition:** add epoch-aware validity or immutable versioning and require a stale-state correctness test before measuring performance.

## Cross-owner state contamination

**Raw user prompt**

> A shared state pool improves hit rate, but objects from different owners can have identical computation keys while isolation rules prohibit sharing. Optimize safely.

**Expected primary skill:** `gpu-state-reuse-eviction`

**Allowed secondary skills:** `gpu-persistent-state`, `gpu-optimization-validation`.

**Must inspect:** owner identity, isolation domain, key namespace, cleanup, observability, and copy-on-write boundaries.

**Forbidden assumptions:** identical computation keys authorize sharing; higher hit rate is the target metric; logical sharing and physical deduplication have the same safety contract.

**Pass condition:** include the isolation domain in validity or disable cross-owner reuse and report the performance cost separately from correctness.

## Append-growing and fixed-size mutable state diverge

**Raw user prompt**

> One cross-step state appends history and preserves old regions. Another keeps a fixed footprint and overwrites its entire value each step. Can one allocator and checkpoint policy manage both?

**Expected primary skill:** `gpu-persistent-state`

**Allowed secondary skills:** `gpu-resource-lifetime-allocation`, `gpu-state-reuse-eviction`, `gpu-virtual-memory-fragmentation`.

**Must inspect:** growth law, update granularity, historical reuse, snapshot semantics, address stability, and reconstruction path.

**Forbidden assumptions:** both states share a page-growth policy; overwritten versions remain reusable; fixed footprint means fixed identity.

**Pass condition:** derive separate state contracts and justify any shared allocator mechanism independently of checkpoint and identity policy.

## Placement policy versus movement order

**Raw user prompt**

> We know which objects should reside on each memory tier, but transfers still block compute because they start too late and compete on one link. Which specialist owns the next decision?

**Expected primary skill:** `gpu-memory-scheduling`

**Allowed secondary skills:** `gpu-memory-tiering-migration`, `gpu-performance-evidence`, `gpu-compiler-runtime`.

**Must inspect:** fixed placement decisions, transfer dependency edges, link contention, start times, readiness, and critical-path slack.

**Forbidden assumptions:** changing placement is the only remedy; asynchronous queues guarantee overlap; link bandwidth is independent across transfers.

**Pass condition:** keep tier choice as an input and optimize movement order, overlap, and contention through the scheduling specialist.

## Logical eviction versus physical residency eviction

**Raw user prompt**

> A retained state remains valuable for future reuse but cannot stay in device memory. Should it be deleted from the logical cache or moved to another tier?

**Expected primary skill:** `gpu-state-reuse-eviction`

**Allowed secondary skills:** `gpu-memory-tiering-migration`, `gpu-memory-scheduling`, `gpu-performance-evidence`.

**Must inspect:** future saved work, logical retention value, lower-tier footprint, restore cost, lookup semantics, and device residency pressure.

**Forbidden assumptions:** device eviction means logical deletion; logical retention requires device residency; a lower-tier copy always has positive value.

**Pass condition:** decide logical retention first, then delegate physical placement and movement timing without conflating the two evictions.

## Local materialization remains a fusion task

**Raw user prompt**

> One kernel writes a full-size temporary that the next kernel immediately reads for a cheap transform. The object does not survive the pipeline and no allocator or cross-call policy is involved.

**Expected primary skill:** `gpu-memory-fusion-layout`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-kernel-execution`, `gpu-numerical-safety`, `gpu-optimization-validation`.

**Must inspect:** producer-consumer bytes, fusion legality, register and local-memory pressure, layout, and numerical ordering.

**Forbidden assumptions:** the new lifetime specialist should own every temporary; fusion must win; source adjacency proves one generated kernel.

**Pass condition:** retain the existing local fusion route and add a new memory-management skill only if cross-graph lifetime, backing, placement, reuse, state semantics, or movement order becomes material.

## Algorithm-local streaming state remains a reduction task

**Raw user prompt**

> A chunked scan carries a compact value from one chunk to the next within one invocation. Verify boundaries and optimize the algorithm.

**Expected primary skill:** `gpu-reductions-scans`

**Allowed secondary skills:** `gpu-numerical-safety`, `gpu-kernel-execution`, `gpu-performance-evidence`, `gpu-optimization-validation`.

**Must inspect:** inclusive or exclusive semantics, chunk boundaries, carry initialization, partial tiles, reduction order, and synchronization.

**Forbidden assumptions:** all state crossing a kernel boundary is persistent state; state reuse or tiering is required.

**Pass condition:** keep the route in the algorithm specialist unless the state survives independent invocations or gains an external owner and retention scope.

## Address stability for graph replay remains a runtime task

**Raw user prompt**

> A captured execution fails on replay because a buffer address changes between runs. Diagnose capture requirements and runtime allocation behavior.

**Expected primary skill:** `gpu-compiler-runtime`

**Allowed secondary skills:** `gpu-virtual-memory-fragmentation`, `gpu-resource-lifetime-allocation`, `gpu-performance-evidence`.

**Must inspect:** capture contract, replay address requirements, allocator behavior, pool lifetime, synchronization, and recapture conditions.

**Forbidden assumptions:** virtual memory policy is necessarily primary; every address can be stabilized without recapture; capture success proves semantic correctness.

**Pass condition:** diagnose the compiler/runtime replay mechanism first and hand off only the backing or lifetime policy that the mechanism exposes.

## Missing baseline remains an evidence task

**Raw user prompt**

> An end-to-end GPU workload is slow, but there is no baseline, timeline, allocation trace, or ranked hotspot. Establish evidence before proposing a change.

**Expected primary skill:** `gpu-performance-evidence`

**Allowed secondary skills:** a measured specialist only after the first evidence pass identifies its trigger.

**Must inspect:** target metric, environment, workload matrix, end-to-end time, timeline, hot operations, transfers, allocation and memory peaks, variance, and measurement protocol.

**Forbidden assumptions:** the visible source pattern is the bottleneck; a kernel must be optimized before profiling; one timing sample proves a result.

**Pass condition:** retain evidence as primary until the bottleneck is classified and route only the measured next decision.

## Floating-point reordering remains a numerical-safety task

**Raw user prompt**

> Review a parallel rewrite that changes a floating-point accumulation tree and may change NaN propagation. Classify correctness risk and design tolerances before performance work.

**Expected primary skill:** `gpu-numerical-safety`

**Allowed secondary skills:** `gpu-reductions-scans`, `gpu-optimization-validation`.

**Must inspect:** semantic equivalence class, dtype, operation order, NaN and Inf behavior, determinism, error distribution, adversarial values, shapes, and fallback contract.

**Forbidden assumptions:** mathematical equivalence implies bitwise identity; one all-close check defines safety; faster execution justifies an unspecified semantic change.

**Pass condition:** preserve numerical safety as primary and require a classified contract before any optimization claim.

## A measured hot kernel remains an execution task

**Raw user prompt**

> Profiling proves one custom kernel dominates runtime and is limited by uncoalesced global loads, register spills, and synchronization. Tune the kernel execution itself.

**Expected primary skill:** `gpu-kernel-execution`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-numerical-safety`, `gpu-optimization-validation`.

**Must inspect:** access coalescing, mapping, register and local-memory pressure, spills, occupancy constraints, synchronization, generated code, isolated time, and end-to-end contribution.

**Forbidden assumptions:** a new resource-management specialist owns every memory access issue; higher occupancy always wins; source-level intent proves generated behavior.

**Pass condition:** keep the measured kernel bottleneck in execution tuning unless evidence moves the dominant cost to another layer.

## Training-wide behavior remains an autodiff task

**Raw user prompt**

> A change makes forward faster, but gradients, saved values, optimizer time, communication overlap, and full iteration performance still need evaluation.

**Expected primary skill:** `gpu-training-autodiff`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-numerical-safety`, `gpu-resource-lifetime-allocation`, `gpu-memory-scheduling`, `gpu-optimization-validation` when their triggers apply.

**Must inspect:** forward and backward correctness, saved values, recomputation legality, optimizer behavior, gradient communication, peak memory, full iteration time, and training-mode matrix.

**Forbidden assumptions:** forward speedup proves training speedup; generic lifetime planning can define gradient semantics; reduced saved bytes imply a lower full-step peak.

**Pass condition:** keep training semantics and full-step acceptance primary while delegating only generic lifetime or scheduling subproblems.

## Final keep-or-reject remains a validation task

**Raw user prompt**

> A completed GPU optimization patch claims a speedup. Define representative benchmarks, guards, fallbacks, failure cases, and the final keep-or-reject record.

**Expected primary skill:** `gpu-optimization-validation`

**Allowed secondary skills:** `gpu-performance-evidence`, `gpu-numerical-safety`, `gpu-training-autodiff`, or one resource specialist only when its acceptance fields apply.

**Must inspect:** target metric, baseline, representative workload matrix, correctness class, guard domain, fallback, isolated and end-to-end measurements, uncertainty, regressions, and rejected alternatives.

**Forbidden assumptions:** one microbenchmark proves end-to-end value; a fast path needs no fallback; missing resource fields should be forced onto unrelated kernel changes.

**Pass condition:** keep final acceptance in validation and include only conditionally applicable specialist records.

## Rendering pipeline is outside scope

**Raw user prompt**

> Optimize rasterization, visibility, shading stages, blending, and frame presentation for a real-time renderer.

**Expected primary skill:** none from this suite unless the request is narrowed to a general compute or resource-state subproblem.

**Allowed secondary skills:** none by default.

**Must inspect:** whether the user has identified an independent allocation, residency, migration, state, scheduling, or compute-kernel issue that can be handled without rendering-specific guidance.

**Forbidden assumptions:** this suite covers shader-stage design, rasterization, ray traversal, visual quality, or frame-presentation policy.

**Pass condition:** state the rendering-pipeline non-goal and offer to analyze only a clearly isolated, transferable compute or resource-state problem.

## Evaluation acceptance

Accept the suite only when:

- every direct case selects its expected primary specialist;
- secondary specialists appear only with an explicit trigger;
- every cross-domain case preserves the stated boundary;
- the agent requests the listed evidence before claiming a policy is beneficial;
- the agent names at least one rejection condition for each proposed policy;
- application-specific examples do not leak into the generic skill bodies;
- existing evidence, numerical, fusion, kernel, compiler/runtime, reduction, training, and validation routes remain primary for their established domains.
