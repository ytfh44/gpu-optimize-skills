# GPU Code Optimizer Skill Suite

A decomposed Agent Skills suite for evidence-driven GPU performance optimization.

Start with `gpu-code-optimizer`. It routes tasks to specialist skills while keeping each activated skill focused.

## Skills

1. `gpu-code-optimizer` — parent/orchestrator and routing.
2. `gpu-performance-evidence` — baselines, profiling, roofline, bottleneck classification.
3. `gpu-numerical-safety` — semantic classes, numerical error, guards and fallbacks.
4. `gpu-memory-fusion-layout` — materialization, fusion, memory traffic, layout.
5. `gpu-kernel-execution` — mapping, tiling, resources, synchronization, matrix units.
6. `gpu-compiler-runtime` — framework compilers, graphs, launch/runtime overhead, transfers, multi-GPU.
7. `gpu-reductions-scans` — reductions, scans, prefix/recurrence, streaming state.
8. `gpu-training-autodiff` — backward pass, saved tensors, recomputation, gradients.
9. `gpu-optimization-validation` — benchmark protocol, acceptance gates, failure records.

Each directory under `skills/` is a standalone skill containing a `SKILL.md` file with YAML frontmatter (`name` and `description`). The layout follows the `skills/<name>/SKILL.md` convention recognized by the [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI.

## Install

```bash
# List skills in this repository without installing
npx skills add <owner>/<repo> --list

# Install a single skill
npx skills add <owner>/<repo> --skill gpu-code-optimizer

# Install every skill in the suite
npx skills add <owner>/<repo> --skill '*'
```

Replace `<owner>/<repo>` with this repository's GitHub path. Project-scoped installs land in `./<agent>/skills/`; pass `-g` for a global install.

## Reporting Misleading Guidance

If any skill in this suite misleads a task — for example by routing to the wrong specialist, asserting the wrong optimization class (C1–C4), misclassifying a bottleneck, omitting a numerical hazard, or producing evidence that does not match the actual hardware or compiler behavior — please open a GitHub Issue on this repository so it can be fixed.

To make the issue actionable, include:

- The skill name (e.g. `gpu-kernel-execution`) and the section heading that misled the task.
- The exact input or code under analysis, plus the target GPU, framework, dtype, shape, and layout.
- What the skill instructed the agent to do or conclude.
- What the correct guidance should be, backed by a profiler trace, compiler IR, hardware counter, specification, or reference paper.
- Whether the misleading instruction caused a correctness regression, a performance regression, or only a wasted optimization step.

Reported issues wait for the maintainer's fix. Once a fix lands, run `npx skills update` to pull the corrected `SKILL.md`.
