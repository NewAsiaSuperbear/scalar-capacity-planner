# Advice adapter contract

`shadow_adapter.py` is a local standard-library guard and serializer.
`plan_result_connector.py` translates a serialized `PlanResult` into its result
fields. Neither module collects data, invokes the optimizer, contacts a serving
API, or applies a recommendation.

## Snapshot inputs

Supply `service_id`, `profile_hash`, `incumbent_x`, `x_candidates`,
`available_at`, `decision_at`, `expires_at`, `max_numerical_gap`, and `gates`.
Timestamps must include timezones and satisfy
`available_at <= decision_at <= now < expires_at`.

Actions must be nonnegative integers. The incumbent and recommendation must
both belong to the supported candidate set. Each named gate (`integrity`,
`support`, `response`, `slo`, `economics`, `baseline`) requires `passed: true`
and a nonempty `evidence_ref`. These are caller assertions; the adapter does
not authenticate the service, profile, result, or underlying evidence.

## Result translation

Pass the serialized plan plus explicit service identity, profile hash, and
incumbent to `translate_plan_result`. The connector uses the global plan gap,
selected-action upper bound, and verified incumbent-action upper bound. Costs
are model objective bounds, rather than observed cash expenditure or savings.
Malformed or unavailable values produce a failed result for the guard to reject.

`unvalidated_gates()` leaves every empirical gate false. Use it when measured
validation is unavailable, including with the supplied synthetic example.

## Output behavior

`advise` emits `status: abstain` when timing, identity consistency, supported
actions, gates, numerical fields, solver status, or tolerance checks fail.
Successful checks emit `status: advice`. Every output has `actuation: false`
and `evidence_verified_by_adapter: false`. Neither status is a service safety
certificate. The caller remains responsible for checking the input contract
and interpreting the advice.

The examples require no credentials, request prompts, or operational data.
