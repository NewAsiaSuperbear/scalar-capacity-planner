# Offline advice examples

These examples translate a serialized planner result into a local advice record.
They do not collect telemetry, authenticate evidence, connect to a serving system,
or change infrastructure. All included fixtures are synthetic.

- [PROTOCOL.md](PROTOCOL.md): measurements, information timing, and comparison requirements.
- [ADAPTER.md](ADAPTER.md): input contract, evidence gates, and abstention behavior.
- `shadow_adapter.py`: a standard-library guard and serializer.
- `plan_result_connector.py`: translation from a serialized `PlanResult`.

Run from the repository root:

```sh
(cd validation && python -m unittest -v test_shadow_adapter test_plan_result_connector)
```

A numerically verified objective gap does not satisfy empirical gates. The
connector test reads `example_result.json`, leaves every empirical gate false,
and checks that advice abstains. Identity and profile bindings are caller
assertions, and gate evidence references are not verified by the adapter.
