# Numerical Safety Judgment Evaluations

Use these cases to test whether an agent distinguishes an empirical error envelope from a formal bound, applies a denominator policy for relative error, labels runtime changes with the correct numerical class, and refuses to scan-ify a non-associative recurrence. Give a behavior agent only the raw prompt and the expected primary skill. Do not include the remaining fields in the test prompt.

## Evaluation contract

For every case, record:

- the numerical class assigned (C1/C2/C3/C4/N/A) and the reason;
- whether error claims are separated into proven/specification bound, analytical bound, empirical envelope, and uncovered domain;
- the denominator policy used for relative error;
- the semantic/runtime flags recorded;
- the acceptance evidence required before a default or fast path.

Fail a case when the agent calls a test-measured maximum error a "bound" without analysis, reports relative error at a zero reference without a policy, forces a non-compute runtime change into C1, or converts a non-associative recurrence into a parallel scan.

## Empirical envelope is not a formal bound

**Raw user prompt**

> A C3 approximation replaces a transcendental with a fast polynomial. Tests on 10k random inputs show max absolute error 1.2e-3 and max relative error 4e-2. Can we ship it as the default path and call the error bound 4e-2?

**Expected primary skill:** `gpu-numerical-safety`

**Allowed secondary skills:** `gpu-optimization-validation`, `gpu-performance-evidence`.

**Must inspect:** whether the 1.2e-3 / 4e-2 figures are proven, analytically derived, or merely tested; the input domain covered; the uncovered domain.

**Forbidden assumptions:** a tested maximum error is a formal error bound; 10k random inputs cover adversarial or boundary cases; one all-close check defines safety.

**Pass condition:** classify the numbers as an empirical envelope, state that no specification or analytical bound exists, list the uncovered domain, and keep the change behind a guard unless a real bound or tolerance is established.

## Relative error at a zero reference needs a denominator policy

**Raw user prompt**

> Comparing reference and new outputs, many reference values are exactly 0. The agent reports "max relative error infinite" and concludes the optimization is broken. Is that the right read?

**Expected primary skill:** `gpu-numerical-safety`

**Allowed secondary skills:** `gpu-optimization-validation`.

**Must inspect:** how relative error is defined when |ref| is 0 or near a guard threshold; whether absolute error is reported alongside; whether the denominator policy is stated.

**Forbidden assumptions:** relative error is well-defined at ref = 0; a single infinite relative error implies global unsafety.

**Pass condition:** report "n/a (ref≈0)" or a scale-relative metric, state the denominator policy, and judge using absolute error plus the empirical envelope on the non-zero domain.

## Runtime change is N/A, not C1

**Raw user prompt**

> We changed the allocator to pool and reuse buffers and remap VMM backing without altering any computed result. How should this be labeled under the numerical taxonomy?

**Expected primary skill:** `gpu-numerical-safety`

**Allowed secondary skills:** `gpu-resource-lifetime-allocation`, `gpu-virtual-memory-fragmentation`.

**Must inspect:** whether any value-producing computation changed; whether the change is outside numerical transformation.

**Forbidden assumptions:** every optimization must be C1-C4; a runtime/backing change that preserves results is "C1"; the same change is double-labeled.

**Pass condition:** label the change N/A with material semantic/runtime flags (e.g. changes_address_stability, architecture_restricted), keeping C1 reserved for bitwise-identical compute transforms.

## Monotone recurrence is not a parallel scan

**Raw user prompt**

> A state update s_{t+1} = f(s_t, x_t) is monotone in s_t. We want to parallelize it over chunks with a prefix-style combine. Is associative combine automatically satisfied?

**Expected primary skill:** `gpu-reductions-scans`

**Allowed secondary skills:** `gpu-numerical-safety`, `gpu-kernel-execution`.

**Must inspect:** whether the combine operator is provably associative; whether a finite, combinable per-chunk summary exists; whether the monotone property alone implies either.

**Forbidden assumptions:** monotonicity implies associativity; a monotone update admits a combinable summary; "prefix-style" structure makes the parallel decomposition valid.

**Pass condition:** reject the scan-ification unless an associative combine or an explicitly proven composable summary/state representation is supplied; otherwise keep the recurrence serial or restructure the state.
