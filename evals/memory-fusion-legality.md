# Memory Fusion Legality Evaluations

Use these cases to test whether an agent applies the fusion legality test correctly, especially that "monotonic streaming state" is not treated as sufficient for tiling, reassociation, or cross-chunk composition. Give a behavior agent only the raw prompt and the expected primary skill.

## Evaluation contract

For every case, record:

- the fusion legality conditions the agent checked;
- whether "monotone" alone was accepted as a license to fuse/tile/reassociate;
- the cross-reference to reduction/scan associativity when a combine is involved.

Fail a case when the agent fuses or tiles a transformation purely because its state is monotone, without an associative combine or a proven composable summary.

## Monotone streaming state is not fusion-safe by itself

**Raw user prompt**

> A kernel maintains a monotone running aggregate across tiles and we want to fuse it with the next producer and split the aggregate across tiles for parallelism. The state is monotone, so that is safe, correct?

**Expected primary skill:** `gpu-memory-fusion-layout`

**Allowed secondary skills:** `gpu-reductions-scans`, `gpu-numerical-safety`, `gpu-kernel-execution`.

**Must inspect:** whether the running aggregate has an associative combine or a proven composable per-tile summary; whether cross-tile composition preserves the result.

**Forbidden assumptions:** monotone state implies combine-associativity; a monotone update admits a combinable per-chunk summary; fusion + tiling is safe whenever state is monotone.

**Pass condition:** require an associative combine or an explicitly proven composable summary/state representation; otherwise keep the aggregate serial or restructure before fusing.
