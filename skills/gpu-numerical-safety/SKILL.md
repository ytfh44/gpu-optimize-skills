---
name: gpu-numerical-safety
description: Load this skill and follow it when optimizing GPU code that may change floating-point evaluation order, precision, boundary behavior, NaN or Inf propagation, determinism, or other program semantics.
---

# GPU Numerical Safety

## Skill navigation
- Parent/orchestrator: [gpu-code-optimizer](../gpu-code-optimizer/SKILL.md)
- [gpu-performance-evidence](../gpu-performance-evidence/SKILL.md) — load to measure the performance benefit independently of correctness
- [gpu-reductions-scans](../gpu-reductions-scans/SKILL.md) — load for reduction trees, scans, prefix operations, and recurrence boundaries
- [gpu-training-autodiff](../gpu-training-autodiff/SKILL.md) — load when gradients, saved tensors, or mixed precision are involved
- [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) — load for acceptance gates and failure-case reporting

Load linked skills only when their trigger applies. Do not duplicate their full workflow here.

## Core rule

An optimization is not safe because the algebra is equivalent over real numbers. GPU optimizations frequently change evaluation order, contraction, precision, masking order, synchronization, aliasing, and boundary behavior. Classify the semantic risk before promoting a fast path.

## Optimization classification

Every optimization carries two independent layers: a **numerical class** (how far the numeric/mathematical semantics deviate from the reference) and, when material, **semantic/runtime flags** (orthogonal risks that are not about numeric deviation). The numerical class answers "how does the new implementation's numeric/mathematical semantics differ from the reference?"; the flags answer "what else about program behavior changed?" A single numerical class is no longer sufficient on its own — non-numeric risks must be recorded separately so they are not silently folded into C4.

### Numerical class

| Class | Name | Description |
|:------|:-----|:------------|
| **C1** | Strict semantic equivalent | Program semantics are unchanged and output is expected to be bitwise-identical against the reference. If compiler lowering, fusion, contraction, or instruction selection changes floating-point evaluation order, classify the change as C2 instead. |
| **C2** | Floating-order changed | Mathematically equivalent but floating-point accumulation order differs. May produce small numerical differences whose magnitude depends on dtype, reduction length, input scale, and conditioning. |
| **C3** | Approximate with tolerance | Introduces an explicit approximation (clipping, truncation, fast math, reduced precision). Must document the error characterization and the value range where it holds, separating: proven/specification bound (e.g. ULP guarantee), analytical bound (derived), empirical envelope (in-domain max/P99 from tests), and the uncovered domain where no guarantee applies. |
| **C4** | Semantics changed | Result-level program semantics differ from the reference (algorithm definition, boundary semantics, mask semantics, user-observable result, approximate objective, or model behavior). Requires explicit user approval. Never the default path. |
| **N/A** | No numeric/semantic deviation | The change alters memory backing, pooling, page mapping, stream scheduling, VMM, cache eviction, or allocation reuse without changing the computed result. Use N/A when no numeric class applies; express any non-numeric risk through flags instead. |

A change that does not alter the computed result (allocator/VMM/pooling/stream-scheduling) should be labeled **N/A**, not forced into C4.

C1 and N/A have disjoint domains: C1 applies only to a value-producing computational transformation expected bitwise-identical; N/A applies to changes outside numerical transformation (allocator/VMM/pooling/stream-scheduling). Label a runtime change C1 only if it is itself a compute transform; otherwise N/A. Do not double-label the same change.

Rules:

- **C3 and C4 optimizations must be opt-in fast paths**, not silent replacements of the original code. The original correct path must remain available as a fallback.
- **C2 optimizations may become the default** only when their error stays within the existing accepted tolerance, does not require relaxing tests, and shows no systematic drift or boundary-case regression. If a C2 change requires tolerance relaxation, it must be gated like a fast path and paired with the reference fallback.
- Any C2 or higher optimization **must** document the numerical difference explicitly: max abs error, max relative error, and which inputs produce the worst case.
- Do not label a change C1 just because the math works out on paper. Floating-point arithmetic is not real arithmetic. Reduction trees, scan ordering, product chains, mask-before vs mask-after, and accumulate-then-broadcast vs broadcast-then-accumulate all change floating-point semantics.
- Record **semantic/runtime flags** separately from the numerical class whenever a non-numeric risk is material. Only record flags that actually apply; do not emit an empty fixed list. Suggested flags: `nondeterministic`, `changes_nan_inf_behavior`, `changes_signed_zero_behavior`, `changes_atomic_order`, `changes_memory_visibility`, `changes_synchronization`, `changes_aliasing`, `changes_inplace_behavior`, `changes_address_stability`, `changes_layout_contract`, `changes_rng_stream`, `domain_restricted`, `architecture_restricted`, `approximate`, `cross_owner_state_sensitive`.

## Optimization decision record

Capture each optimization as:

```text
Optimization:
- Numerical class: C1 / C2 / C3 / C4 / N/A
- Semantic/runtime flags:
  - <material flags only>
- Domain:
  - shape / dtype / layout / device / mode
- Guard:
  - <conditions under which the fast path is enabled>
- Fallback:
  - <name or description of the reference path>
- Evidence:
  - <profiler, IR, benchmark, or counter confirming the claim>
```

