# Scalar Capacity Planner

Plan reserved and elastic capacity under one uncertain scalar state, with independently checked lower and upper objective bounds. This installable Python package is an **offline research prototype**. All examples use **synthetic assumptions**; no AI workload traces have been collected or calibrated. It does not control infrastructure or provide a production autoscaler.

## Quickstart

Python 3.10 or later:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
# To reproduce the recorded Python 3.12 dependency environment:
# python -m pip install -c requirements-tested.txt -e '.[test]'
scalar-capacity-planner --k 3 --Y 2
python -m pytest -q tests
(cd validation && python -m unittest -v test_shadow_adapter test_plan_result_connector)
```

## Model and API

```python
from scalar_capacity_planner import ModelSpec, CapacityPlanner
spec = ModelSpec(a=(2, -.5), b=(3, -.5), d=(8, 2),
                 p=1, h=4, mean_band=(-.1, .1),
                 mad_center=0, mad_upper=.5, nmax=4)
planner = CapacityPlanner(spec, grid_size=401)
result = planner.solve(k=3, Y=2, gap_tolerance=.05)
updated = planner.solve(k=2.5, Y=1)  # same DPP graph
```

Coefficients are in increasing power order. `a(t)` is elastic capacity per unit, `b(t)` reserved capacity per integer unit, and `d(t)` demand under one common normalized shock t in [-1,1]. One planning window and consistent cost/capacity units are assumed. a and b have degree at most two; d is affine. a and b must be positive everywhere; d must be nonnegative. The supported model further requires min(a)>p/h, checked using exact rational quadratic minima. p and h are positive elastic and shortage prices. k is nonnegative reserved-unit cost; Y is nonnegative elastic cap. x ranges over every integer 0..nmax (nmax at most 1000). Costs and caps may change only through `solve`; a different model requires a new immutable `ModelSpec` and planner.

For each x and shock t the model solves

    Q(x,t) = min p*y + h*z
    subject to b(t)*x + a(t)*y + z >= d(t), 0 <= y <= Y, z >= 0.

The objective is k*x + sup E[Q(x,t)], over probability laws supported on [-1,1] whose mean lies in `mean_band` and E|t-mad_center| <= mad_upper. MAD center is a fixed supplied center, not the unknown law's mean. Parameters are assumptions, not learned from data. Unbounded shortage z is a priced soft penalty: no hard SLA guarantee follows.

`ModelSpec` copies coefficient inputs into immutable tuples. `CapacityPlanner.spec` is read-only. There are no fresh coefficient arguments at solve time to disagree with the cached graph. `is_dpp` reports the actual CVXPY graph property. Calls on one planner are serialized. Private attributes are implementation details and must not be mutated.

## Bounds and statuses

The numerical optimization uses piecewise-affine moment majorants and cubic Markov–Lukács 2x2 PSD representations. The graph is built once; x and Y are CVXPY parameters. k is added after each integer action is evaluated, so changing k requires no graph rebuild.

Independently of solver feasibility residuals, exact `Fraction` arithmetic interprets the supplied binary floating-point inputs and numerical majorant coefficients as rationals. Bernstein convex-hull lower bounds on 32 subintervals per center-side bound all three polynomial constraints. A nonnegative constant repair makes the majorant globally valid on the continuous support. This does not rely on the solver's PSD feasibility report.

A fresh SciPy grid LP generates a candidate lower-bound law for every action. Its nonnegative weights are converted to exact rationals and normalized; mixing toward an analytically feasible Dirac anchor repairs mean/MAD violations. If the grid LP fails, the feasible Dirac law is used and the diagnostic records that fallback. The law is validated exactly before computing its recourse. The grid LP is only a lower-bound generator, not a proof of continuous-support optimality.

For each action, fixed cost is added exactly before final bounds are rounded outwards to floats. The plan selects the smallest certified upper bound; its global lower bound is the minimum certified lower bound across **all** enumerated actions. Missing action bounds make the global gap unavailable. `objective` is the numerical solver's estimated worst-expected total cost, not a bound; use `lower_bound`, `upper_bound`, and `gap` for guarantees. An integer decision is only gap-optimal under these assumptions; the exact minimizing integer need not be uniquely identified.

- `verified`: an independently bounded global objective gap is within `gap_tolerance`. This is mathematical model verification, not operational safety.
- `unknown`: requested tolerance not reached or some independent bound/solver result is unavailable. Existing bounds remain informative.
- `infeasible`: the ambiguity set is provably empty by the exact Jensen/Dirac condition dist(center, mean_band)>MAD cap. It does not mean capacity shortage is impossible to handle: z is unbounded.
- `solver_error`: solver calls failed and no action could be independently bounded.

Nonempty boundary ambiguity sets are allowed. No dual-attainment claim is made for them; independent repaired bounds remain valid if produced. Invalid/unsupported inputs raise ValueError or TypeError rather than being mislabeled infeasible. `solver=` is intended for diagnostics; the tested default is CLARABEL. This implementation is bounded and may be slow for large nmax. It does not certify calibration error, model fit, multi-dimensional shocks, operational SLA, or real provider economics.

## Synthetic example

`example_result.json` records the default command above and labels its inputs as
synthetic. `objective` is a solver estimate; the independently checked fields are
`lower_bound`, `upper_bound`, and `gap`. Numerical values can vary slightly with
solver versions. `requirements-tested.txt` records the Python 3.12 dependency
versions used to reproduce the example and run the tests.

The planner chooses the reserved count before observing the state. Elastic
recourse assumes that the state is then observed and capacity becomes available
within the planning window. Startup delays, queue dynamics, discrete billing,
and delayed observations need separate modeling and measurement.

## Advice interface and future validation

The optional [validation examples](validation/README.md) translate serialized
planner results into local advice records. They perform no network requests or
actuation. Empirical gates remain unvalidated for the synthetic example, so the
example abstains even when the objective gap is verified. Caller-supplied gate
evidence and identity labels are not authenticated by this interface.

A [validation protocol](validation/PROTOCOL.md) describes the measurements needed
before making service-quality or cost-benefit claims. No measured serving-cost
benefit is claimed by this project.

## Implementation notes

The semidefinite graph uses the cubic interval nonnegativity representation of
Markov and Lukacs and CVXPY parameter reuse. These ideas do not imply affiliation
with or endorsement by any researcher or institution. Automated tests cover
model invariants, direct recourse LP comparisons, graph reuse, error statuses,
and independent-bound repairs; they do not validate real service performance.

AI tools assisted with implementation and documentation. Numerical guarantees
come from the stated model and independent arithmetic checks, rather than from
AI-generated assertions.

## License

Licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for
copyright attribution. Third-party dependencies retain their own licenses.
