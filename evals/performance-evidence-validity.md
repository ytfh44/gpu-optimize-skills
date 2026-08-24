# Performance Evidence Validity Evaluations

Use these cases to test whether an agent treats profiler/counter results as measurements (not ground truth), records measurement validity, refuses to optimize occupancy as a target, and refuses to claim Tensor Core usage without evidence. Give a behavior agent only the raw prompt and the expected primary skill.

## Evaluation contract

For every case, record:

- the evidence tier cited (direct observation / derived measurement / analytical model / inference / assumption);
- the measurement-validity fields recorded for any counter/profiler finding;
- whether occupancy or Tensor Core usage is asserted without evidence.

Fail a case when the agent reports a multi-pass replay counter as the real performance, treats occupancy as the optimization target, or claims Tensor Core execution from the shape of the code alone.

## Profiler replay artifact is not real performance

**Raw user prompt**

> Nsight Compute reports kernel X is 30% faster after my change, collected with multi-pass replay because some metrics needed separate passes. Ship it?

**Expected primary skill:** `gpu-performance-evidence`

**Allowed secondary skills:** `gpu-kernel-execution`, `gpu-optimization-validation`.

**Must inspect:** collection mode; replay count; whether concurrency was preserved across passes; profiler overhead; direct vs derived metric; end-to-end timing.

**Forbidden assumptions:** a counter from one replay pass equals the original execution; multi-pass metrics are consistent and in-range; a profiler delta is an end-to-end speedup.

**Pass condition:** report collection mode and replay artifacts, mark the number hypothetical until validated against an end-to-end timing, and require a real timeline before claiming improvement.

## Occupancy is not the target

**Raw user prompt**

> Kernel Y runs at 40% occupancy. Let's raise occupancy to win performance.

**Expected primary skill:** `gpu-performance-evidence`

**Allowed secondary skills:** `gpu-kernel-execution`.

**Must inspect:** the actual bottleneck (compute, bandwidth, synchronization, instruction dependency); whether occupancy is even the limiting resource.

**Forbidden assumptions:** higher occupancy is always better; occupancy is the performance target; a low-occupancy kernel is necessarily suboptimal.

**Pass condition:** refuse to optimize occupancy as a goal; classify the real bottleneck from evidence and tune only the measured limiter.

## Tensor Core claim needs evidence

**Raw user prompt**

> The code is a matmul, so it definitely uses Tensor Cores and is optimal. Anything to improve?

**Expected primary skill:** `gpu-performance-evidence`

**Allowed secondary skills:** `gpu-kernel-execution`, `gpu-compiler-runtime`.

**Must inspect:** profiler trace, compiler IR, precision config, shape alignment to tile constraints, and whether a fast path is actually selected.

**Forbidden assumptions:** a matmul shape implies Tensor Core execution; claiming Tensor Cores without evidence; source shape proves generated behavior.

**Pass condition:** require profiler/IR evidence before asserting Tensor Core usage, and identify the real bottleneck rather than assuming optimality.

## One sample is not proof

**Raw user prompt**

> I timed it once: 12 ms, down from 15 ms. That is a 20% speedup, merge it.

**Expected primary skill:** `gpu-performance-evidence`

**Allowed secondary skills:** `gpu-optimization-validation`.

**Must inspect:** median and p95, variance, benchmark state (compile/warm-up, scope), representative workload matrix.

**Forbidden assumptions:** one timing sample proves a result; a single microbenchmark proves end-to-end value.

**Pass condition:** require median/p95 over a representative matrix and a stated measurement protocol before any keep/reject decision.
