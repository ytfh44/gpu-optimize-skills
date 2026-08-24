# Lifetime Aliasing Contract Evaluations

Use these cases to test whether an agent distinguishes unconditional aliasing from schedule-conditioned aliasing and accepts the latter when an explicit ordering constraint makes it safe. Give a behavior agent only the raw prompt and the expected primary skill.

## Evaluation contract

For every case, record:

- whether the alias is unconditional or schedule-conditioned;
- the ordering constraint that makes a schedule-conditioned alias safe;
- which specialist owns the ordering constraint.

Fail a case when the agent rejects a schedule-conditioned alias that is safe under an explicit ordering constraint, or treats lifetime as the sole owner of scheduling order.

## Schedule-conditioned aliasing is acceptable

**Raw user prompt**

> Buffers A and B can otherwise run in parallel, but we want to alias them to save 10 GB. If we add an ordering constraint A_last_use -> B_create, is the alias then safe?

**Expected primary skill:** `gpu-resource-lifetime-allocation`

**Allowed secondary skills:** `gpu-memory-scheduling`, `gpu-virtual-memory-fragmentation`.

**Must inspect:** whether feasible executions without the constraint would overlap live ranges; whether the added ordering constraint removes the overlap; whether the constraint is recorded as a precondition.

**Forbidden assumptions:** every aliasing candidate must be safe under all feasible executions; lifetime alone owns scheduling order; an ordering constraint cannot make an alias safe.

**Pass condition:** accept the schedule-conditioned alias, record the A_last_use -> B_create constraint as a precondition owned by the scheduling specialist, and distinguish it from unconditional aliasing in the eligibility record.
