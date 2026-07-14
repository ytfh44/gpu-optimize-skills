# Research Foundations

This maintainer index records the research mechanisms, generalizations, and counterexamples that informed the skill suite. It is not runtime guidance and no `SKILL.md` should load or link to it.

## Contents

- [Provenance policy](#provenance-policy)
- [Existing optimization skills](#existing-optimization-skills)
- [Resource lifetime and allocation](#resource-lifetime-and-allocation)
- [Virtual memory and fragmentation](#virtual-memory-and-fragmentation)
- [Tiering and memory scheduling](#tiering-and-memory-scheduling)
- [Reuse, eviction, and heterogeneous state](#reuse-eviction-and-heterogeneous-state)
- [Transferable resource-management work from graphics](#transferable-resource-management-work-from-graphics)
- [Maintainer synthesis](#maintainer-synthesis)

## Provenance policy

These mappings describe an intellectual lineage and a source of counterexamples. They do not claim priority. Similar patterns may predate these papers in operating systems, compilers, databases, high-performance computing, graphics systems, storage systems, or production runtimes.

Use the labels consistently:

- **Direct adaptation** means the repository preserves the source mechanism's central structure within a similar decision problem.
- **Generalization** means the repository removes an application, operator, model, framework, or hardware restriction and retains only a conditional systems principle.
- **Counterexample** means the source prevents one attractive policy from being stated as universal.

Do not copy application-specific data structures, names, performance numbers, or hardware assumptions into a generic skill. Preserve mechanisms, decision variables, evidence requirements, and rejection conditions.

## Existing optimization skills

### CODA: Rewriting Transformer Blocks as GEMM-Epilogue Programs

- **Primary paper:** [CODA: Rewriting Transformer Blocks as GEMM-Epilogue Programs](https://arxiv.org/abs/2605.19269), current arXiv version.
- **Concrete mechanism:** Keep an expert-designed GEMM mainloop fixed, expose composable epilogue primitives, and execute surrounding memory-bound work while output tiles remain on chip. The paper covers forward and backward paths and avoids repeated global-memory materialization around dense linear algebra.
- **General principle:** Find an expensive operation that already owns the useful data lifetime, then attach cheap compatible work before the data leaves fast storage.
- **Skill mapping:** `gpu-code-optimizer` anchor-first priority; `gpu-performance-evidence` anchor and data-lifetime audit; `gpu-memory-fusion-layout` producer epilogue and full-buffer elimination; `gpu-reductions-scans` tile-local partials and compact state; `gpu-training-autodiff` joint forward/backward observation.
- **Do not generalize:** The paper directly supports GEMM-centered epilogues in standard Transformer blocks. It does not directly establish arbitrary anchors, consumer prologues, non-Transformer workloads, or every accelerator backend.
- **Counterpoint or failure condition:** Added epilogue work can damage the mainloop through resource pressure, synchronization, or unsupported semantics. A source-level fusion proposal does not prove the intended generated kernel.
- **Classification:** Direct adaptation for GEMM epilogues and compact tile partials; generalization for arbitrary anchors, consumer prologues, and broader workloads.

## Resource lifetime and allocation

### SuperNeurons: Dynamic GPU Memory Management for Training Deep Neural Networks

- **Primary paper:** [SuperNeurons: Dynamic GPU Memory Management for Training Deep Neural Networks](https://arxiv.org/abs/1801.04380), PPoPP 2018.
- **Concrete mechanism:** Combine liveness analysis, a unified tensor pool, cost-aware recomputation, and dynamic workspace allocation to reduce peak device memory.
- **General principle:** Treat liveness, allocation reuse, reconstruction, and workspace capacity as one plan rather than independent allocator tricks.
- **Skill mapping:** `gpu-resource-lifetime-allocation` resource inventory, live intervals, pooling, workspace planning, and reconstruction alternatives; `gpu-memory-scheduling` movement and recomputation placement.
- **Do not generalize:** Layer-structured training traces do not represent irregular task graphs, persistent cross-request state, or unpredictable consumers.
- **Counterpoint or failure condition:** A shared pool can retain excessive capacity, and recomputation can lose when its cost or state dependencies are mischaracterized.
- **Classification:** Generalization.

### Checkmate: Breaking the Memory Wall with Optimal Tensor Rematerialization

- **Primary paper:** [Checkmate: Breaking the Memory Wall with Optimal Tensor Rematerialization](https://arxiv.org/abs/1910.02653), MLSys 2020.
- **Concrete mechanism:** Formalize memory-constrained rematerialization over a computation graph and solve schedules with profile-based hardware costs.
- **General principle:** Compare retention, release, and reconstruction under an explicit dependency graph, memory budget, and execution-cost model.
- **Skill mapping:** `gpu-resource-lifetime-allocation` rematerialization decision; `gpu-memory-scheduling` dependency-correct placement of reconstruction; `gpu-optimization-validation` cost-model validation.
- **Do not generalize:** An optimizer's schedule is only as accurate as its graph, state semantics, determinism assumptions, and cost profile.
- **Counterpoint or failure condition:** Dynamic control flow, stochastic operations, mutable state, or profile drift can invalidate a static rematerialization plan.
- **Classification:** Direct adaptation of the decision formulation; generalization beyond training tensors.

### Coop: Memory is not a Commodity

- **Primary paper:** [Coop: Memory is not a Commodity](https://arxiv.org/abs/2311.00591), current arXiv version.
- **Concrete mechanism:** Co-optimize allocation and rematerialization because freeing discontiguous objects may not create the address range needed by a new allocation.
- **General principle:** Capacity and allocatability differ; memory has address, extent, alignment, and placement structure.
- **Skill mapping:** `gpu-resource-lifetime-allocation` interference and placement awareness; `gpu-virtual-memory-fragmentation` largest extent and free-space geometry; the handoff between those skills.
- **Do not generalize:** Contiguous eviction windows and tensor partitioning are policy choices, not universal remedies.
- **Counterpoint or failure condition:** Physical or virtual remapping may remove an extent constraint, while excessive co-optimization can add planner and runtime overhead.
- **Classification:** Direct adaptation of capacity-versus-allocatability; counterexample to byte-only memory accounting.

## Virtual memory and fragmentation

### Efficient Memory Management for Large Language Model Serving with PagedAttention

- **Primary paper:** [Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180), SOSP 2023.
- **Concrete mechanism:** Represent a dynamically growing logical sequence with fixed-size noncontiguous physical blocks and a software block table; share eligible blocks to reduce duplication.
- **General principle:** A logical resource need not have one physically contiguous allocation, and growth should not require reserving the maximum possible physical size.
- **Skill mapping:** `gpu-virtual-memory-fragmentation` software indirection, block granularity, and physical backing; `gpu-persistent-state` append-growing state; `gpu-state-reuse-eviction` sharing and copy-on-write contracts.
- **Do not generalize:** A block table is not automatically appropriate for arbitrary kernels, mutation models, or address-stability contracts.
- **Counterpoint or failure condition:** Indirection changes kernel interfaces and access costs; coarse blocks waste space while fine blocks increase metadata and lookup overhead.
- **Classification:** Direct adaptation of logical-to-physical decoupling; generalization beyond one cache type.

### vAttention: Dynamic Memory Management for Serving LLMs without PagedAttention

- **Primary paper:** [vAttention: Dynamic Memory Management for Serving LLMs without PagedAttention](https://arxiv.org/abs/2405.04437), ASPLOS 2025 version.
- **Concrete mechanism:** Reserve contiguous virtual ranges and add physical backing on demand through GPU virtual-memory APIs, preserving compatibility with kernels that expect virtual contiguity.
- **General principle:** Virtual contiguity and physical contiguity are separate decisions; address abstraction can isolate memory management from compute kernels.
- **Skill mapping:** `gpu-virtual-memory-fragmentation` virtual reservation, delayed commitment, mapping latency, page granularity, and kernel compatibility; `gpu-compiler-runtime` concrete API and capture constraints.
- **Do not generalize:** Large virtual reservations, page operations, address-space limits, and vendor API behavior remain platform-dependent.
- **Counterpoint or failure condition:** Mapping latency, coarse pages, translation behavior, and address-space pressure can outweigh compatibility benefits.
- **Classification:** Counterexample to default software paging; direct adaptation of virtual/physical decoupling.

### GMLake: Efficient and Transparent GPU Memory Defragmentation for Large-scale DNN Training with Virtual Memory Stitching

- **Primary paper:** [GMLake: Efficient and Transparent GPU Memory Defragmentation for Large-scale DNN Training with Virtual Memory Stitching](https://arxiv.org/abs/2401.08156), ASPLOS 2024.
- **Concrete mechanism:** Use low-level virtual-memory mappings to stitch noncontiguous physical blocks into a virtually contiguous allocation and avoid splitting-based caching-allocator fragmentation.
- **General principle:** Reconstruct logical extents with virtual mappings when physical free space exists but is poorly shaped.
- **Skill mapping:** `gpu-virtual-memory-fragmentation` stitching, allocator trace analysis, committed versus reserved memory, and transparent backing.
- **Do not generalize:** Stitching does not remove page-granularity waste, mapping cost, or platform constraints, and it does not solve excessive live memory.
- **Counterpoint or failure condition:** A lifetime plan or a simpler pool may outperform remapping for regular traces; virtual stitching cannot repair true capacity exhaustion.
- **Classification:** Direct adaptation.

### vTensor: Flexible Virtual Tensor Management for Efficient LLM Serving

- **Primary paper:** [vTensor: Flexible Virtual Tensor Management for Efficient LLM Serving](https://arxiv.org/abs/2407.15309), current arXiv version.
- **Concrete mechanism:** Expose a virtual tensor abstraction that decouples computation kernels from dynamic physical-memory management and extension.
- **General principle:** Keep compute interfaces stable when backing policy can be implemented below the logical resource abstraction.
- **Skill mapping:** `gpu-virtual-memory-fragmentation` backing abstraction and kernel compatibility; `gpu-compiler-runtime` interface and runtime integration boundary.
- **Do not generalize:** Transparent virtual objects are not free and may not represent irregular sparse access, remote tiers, or mutable sharing safely.
- **Counterpoint or failure condition:** Abstraction hides costs only from source code, not from mapping latency, translation, synchronization, or capacity accounting.
- **Classification:** Generalization and architectural counterexample to kernel-coupled paging.

## Tiering and memory scheduling

### G10: Enabling an Efficient Unified GPU Memory and Storage Architecture with Smart Tensor Migrations

- **Primary paper:** [G10: Enabling an Efficient Unified GPU Memory and Storage Architecture with Smart Tensor Migrations](https://arxiv.org/abs/2310.09443), MICRO 2023.
- **Concrete mechanism:** Characterize predictable resource behavior with compiler information, place data across GPU, host, and flash memory, and schedule migration ahead of use under bandwidth constraints.
- **General principle:** Predictable future use enables proactive residency changes, but the migration plan must include every tier's capacity, latency, bandwidth, and overlap limits.
- **Skill mapping:** `gpu-memory-tiering-migration` tier model, residency transitions, and traffic budget; `gpu-memory-scheduling` advance movement and overlap windows.
- **Do not generalize:** Regular static traces do not justify proactive migration for data-dependent or adversarial access patterns.
- **Counterpoint or failure condition:** Prediction error, bandwidth contention, and changed schedules can expose transfer stalls or create thrashing.
- **Classification:** Direct adaptation of predictive migration; counterexample boundary for unpredictable access.

### TURNIP: A Nondeterministic GPU Runtime with CPU RAM Offload

- **Primary paper:** [TURNIP: A "Nondeterministic" GPU Runtime with CPU RAM Offload](https://arxiv.org/abs/2405.16283), current arXiv version.
- **Concrete mechanism:** Compile compute and memory dependencies into a graph, then choose among ready operations at runtime as transfer completion events become known.
- **General principle:** A dataflow graph defines a partial order, not one fixed total order; runtime readiness can select work that avoids blocking on uncertain movement.
- **Skill mapping:** `gpu-memory-scheduling` dependency graph, readiness, event-driven ordering, starvation, and critical-path stalls; `gpu-memory-tiering-migration` offload feasibility.
- **Do not generalize:** Reordering is legal only when side effects, mutable state, communication, determinism, and resource constraints permit it.
- **Counterpoint or failure condition:** Additional concurrency can increase peak memory or contention, and no legal ready work may exist during a critical transfer.
- **Classification:** Direct adaptation of event-driven memory scheduling; counterexample to static overlap assumptions.

## Reuse, eviction, and heterogeneous state

### SGLang: Efficient Execution of Structured Language Model Programs

- **Primary paper:** [SGLang: Efficient Execution of Structured Language Model Programs](https://arxiv.org/abs/2312.07104), current arXiv version.
- **Concrete mechanism:** Organize reusable prefix state with a radix structure so content relationships drive sharing and reuse across executions.
- **General principle:** State identity and reusable substructure can be semantic rather than address-based; partial reuse requires an explicit structural contract.
- **Skill mapping:** `gpu-state-reuse-eviction` identity, prefix or sparse reuse, sharing, invalidation, and lookup cost; `gpu-persistent-state` retained immutable history.
- **Do not generalize:** Prefix structure, immutability, position semantics, and request behavior are application-specific.
- **Counterpoint or failure condition:** High hit rate can still lose when lookup, movement, memory footprint, or interference exceeds saved computation.
- **Classification:** Generalization.

### Marconi: Prefix Caching for the Era of Hybrid LLMs

- **Primary paper:** [Marconi: Prefix Caching for the Era of Hybrid LLMs](https://arxiv.org/abs/2411.19379), MLSys 2025 version.
- **Concrete mechanism:** Distinguish in-place recurrent state from append-oriented state and rank admission and eviction by reuse likelihood, saved computation, and memory footprint rather than recency alone.
- **General principle:** Classify state by mutation semantics before designing reuse, admission, or eviction; optimize value, not raw hit count.
- **Skill mapping:** `gpu-persistent-state` growth and mutation taxonomy; `gpu-state-reuse-eviction` value function, admission, and eviction.
- **Do not generalize:** Exact-match rules and hit scenarios arise from the paper's model structure and do not define every mutable state object.
- **Counterpoint or failure condition:** Forecasts can drift, mutable state can invalidate sharing, and retention may reduce throughput through memory interference.
- **Classification:** Direct adaptation of state-semantic classification and value-based retention; generalization beyond model state.

### Sparse Prefix Caching for Hybrid and Recurrent LLM Serving

- **Primary paper:** [Sparse Prefix Caching for Hybrid and Recurrent LLM Serving](https://arxiv.org/abs/2605.05219), arXiv v1.
- **Concrete mechanism:** Store exact recurrent states at selected checkpoints, resume from the deepest hit, and exactly recompute the missing suffix; optimize checkpoint placement under an overlap-depth distribution.
- **General principle:** Persistent state can trade checkpoint density against exact reconstruction cost, and optimal placement depends on the future reuse distribution.
- **Skill mapping:** `gpu-persistent-state` sparse checkpoints, snapshot restoration, and reconstruction; `gpu-state-reuse-eviction` admission value; `gpu-memory-scheduling` suffix reconstruction placement.
- **Do not generalize:** The result assumes state can be extracted and restored exactly and that future overlap resembles the modeled distribution.
- **Counterpoint or failure condition:** State mutation, restore incompatibility, prediction shift, or expensive suffix reconstruction can erase the benefit.
- **Classification:** Direct adaptation of sparse exact checkpointing; counterexample to both dense retention and no retention.

## Transferable resource-management work from graphics

Rendering-pipeline algorithms remain outside the suite. These sources contribute only general resource-lifetime, residency, working-set, and scheduling ideas.

### A Resource Allocation Algorithm for a History-Aware Frame Graph

- **Primary paper:** [A Resource Allocation Algorithm for a History-Aware Frame Graph](https://doi.org/10.24132/JWSCG.2023.7), Journal of WSCG 2023.
- **Concrete mechanism:** Derive transient and history-resource lifetimes from a pass graph and reuse physical storage for resources with nonoverlapping intervals.
- **General principle:** Place resources in a time-by-address plan; lifetime overlap and alignment determine safe aliasing.
- **Skill mapping:** `gpu-resource-lifetime-allocation` first/last use, transient aliasing, history-state boundary, and peak overlap.
- **Do not generalize:** Frame cadence, graphics resource states, and rendering API constraints are not part of the compute suite.
- **Counterpoint or failure condition:** Dynamic passes, asynchronous consumers, escaped handles, and cross-invocation history can invalidate a static alias plan.
- **Classification:** Generalization.

### GPU Cache Flush Minimization in Render Graph Systems

- **Primary paper:** [GPU Cache Flush Minimization in Render Graph Systems](https://doi.org/10.24132/JWSCG.2024.8), Journal of WSCG 2024.
- **Concrete mechanism:** Select among legal pass orders to reduce barriers, render-pass breaks, and cache flush or invalidation costs.
- **General principle:** Different topological orders of the same dependency graph can produce different memory-system costs.
- **Skill mapping:** `gpu-memory-scheduling` legal reordering, barrier cost, resource transitions, and partial-order optimization.
- **Do not generalize:** Rendering pass semantics and tile-renderer behavior do not define general GPU compute queues.
- **Counterpoint or failure condition:** Fewer transitions can worsen parallelism, peak memory, or the critical path; legality must include all side effects.
- **Classification:** Generalization.

### Residency Octree: A Hybrid Approach for Scalable Web-Based Multi-Volume Rendering

- **Primary paper:** [Residency Octree: A Hybrid Approach for Scalable Web-Based Multi-Volume Rendering](https://arxiv.org/abs/2309.04393), VIS 2023.
- **Concrete mechanism:** Separate a resolution-independent spatial hierarchy from cached multi-resolution bricks so missing high-resolution data can use an available lower-resolution representation.
- **General principle:** Residency, identity, and representation quality can be separate axes when the semantic contract permits alternatives.
- **Skill mapping:** `gpu-memory-tiering-migration` working-set residency and miss handling; `gpu-persistent-state` representation contract; `gpu-numerical-safety` whenever substitution changes results.
- **Do not generalize:** Approximate fallback is not acceptable for exact numerical computation unless the user explicitly approves changed semantics.
- **Counterpoint or failure condition:** A lower-quality resident substitute may violate correctness, and hierarchy traversal can cost more than the avoided movement.
- **Classification:** Counterexample and guarded generalization.

### Virtual Memory for 3D Gaussian Splatting

- **Primary paper:** [Virtual Memory for 3D Gaussian Splatting](https://arxiv.org/abs/2506.19415), arXiv v1.
- **Concrete mechanism:** Identify a view-dependent working set, page scene data, and stream only required pages to the GPU in time for use.
- **General principle:** Treat high-bandwidth device memory as a managed working-set cache when demand can be predicted and bounded.
- **Skill mapping:** `gpu-memory-tiering-migration` working-set prediction, residency, streaming, and incremental changes; `gpu-memory-scheduling` just-in-time prefetch.
- **Do not generalize:** Visibility, camera coherence, level of detail, and visual quality are rendering-specific predictors and policies.
- **Counterpoint or failure condition:** Unpredictable access, transfer spikes, or inaccurate working-set selection can cause misses and tail-latency failures.
- **Classification:** Generalization and counterexample to demand-fault-only migration.

## Maintainer synthesis

The papers support six generic decision questions:

| Question | Primary skill | Evidence that prevents overgeneralization |
|---|---|---|
| When must the object exist? | `gpu-resource-lifetime-allocation` | Live intervals, consumers, reconstruction cost, and peak overlap |
| How does the logical object obtain physical backing? | `gpu-virtual-memory-fragmentation` | Extent geometry, page granularity, mapping cost, and kernel compatibility |
| Where should the object reside? | `gpu-memory-tiering-migration` | Tier topology, working set, transfer budget, and prediction error |
| Is the logical state worth retaining and sharing? | `gpu-state-reuse-eviction` | Identity, validity, saved work, footprint, lookup, movement, and interference |
| What mutation and ownership contract defines the state? | `gpu-persistent-state` | Growth law, epochs, snapshots, branches, reconstruction, and cleanup |
| When should compute and memory actions run? | `gpu-memory-scheduling` | Dependency graph, critical path, readiness, overlap, contention, and tail stalls |

No source supports default paging, default offload, default recency eviction, default reuse, default proactive migration, or default overlap. Each source contributes a mechanism whose benefit depends on an explicit workload and cost model.
