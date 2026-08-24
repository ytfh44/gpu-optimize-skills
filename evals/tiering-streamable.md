# Tiering Streamable Readiness Evaluations

Use these cases to test whether an agent applies the offload/prefetch rejection rule only to atomic/all-or-nothing readiness and models streamable/chunked consumption separately. Give a behavior agent only the raw prompt and the expected primary skill.

## Evaluation contract

For every case, record:

- whether the resource is atomic or streamable;
- the readiness model used (whole-object vs chunk/tile, pipeline fill/drain, consumer service rate);
- whether first-chunk deadline and steady-state throughput were checked.

Fail a case when the agent rejects an offload solely because full-object transfer exceeds the inactive interval, while a streamable resource could be hidden via chunked consumption.

## Streamable tensor can hide migration

**Raw user prompt**

> A 4 GB tensor is consumed chunk-by-chunk. Full-object transfer takes longer than the inactive interval and the consumer is on the critical path. Reject the prefetch?

**Expected primary skill:** `gpu-memory-tiering-migration`

**Allowed secondary skills:** `gpu-memory-scheduling`, `gpu-performance-evidence`.

**Must inspect:** chunk/tile readiness, pipeline fill/drain, producer/consumer service rate, first-chunk deadline, steady-state throughput.

**Forbidden assumptions:** full-object transfer time bounds hideability; atomic/all-or-nothing readiness applies to streamable resources; the offload is unhideable because whole-object transfer > inactive interval.

**Pass condition:** model chunked readiness and throughput; accept the prefetch when first-chunk deadline and steady-state service rate are met, even if full-object transfer exceeds the inactive interval.
