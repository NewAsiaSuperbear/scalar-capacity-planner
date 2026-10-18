"""Use the actual package-generated synthetic artifact, no solver dependency."""
import json
from pathlib import Path
import unittest
import test_shadow_adapter as guard_tests
from shadow_adapter import advise
from plan_result_connector import translate_plan_result, unvalidated_gates


class ConnectorTest(unittest.TestCase):
    def test_verified_synthetic_plan_still_abstains(self):
        path = Path(__file__).resolve().parents[1] / 'example_result.json'
        artifact = json.loads(path.read_text())
        self.assertIn('SYNTHETIC', artifact['data_label'])
        plan = artifact['result']
        self.assertEqual(plan['status'], 'verified')
        fixture = guard_tests.ShadowGuardTest(); fixture.setUp()
        snapshot = fixture.s
        snapshot['x_candidates'] = list(range(artifact['model']['nmax'] + 1))
        snapshot['gates'] = unvalidated_gates()
        result = translate_plan_result(plan, service_id=snapshot['service_id'],
                                       profile_hash=snapshot['profile_hash'],
                                       incumbent_x=snapshot['incumbent_x'])
        self.assertEqual(result['solver_status'], 'ok')
        self.assertEqual(result['recommended_x'], plan['selected_x'])
        self.assertEqual(result['numerical_gap'], plan['gap'])
        self.assertEqual(result['recommended_modeled_cost'], plan['upper_bound'])
        self.assertEqual(result['identity_binding'], 'caller_asserted_unverified')
        advice = advise(snapshot, result, fixture.now)
        self.assertEqual(advice['status'], 'abstain')
        self.assertIsNone(advice['recommended_x'])
        self.assertFalse(advice['actuation'])
        self.assertEqual(set(advice['reasons']), {'gate_failed:' + k for k in snapshot['gates']})


if __name__ == '__main__':
    unittest.main()
