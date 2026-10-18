"""Explicit local translation of a serialized PlanResult, not live integration.

Caller-supplied identity labels bind a result to a snapshot by convention only.
This module neither verifies that binding nor authenticates planner provenance.
"""
import math
from shadow_adapter import GATES


def unvalidated_gates():
    """Numerical verification never supplies empirical validation evidence."""
    return {key: {'passed': False, 'evidence_ref': None} for key in GATES}


def translate_plan_result(plan, *, service_id, profile_hash, incumbent_x):
    """Map package PlanResult dict to guard fields; invalid input fails closed.

    The package's global `gap` maps to `numerical_gap`; action gaps must not
    replace it. Modeled costs are conservative objective upper bounds, not
    observations or estimated cash savings. The caller must identify incumbent.
    """
    out = dict(service_id=service_id, profile_hash=profile_hash,
               solver_status='failed', recommended_x=None,
               incumbent_modeled_cost=None, recommended_modeled_cost=None,
               numerical_gap=None, identity_binding='caller_asserted_unverified')
    try:
        selected = plan['selected_x']
        if plan['status'] != 'verified' or type(selected) is not int:
            return out
        if type(incumbent_x) is not int:
            return out
        lower, upper, gap = (plan[k] for k in ('lower_bound', 'upper_bound', 'gap'))
        actions = plan['actions']
        matches = [a for a in actions if type(a.get('x')) is int and a['x'] == incumbent_x]
        if len(matches) != 1 or matches[0]['status'] != 'verified':
            return out
        incumbent_upper = matches[0]['upper_bound']
        values = (lower, upper, gap, incumbent_upper)
        if any(type(v) not in (float, int) or not math.isfinite(v) for v in values):
            return out
        if lower > upper or gap < 0 or not math.isclose(gap, upper-lower, rel_tol=1e-7, abs_tol=1e-12):
            return out
        out.update(solver_status='ok', recommended_x=selected,
                   incumbent_modeled_cost=incumbent_upper,
                   recommended_modeled_cost=upper, numerical_gap=gap,
                   numerical_lower_bound=lower, numerical_upper_bound=upper)
    except (KeyError, TypeError, ValueError):
        pass
    return out