## Scope of the labels

The numerical class (C1–C4, N/A) and semantic/runtime flags are conversational and review shorthand for this skill suite. They may be spoken to the user or to a parent agent when reporting the risk of a change.

These labels **must not** be written into the codebase as bare `C1`/`C2`/`C3`/`C4`. Do not put bare class codes into source comments, docstrings, identifiers, variable names, enum values, configuration keys, commit messages, branch names, tags, file names, or generated code. When the codebase itself must record the risk, use a descriptive name (for example, `floating_point_reorder`, `approximate_with_tolerance`, `semantics_changed`) together with the relevant flags, and keep the numerical-class mapping in the surrounding conversation, pull request, or decision record instead.

---

## Default-safe-path rule

A numerical or semantic change may replace the default path **only when it satisfies the program's existing numerical and determinism contract** without weakening tests, relaxing accepted tolerances, or expanding the accepted semantic domain.

- **C1** (bitwise-identical strict semantic equivalent): may be the default path.
- **C2** (numerically-equivalent reassociation — reduction tree, FMA contraction, mathematically-equivalent reordering): may become the default path when the project's correctness contract is already tolerance-based, the change stays within that tolerance, requires no test relaxation, preserves any deterministic-mode contract, and shows no systematic drift or boundary-case regression on real and pathological inputs. Under such a contract, C2 does **not** automatically require opt-in.
- **C3** (explicit approximation — precision reduction, truncation, fast transcendental, clipping, quantization, approximate reciprocal): default should be gated / opt-in unless the upstream API already defines this approximate contract.
- **C4** (result-level program semantics changed): always requires explicit approval.

A change that does **not** satisfy the existing contract must be:

- Gated behind a parameter, compile-time flag, runtime check, or configuration switch;
- Paired with a documented fallback to the original correct implementation;
- Accompanied by guard conditions (see the guard-condition template below).

The default code path must remain safe and correct. **Bitwise different does not equal semantically unsafe** — but a change becomes the default only through compatibility with the accepted contract, never by the size of the diff.

---

## Guard-condition template

Every fast path must declare its guard conditions explicitly. Use this template:

```text
Fast path is enabled only when:
- dtype is ...
- shape satisfies ...
- rank is ...
- layout / stride pattern is ...
- alignment is ...
- value range is ...
- precision mode is ...
- deterministic mode is ...
- training / inference mode is ...
- gradient required / no-gradient is ...
- device capability / architecture is ...
- chunk / block / tile size is ...
Otherwise use fallback path: <name or description>.
```

Common guard categories:

- **Type guards**: dtype, precision mode, mixed-precision configuration.
- **Shape guards**: minimum/maximum dimensions, divisibility, rank.
- **Layout guards**: contiguous, channel-last, channel-first, striding, alignment.
- **Value guards**: range (non-negative, normalized, bounded), presence of NaN/Inf/denormal.
- **Hardware guards**: device capability, architecture generation, driver version.
- **Mode guards**: training vs inference, gradient required, deterministic mode, debug mode.
- **Aliasing guards**: input/output overlap, in-place update safety.

---

### Guard design rules

A guard must be checkable and tied to the actual precondition. Avoid vague statements such as “for normal inputs” or “for supported shapes.” Express the condition in terms of dtype, dimensions, strides, alignment, architecture, value range, determinism mode, gradient requirements, aliasing, or other observable properties.

Do not use a guard to hide an uncharacterized correctness defect. If a fast path is wrong for inputs inside its declared domain, shrink or remove the domain until the implementation is correct.

When the runtime cost of a value-domain check would erase the speedup, use one of these patterns:

- enforce the contract at an API boundary and document it;
- assert in debug/test builds and trust a stronger upstream invariant in production;
- compute a cheap conservative predicate;
- keep the reference path as the default and make the optimization explicit opt-in.

## Numerical discipline

### Error reporting (mandatory for C2+)

For any optimization that changes numerics, report **all** of the following:

| Metric | Required |
|:-------|:--------:|
| Max absolute error | ✓ |
| Mean absolute error | ✓ |
| P95 / P99 absolute error | ✓ |
| Max relative error | ✓ |
| Mean relative error | ✓ |
| P95 / P99 relative error | ✓ |
| Normalised error (`‖new − ref‖ / ‖ref‖`) | ✓ |
| ULP error (if bit-level precision matters) | optional |
| NaN count in output | ✓ |
| Inf count in output | ✓ |
| Signed-zero differences | optional |
| Worst-case input shape | ✓ |
| Worst-case random seed | ✓ |
| Error vs sequence length / batch size trend | ✓ |
| Systematic bias direction (new > ref or new < ref) | ✓ |

Do **not** report only max abs diff. Small denominators inflate relative error; large outputs hide absolute error. Report both.

