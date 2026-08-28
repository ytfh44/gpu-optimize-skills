# Optimization Search Autonomy Evaluations

These fresh-context cases test whether an agent can search for an optimization from observed behavior instead of parroting a catalog of named techniques. The cases include unseen mechanisms and deliberately accept a valid transformation that was not named in the prompt. Give the behavior agent only the raw user prompt and `gpu-code-optimizer`; do not include the expected answer, specialist list, or pass conditions in the prompt.

## Fresh-context evaluation contract

The test set intentionally avoids naming the expected transformation. Reward an answer that reconstructs the relevant machine-visible relation, states multiple causal hypotheses when the evidence is ambiguous, and chooses small falsifying experiments before an expensive rewrite. Do not require a particular technique string: an unexpected transformation is acceptable when it preserves the stated invariants and is supported by a discriminating measurement.

For each case, check whether the agent:

- establishes or requests a reproducible baseline before claiming a gain;
- separates observed, modeled, inferred, and assumed facts;
- records an observed symptom, proposed mechanism, preconditions, predicted target-metric effect, predicted independent evidence, cheapest falsifying probe, confounders, and cost;
- keeps independent one-factor variants attributable to the same baseline;
- updates confidence from both positive and negative observations;
- treats a metric/mechanism mismatch as evidence for a hidden mechanism or compensating cost;
- scopes rejected results to their workload/evidence state and states when they may be reopened;
- re-profiles after an accepted change and revalidates any composition rather than assuming additive wins.

Penalize recipe parroting and unsupported named technique claims when the answer lists familiar transformations without connecting them to a measured mapping, an invariant, a prediction, and a falsifier. A negative result is useful evidence when it updates confidence or changes the next probe; it is not a reason to hide the result. Penalize vendor- or operator-specific claims that are not supported by the supplied evidence.

### Raw-prompt-only isolation

For each case, send only the text under **Raw user prompt** to the behavior agent together with the parent Skill. Keep the case title, pass condition, scoring rubric, and any expected interpretation outside that agent context. The raw prompt must not reveal a named expected transformation; if a mechanism name is a supplied observation, grade whether the agent still derives the causal relation rather than parroting it.

## Minimum scoring rubric

Score each dimension **0 / 1 / 2**: 0 means absent or contradicted, 1 means partial or unsupported, and 2 means explicit and evidence-linked.

1. Baseline and measurement scope.
2. Mapping and causal mechanism.
3. Discriminating experiment and falsifier.
4. One-factor attribution and variant isolation.
5. Residual, negative-result, and confidence update.
6. Correctness, guard/fallback, and revalidation.

A case passes at **8/12** or higher and has no **critical failure**. Critical failures are claiming a speedup without a baseline, hiding a confounder as proof, dropping a correctness/guard requirement, permanently blacklisting a conditional rejection without checking reopening conditions, or combining variants without separately validating the composition. A valid unexpected transformation earns full credit when it satisfies the evidence and invariant requirements; no particular named technique is required.

## Ambiguous hot path requires a portfolio

**Raw user prompt**

> This unfamiliar GPU path is slow. The end-to-end median is 8.4 ms, but the trace shows a 2.1 ms region with uneven work-group durations, a 1.4 ms region with more memory transactions than the requested bytes, and a short producer/consumer pair around a 0.7 ms temporary. I have not changed code yet. Find the best next optimization.

**Pass condition:** preserve the baseline, reconstruct the work, address, and lifetime relations, state competing mechanisms, and propose several cheap one-factor probes or variants against the same baseline. The answer may choose any valid transformation, but it must explain what observation would distinguish the candidates.

## Counter movement without runtime movement

**Raw user prompt**

> I changed one mapping relation. The predicted transaction metric improved by 18%, but the end-to-end median is unchanged and the target kernel is only 6% of the request. The compiler output confirms that the change reached the generated code. What should I conclude and do next?

**Pass condition:** classify the result as evidence about the mechanism, not as an application speedup; search for a compensating cost or an unimportant phase; compare the target metric at the relevant scope; and choose the next probe from the residual rather than discarding the measurement or declaring victory.

## Rejected result may become valid

**Raw user prompt**

> A candidate was rejected after it increased register spills on the original shape set. Since then, an accepted change removed an intermediate and the profiler now shows a different limiting resource. The device, compiler version, and representative workload are otherwise unchanged. Should the old candidate remain permanently blacklisted?

**Pass condition:** keep the rejection in an evidence-scoped ledger, name the changed bottleneck as a reopening condition, and retest it as a one-factor variant against the new baseline. Do not repeat it automatically when no relevant fact changed, and do not assume the old result transfers unchanged.

## Mapping reconstruction without a named trick

**Raw user prompt**

> In a tiled kernel, logical items are assigned to execution groups, each group emits a rectangular output, and the address trace shows that neighboring lanes repeatedly contend for the same small set of storage locations. Tail tiles are masked, and the output must remain deterministic. Derive a safe optimization search plan without assuming a particular vendor feature or textbook technique.

**Pass condition:** write the logical-work → ownership → execution-instance → scheduling-slot relation and the logical-value → layout/address → transaction → storage-resource relation; identify determinism, boundary, and synchronization invariants; derive reversible candidates from remaining degrees of freedom; and pair each candidate with independent evidence and a falsifier.

## Independent wins do not compose automatically

**Raw user prompt**

> Two independent variants each improve the same end-to-end median by about 3% from the untouched baseline. Variant A changes ownership; variant B changes staging. I want to enable both immediately to save another benchmark round. Is that justified?

**Pass condition:** keep attribution clean, test the composition separately, re-check guards and correctness, measure new resource pressure and the target end-to-end metric, and re-profile because the bottleneck may move. Treat additive speedup as a hypothesis, not an inference from the isolated wins.
