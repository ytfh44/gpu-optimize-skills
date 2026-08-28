# GPU Code Optimizer Skill Suite

A decomposed Agent Skills suite for evidence-driven GPU compute, resource, and runtime-state optimization.

Start with `gpu-code-optimizer`. It routes tasks to specialist skills while keeping each activated skill focused.

The suite targets GPU compute and transferable resource/state-management problems. Graphics rendering pipelines are a non-goal: it does not cover rasterization, shader-stage design, ray tracing, visibility, blending, frame presentation, or visual-quality policy.

## Skills

1. `gpu-code-optimizer` — parent/orchestrator and routing.
2. `gpu-performance-evidence` — baselines, profiling, roofline, bottleneck classification.
3. `gpu-numerical-safety` — semantic classes, numerical error, guards and fallbacks.
4. `gpu-memory-fusion-layout` — materialization, fusion, memory traffic, layout.
5. `gpu-resource-lifetime-allocation` — liveness, peak overlap, transient aliasing, pooling, workspace, rematerialization.
6. `gpu-virtual-memory-fragmentation` — allocatability, fragmentation, VMM, indirection, page granularity, compaction.
7. `gpu-memory-tiering-migration` — placement, residency, prefetch, offload, replication, migration.
8. `gpu-state-reuse-eviction` — identity, validity, sharing, admission, retention, invalidation, logical eviction.
9. `gpu-persistent-state` — cross-call growth, mutation, ownership, snapshots, branches, checkpoints, cleanup.
10. `gpu-memory-scheduling` — dependency-aware timing of compute, movement, rematerialization, barriers, and reclamation.
11. `gpu-kernel-execution` — mapping, tiling, resources, synchronization, matrix units.
12. `gpu-compiler-runtime` — framework compilers, graphs, launch/runtime mechanisms, transfers, multi-GPU.
13. `gpu-reductions-scans` — reductions, scans, prefix/recurrence, algorithm-local streaming state.
14. `gpu-training-autodiff` — backward pass, saved tensors, recomputation, gradients.
15. `gpu-optimization-validation` — benchmark protocol, acceptance gates, failure records.

Each directory under `skills/` is a standalone skill containing a `SKILL.md` file with YAML frontmatter (`name` and `description`). The layout follows the `skills/<name>/SKILL.md` convention recognized by the [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI.

## Install

```bash
# Run these commands from a local checkout at an immutable, reviewed commit.
# Pin the CLI package to a reviewed version as well.

# List skills in the checked-out repository without installing
npx --yes skills@<cli-version> add . --list

# Install a single skill
npx --yes skills@<cli-version> add . --skill gpu-code-optimizer

# Install every skill in the suite
npx --yes skills@<cli-version> add . --skill '*'
```

Replace `<cli-version>` with an explicitly reviewed package version. Review the checked-out `SKILL.md` files before wildcard installation; advance the repository commit and CLI version deliberately rather than following a mutable source. Project-scoped installs land in `./<agent>/skills/`; pass `-g` for a global install.

## Maintainer resources

- [Research foundations](references/research-foundations.md) records source mechanisms, generalizations, counterexamples, and limits. Skill bodies intentionally do not load it.
- [Memory-management routing evaluations](evals/memory-management-routing.md) defines positive, boundary, and regression cases for fresh-context testing.
- [Optimization-search autonomy evaluations](evals/optimization-search-autonomy.md) tests hypothesis portfolios, causal probes, mapping reconstruction, scoped negative results, and composition revalidation without requiring named techniques.

## Maintainer checks

Run the document-contract tests with `python -m unittest discover -s tests -v`. The fresh-context evaluations remain behavior tests: give an agent only the raw prompt and the parent Skill, then grade the reasoning contract described in the evaluation file.

## Reporting Misleading Guidance

If any skill in this suite misleads a task — for example by routing to the wrong specialist, asserting the wrong optimization class (C1–C4), misclassifying a bottleneck, omitting a numerical hazard, or producing evidence that does not match the actual hardware or compiler behavior — please open a GitHub Issue on this repository so it can be fixed.

To make the issue actionable, include:

- The skill name (e.g. `gpu-kernel-execution`) and the section heading that misled the task.
- The exact input or code under analysis, plus the target GPU, framework, dtype, shape, and layout.
- What the skill instructed the agent to do or conclude.
- What the correct guidance should be, backed by a profiler trace, compiler IR, hardware counter, specification, or reference paper.
- Whether the misleading instruction caused a correctness regression, a performance regression, or only a wasted optimization step.

Reported issues wait for the maintainer's fix. Once a fix lands, review it, advance the pinned repository commit deliberately, rerun validation, and reinstall from that checked-out revision.