Relative error is undefined when |ref| is 0 or below a stated guard threshold. Compute the relative-error rows (Max/Mean/P95/P99 relative error, Normalised error) only over the guarded denominator domain. For the excluded near-zero domain, report the excluded count and absolute or scale-relative metrics, and state the denominator policy. Never infer 'safe' from a single max abs diff; an empirical envelope is not a formal bound.

### Tolerance rule

Relaxing a correctness tolerance is a **semantic decision**, not a debugging shortcut. Before relaxing any tolerance, answer:

- Is the error from floating-point accumulation reordering (C2) or from an explicit approximation (C3)?
- Is there truncation, clipping, or saturation?
- Does error grow with sequence length, batch size, or input magnitude?
- Does error concentrate on extreme inputs or distribute uniformly?
- Is a more numerically stable formulation available?
- Should the fast path be opt-in rather than default?

Tolerance values are contracts. Do not raise them without explaining the root cause.

### Numerical pathology checklist

When an optimization introduces division, cumprod, exp, log, reciprocal, rsqrt, subtraction of nearly-equal values, prefix-product, normalisation, softmax, or log-sum-exp, perform a dedicated numerical stability analysis:

- Can the operation produce NaN?
- Can the operation produce ±Inf?
- Can intermediate values underflow to zero (especially cumprod chains)?
- Can intermediate values overflow (especially division by subnormals)?
- Does the optimization change how subnormals are handled (flush-to-zero vs gradual underflow)?
- Does the optimization change signed-zero behavior?
- Does the optimization change the rounding path?
- Does the optimization change how extreme inputs propagate?
- Does the optimization change mask-before vs mask-after ordering (∞·0 = NaN risk)?
- Does the optimization push a scale factor into or out of a reduction?

Math equivalence does not guarantee floating-point safety. Every division, cumprod, and exp chain needs explicit guardrails.

---

## Value-range and distribution contract

Many fast paths make implicit assumptions about input values. Document them:

- Are inputs expected to be non-negative? Normalised?
- Is there an expected bound on scale, gate values, probabilities, or weights?
- Can extreme values, NaN, or Inf appear in valid inputs?
- Can subnormals appear? Does the fast path handle them or flush them?
- Does the fast path depend on a specific random distribution?
- Does it depend on early-training vs late-training statistics?
- Does it depend on parameter initialization range?
- Does it depend on quantization scale range?

If a fast path depends on a value-range assumption, it needs a runtime assert, debug assert, documentation, or fallback.

---

## Boundary semantics

Boundary rules are part of semantics. Explicitly test inclusive/exclusive conventions, masks, padding, tails, chunk boundaries, empty inputs, singleton dimensions, and non-divisible sizes.

For operations with masks or infinities, order matters. Examples:

- masking before versus after exponentiation;
- multiplying a masked value by zero when the unmasked value may be Inf;
- subtracting maxima before exponentiation;
- accumulating a scale inside versus outside a reduction;
- applying clipping before versus after normalization;
- changing an exclusive scan to inclusive plus shift.

These changes may alter NaN propagation, signed zero, underflow, overflow, and rounding even when the intended mathematical result appears equivalent.

## Mixed precision and fast math

Treat reduced precision, tensor-float modes, approximate transcendentals, flush-to-zero behavior, and contraction/FMA changes as explicit numerical choices.

Before enabling a lower-precision path, record:

- storage dtype and compute/accumulation dtype;
- cast points and rounding modes where relevant;
- scale/normalization strategy;
- saturation or clipping behavior;
- range of intermediate values;
- whether the reference uses a higher-precision accumulator;
- expected error growth with reduction length or depth.

Do not classify a precision change as C1. It is usually C2 or C3 depending on whether the mathematical operation remains exact but the evaluation order/precision changes, or whether an explicit approximation is introduced.

## Determinism, atomics, and parallel reductions

A faster reduction or atomic scheme can change result order across runs. Distinguish:

- deterministic algorithm with different but stable order;
- nondeterministic scheduling that changes accumulation order run to run;
- semantically different conflict resolution;
- implementation-defined behavior that the reference never guaranteed.

If deterministic mode is a supported user contract, a nondeterministic fast path requires an explicit guard and fallback. Performance comparisons must report whether deterministic mode is enabled on both paths.

## Test corpus

For C2+ changes, test more than random normal data. Include:

- zeros, signed zeros, all-equal values;
- tiny/subnormal-scale values where supported;
- very large finite values near overflow thresholds;
- NaN and ±Inf where valid inputs may contain them;
- cancellation-heavy patterns;
- monotone increasing/decreasing sequences;
- sparse and highly skewed values;
- lengths around block/chunk boundaries;
- multiple seeds and representative real inputs.

Sweep dimensions that control error growth: reduction length, sequence length, number of recurrent steps, batch size, and scale magnitude.

## Acceptance rule

C1 requires semantic equivalence and expected bitwise identity under the same execution semantics. C2 requires existing accepted tolerance without silently relaxing tests. C3 requires an explicit approximation contract and opt-in or otherwise clearly approved behavior. C4 requires explicit user approval.

A speedup that only passes after unexplained tolerance relaxation is not accepted. Route the result to [gpu-optimization-validation](../gpu-optimization-validation/SKILL.md) with the full error report and failure cases.
