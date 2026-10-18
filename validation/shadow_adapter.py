"""Offline advice guard. Pure stdlib; no network, serving imports or actuation.

Gate evidence is supplied by caller, not verified by this adapter. This is NOT
an optimizer or production safety layer. All demo values are synthetic.
"""
from datetime import datetime, timezone
import math

GATES = ('integrity', 'support', 'response', 'slo', 'economics', 'baseline')


def _time(value):
    out = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if out.tzinfo is None:
        raise ValueError('timezone required')
    return out


def _number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def advise(snapshot, result, now=None):
    """Return advisory JSON dict; no deployment-side effects of any kind."""
    now = now or datetime.now(timezone.utc)
    reasons = []
    incumbent = snapshot.get('incumbent_x')
    out = {'mode': 'shadow', 'actuation': False, 'status': 'abstain',
           'incumbent_x': incumbent, 'recommended_x': None,
           'reasons': reasons, 'evidence_verified_by_adapter': False}
    try:
        if now.tzinfo is None:
            raise ValueError('now timezone required')
        decision = _time(snapshot['decision_at'])
        available = _time(snapshot['available_at'])
        expiration = _time(snapshot['expires_at'])
        if not available <= decision <= now < expiration:
            reasons.append('stale_or_noncausal_timing')
        candidates = snapshot['x_candidates']
        if not candidates or any(type(x) is not int or x < 0 for x in candidates):
            reasons.append('invalid_discrete_actions')
        if type(incumbent) is not int or incumbent not in candidates:
            reasons.append('unsupported_incumbent')
        for key in ('service_id', 'profile_hash'):
            if not snapshot.get(key) or snapshot[key] != result.get(key):
                reasons.append('identity_mismatch:' + key)
        for gate in GATES:
            entry = snapshot.get('gates', {}).get(gate, {})
            if entry.get('passed') is not True or not entry.get('evidence_ref'):
                reasons.append('gate_failed:' + gate)
        choice = result.get('recommended_x')
        if type(choice) is not int or choice not in candidates:
            reasons.append('unsupported_recommendation')
        if result.get('solver_status') != 'ok':
            reasons.append('solver_failure')
        for field in ('incumbent_modeled_cost', 'recommended_modeled_cost', 'numerical_gap'):
            if not _number(result.get(field)) or result[field] < 0:
                reasons.append('invalid_value:' + field)
        tolerance = snapshot.get('max_numerical_gap')
        if not _number(tolerance) or tolerance < 0:
            reasons.append('invalid_gap_tolerance')
        elif _number(result.get('numerical_gap')) and result['numerical_gap'] > tolerance:
            reasons.append('excess_numerical_gap')
        if not reasons:
            out.update(status='advice', recommended_x=choice,
                       service_id=snapshot['service_id'], profile_hash=snapshot['profile_hash'],
                       as_of=snapshot['decision_at'], expires_at=snapshot['expires_at'],
                       provenance=snapshot.get('provenance', 'unspecified'),
                       modeled_costs={k: result[k] for k in ('incumbent_modeled_cost', 'recommended_modeled_cost')},
                       numerical_gap=result['numerical_gap'])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        reasons.append('invalid_input:' + type(exc).__name__)
    return out
