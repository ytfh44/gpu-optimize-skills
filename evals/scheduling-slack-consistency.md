# Memory Scheduling Slack Consistency Evaluations

Use these cases to test whether an agent computes slack for a fixed candidate concurrency set S and does not derive overlap from isolated durations and then feed the lengthened duration back as if independent. Give a behavior agent only the raw prompt and the expected primary skill.

## Evaluation contract

For every case, record:

- whether slack was computed for a fixed candidate concurrency set S;
- whether overlap was decided before or after resolving the concurrency set;
- whether isolated duration was used to justify overlap that then lengthens the duration.

Fail a case when the agent computes slack from isolated durations, schedules overlap, and treats the resulting lengthened duration as if it were independent evidence.

## Slack from isolated duration is circular

**Raw user prompt**

> Task A runs 5 ms alone. If we overlap it with B, the critical path still has 3 ms slack, so overlap is safe.

**Expected primary skill:** `gpu-memory-scheduling`

**Allowed secondary skills:** `gpu-performance-evidence`.

**Must inspect:** the concurrency set S assumed; whether d_i(S) was recomputed under overlap; whether slack was solved inside schedule optimization.

**Forbidden assumptions:** isolated duration equals duration under overlap; slack computed once from isolated timing is valid for the overlapped schedule; lengthened duration from overlap does not change the slack.

**Pass condition:** state the fixed candidate concurrency set S, compute d_i(S) and contention under that S, solve slack inside schedule optimization, and report the realized critical chain rather than a one-shot isolated slack.
