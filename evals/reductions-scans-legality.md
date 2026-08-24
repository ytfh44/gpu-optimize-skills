# Reduction and Scan Legality Evaluations

Use these cases to test whether an agent requires a verified associative combine before parallel scan/combine decomposition and does not treat monotonicity as composability. Give a behavior agent only the raw prompt and the expected primary skill.

## Evaluation contract

For every case, record:

- whether associativity of the combine operator was checked or proven;
- whether a finite, combinable per-chunk summary exists;
- the numerical class and any semantic/runtime flags.

Fail a case when the agent decomposes a non-associative operator into a parallel scan, or treats a monotone state update as if it admitted a combinable summary.

## Non-associative operator rejects parallel scan

**Raw user prompt**

> Parallelize a running max-plus scan (combine = max(a, b + c)) over chunks. It is just a scan, right?

**Expected primary skill:** `gpu-reductions-scans`

**Allowed secondary skills:** `gpu-numerical-safety`, `gpu-kernel-execution`.

**Must inspect:** whether max(a, b + c) is associative; whether the chunk boundary combine preserves the global result.

**Forbidden assumptions:** any two-argument combine is associative; "scan" structure makes parallel decomposition valid; a serial reference run defines the parallel semantics.

**Pass condition:** reject the naive parallel scan unless an associative reformulation or a proven composable summary is supplied; otherwise keep it serial or restructure.

## Monotone reduction is not composable

**Raw user prompt**

> This reduction is monotone in the accumulator, so we can split it into chunks and recombine freely.

**Expected primary skill:** `gpu-reductions-scans`

**Allowed secondary skills:** `gpu-numerical-safety`.

**Must inspect:** whether monotonicity implies a finite, combinable per-chunk summary; whether an explicit composable representation is proven.

**Forbidden assumptions:** monotonicity implies associativity; a monotone update admits a combinable summary; chunking is always safe for stateful reductions.

**Pass condition:** require an explicitly proven composable summary/state representation; do not treat "monotone" as license to tile or reassociate.
