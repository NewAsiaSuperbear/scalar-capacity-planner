from dataclasses import FrozenInstanceError,replace
from fractions import Fraction
import json,os,subprocess,sys
import numpy as np
import pytest
from scipy.optimize import linprog
from scalar_capacity_planner import ModelSpec,CapacityPlanner,Status
from scalar_capacity_planner.bounds import upper_certificate,feasible_lower,recourse_exact


def spec(**changes):
    return replace(ModelSpec(a=(2,-.5),b=(3,-.5),d=(8,2),p=1,h=4,mean_band=(-.1,.1),mad_center=0,mad_upper=.5,nmax=4),**changes)


@pytest.mark.parametrize('changes',[{'a':(0,)},{'a':(.25,)},{'b':(1,2)},{'d':(-1,)},{'d':(1,2,3)},{'mad_upper':-1},{'mean_band':(.5,-.5)},{'mean_band':(-2,0)},{'nmax':2.5},{'nmax':True},{'p':float('nan')},{'support':(0,1)}])
def test_bad_inputs(changes):
    with pytest.raises(ValueError): spec(**changes)


def test_immutable_and_owned_coefficients():
    a=[2,-.5];s=spec(a=a);a[0]=100
    assert s.a==(2,-.5)
    with pytest.raises(FrozenInstanceError): s.p=5
    planner=CapacityPlanner(s)
    with pytest.raises(AttributeError): planner.spec=spec()
    with pytest.raises(TypeError): planner.solve(3,2,a=[100])


def test_recourse_matches_direct_lp():
    p=CapacityPlanner(spec())
    for x in range(5):
        for Y in (0,1.5,10):
            for t in np.linspace(-1,1,17):
                a=2-.5*t;b=3-.5*t;d=8+2*t
                direct=linprog([1,4],A_ub=[[-a,-1]],b_ub=[b*x-d],bounds=[(0,Y),(0,None)],method='highs')
                assert direct.success
                assert p.recourse(x,Y,t)==pytest.approx(direct.fun,abs=1e-9)


def test_cache_updates_and_global_bounds():
    p=CapacityPlanner(spec());assert p.is_dpp
    graph=id(p._problem)
    for k,Y in ((3,2),(2.5,1),(3,2)):
        r=p.solve(k,Y,gap_tolerance=.1)
        fresh=CapacityPlanner(spec()).solve(k,Y,gap_tolerance=.1)
        assert id(p._problem)==graph
        assert r.status==Status.VERIFIED
        assert r.lower_bound==min(a.lower_bound for a in r.actions)
        assert r.gap>=r.upper_bound-r.lower_bound
        assert r.selected_x==fresh.selected_x
        assert r.upper_bound==pytest.approx(fresh.upper_bound,abs=1e-4)
        assert all(a.lower_bound<=a.upper_bound for a in r.actions)


def test_statuses():
    empty=CapacityPlanner(spec(mean_band=(.8,.9),mad_center=0,mad_upper=.1)).solve(3,2)
    assert empty.status==Status.INFEASIBLE
    error=CapacityPlanner(spec()).solve(3,2,solver='NOT_A_SOLVER')
    assert error.status==Status.SOLVER_ERROR and error.gap is None
    unknown=CapacityPlanner(spec()).solve(3,2,gap_tolerance=0)
    assert unknown.status==Status.UNKNOWN
    degenerate=CapacityPlanner(spec(mean_band=(0,0),mad_upper=0)).solve(3,2)
    assert degenerate.status!=Status.INFEASIBLE


def test_independent_upper_repairs_bad_majorant():
    s=spec();ub,delta=upper_certificate(s,1,2,[-100,2,-1])
    assert delta>0
    assert ub>=max(recourse_exact(s,1,2,Fraction(str(t))) for t in (0,))


def test_lower_repairs_bad_law():
    s=spec();lb,w=feasible_lower(s,0,2,[-1,1],[0,1])
    assert -.1-1e-15<=w['mean']<=.1+1e-15 and w['mad']<=.5
    assert w['anchor_mix']>0


@pytest.mark.parametrize('k,Y,tol',[(float('inf'),2,.1),(3,-1,.1),(3,2,-1)])
def test_invalid_solve(k,Y,tol):
    with pytest.raises(ValueError): CapacityPlanner(spec()).solve(k,Y,gap_tolerance=tol)


def test_import_does_not_modify_environment_or_path():
    code='import os,sys,json; before=dict(os.environ); path=list(sys.path); import scalar_capacity_planner; print(json.dumps([before==dict(os.environ),path==sys.path]))'
    r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True)
    assert json.loads(r.stdout)==[True,True]


@pytest.mark.parametrize('center',[-1.,1.])
def test_endpoint_center_nonempty(center):
    p=CapacityPlanner(spec(mad_center=center,mad_upper=1.5))
    r=p.solve(3,2,gap_tolerance=.1)
    assert r.status==Status.VERIFIED
    assert r.gap is not None and all(a.upper_bound is not None for a in r.actions)


def test_quadratic_reserved_and_elastic():
    p=CapacityPlanner(spec(a=(2,-.2,.1),b=(3,.1,.2)))
    r=p.solve(3,2,gap_tolerance=.1)
    assert r.status==Status.VERIFIED
