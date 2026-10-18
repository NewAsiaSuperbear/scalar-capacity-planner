import copy
from datetime import datetime, timezone
import unittest
from shadow_adapter import advise, GATES


class ShadowGuardTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2025, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
        self.s = dict(service_id='SYNTHETIC_SERVICE', profile_hash='SYNTHETIC_PROFILE',
                      provenance='synthetic', incumbent_x=1, x_candidates=[1, 2],
                      available_at='2025-01-01T11:59:59Z', decision_at='2025-01-01T12:00:00Z',
                      expires_at='2025-01-01T12:01:00Z', max_numerical_gap=.01,
                      gates={k: {'passed': True, 'evidence_ref': 'SYNTHETIC_FIXTURE_ONLY'} for k in GATES})
        self.r = dict(service_id='SYNTHETIC_SERVICE', profile_hash='SYNTHETIC_PROFILE',
                      recommended_x=2, solver_status='ok', incumbent_modeled_cost=10.,
                      recommended_modeled_cost=9., numerical_gap=.001)

    def test_advice_never_actuates(self):
        before = copy.deepcopy((self.s, self.r))
        a = advise(self.s, self.r, self.now)
        self.assertEqual(a['status'], 'advice')
        self.assertFalse(a['actuation'])
        self.assertFalse(a['evidence_verified_by_adapter'])
        self.assertEqual(before, (self.s, self.r))

    def test_rejection_cases(self):
        cases = [('available_at', '2025-01-01T12:00:01Z'),
                 ('expires_at', '2025-01-01T11:59:59Z'),
                 ('profile_hash', 'other'), ('x_candidates', [1.5]),
                 ('max_numerical_gap', -1), ('gates', {})]
        for field, value in cases:
            s = copy.deepcopy(self.s); s[field] = value
            with self.subTest(field=field):
                a = advise(s, self.r, self.now)
                self.assertEqual(a['status'], 'abstain')
                self.assertIsNone(a['recommended_x'])
                self.assertFalse(a['actuation'])

    def test_bad_solver_results(self):
        for field, value in [('recommended_x', 1.5), ('recommended_x', True),
                             ('solver_status', 'failed'), ('numerical_gap', float('nan')),
                             ('numerical_gap', .1), ('incumbent_modeled_cost', None)]:
            r = dict(self.r); r[field] = value
            with self.subTest(field=field, value=value):
                self.assertEqual(advise(self.s, r, self.now)['status'], 'abstain')

    def test_malformed_input(self):
        self.assertEqual(advise({}, {}, self.now)['status'], 'abstain')


if __name__ == '__main__':
    unittest.main()
