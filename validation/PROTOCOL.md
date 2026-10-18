# Empirical validation protocol

The package currently has synthetic examples and interface tests. No service
profile, production deployment, or measured operating-cost benefit is provided.
The following protocol describes future validation, rather than completed work.

## Freeze the service and accounting units

Choose one model artifact, runtime, hardware allocation, precision, batching and
cache policy, and request class. Record versions and hashes. Fix latency and
quality targets before collecting outcomes. Define a planning window and keep
capacity, work, and price units consistent across reserved capacity `b(t) * x`,
elastic capacity `a(t) * y`, demand `d(t)`, and shortage `z`.

The shortage variable is a priced penalty with no upper bound. It does not
represent a guaranteed overflow provider or establish an SLA. Continuous elastic
capacity is a relaxation unless divisible resource time is operationally
available. Rounding a plan requires reevaluation of its bounds.

Measure startup, warmup, draining, billing granularity, backlog, and resource
interference. If queue state carries materially between windows, the static
model requires revision before its advice can be interpreted operationally.

## Preserve information timing

Make the reserved decision using only records available at the decision time.
Keep realized outcomes separate from forecasts. Perfect-information elastic
recourse assumes that the scalar state is observed before choosing elastic
capacity and that capacity becomes ready in time. Score a causal policy
separately when those assumptions fail. Output length observed after generation
cannot serve as a contemporaneous predictor without an explicit forecast.

Use the same offered workload, initial queue and cache state, seeds, resource
limits, and accounting rules for every compared policy. Record failed, timed-out,
rejected, canceled, and retried requests. Randomize repeated policy blocks to
reduce order effects and report interference and censoring.

## Test the response model before optimizing

Collect repeated measurements for every supported action and operating region.
Fit `a`, `b`, and `d` on training data only and preserve chronological holdout
blocks. Check action-specific residuals, rather than only pooled fit. Compare
the scalar-state response with richer models of concurrency, request sizes,
cache state, batching, bursts, and queues. Reject scalar sufficiency if omitted
state materially changes capacity or service-quality conclusions.

Freeze acceptance thresholds before holdout measurement. Empirical quantiles
are not deterministic action-uniform response bounds. Regions without adequate
support must remain outside advice. An arrival trace alone does not supply
counterfactual service times, billing, replica states, or policy costs.

## Evidence gates

| Gate | Required evidence |
| --- | --- |
| Integrity | Consistent service identity, units, timestamps, request counts, and recorded censoring. |
| Support | Repeated observations across every advertised action and workload region. |
| Response | Prespecified held-out error checks and comparisons with richer state models. |
| SLO | Measured latency, error, and completion behavior under the proposed decisions. |
| Economics | Measured billable resource use, applicable tariffs, and startup/overflow sensitivity. |
| Baseline | Matched comparisons with the strongest feasible prespecified alternatives. |

The adapter consumes caller-supplied gate flags and evidence references. It does
not independently validate the evidence. A mathematical objective-gap check
never sets these empirical gates to true.

## Comparisons and reporting

Compare fixed incumbent capacity, a demand-quantile rule, sample-average scenario
planning, and a suitable grid or exchange method using the same actions and
information. Include a simple exact solution when coefficients are constant.
Keep model-level bound verification separate from service replay.

Report modeled objective bounds, planning time, observed resource use,
throughput, overflow, latency quantiles, errors, timeouts, and startup counts.
Use paired repeated blocks and state the assumptions behind uncertainty
intervals. Report negative or inconclusive outcomes and all prespecified
configurations. Without an applicable tariff, report resources and modeled
cost instead of money saved.

Stop after one frozen service's complete held-out evaluation and an explicit
assessment of model adequacy. This repository's interface remains advice-only;
production integration requires separate engineering and validation.
