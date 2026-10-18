"""Reusable cubic SOS graph with independently certified bounds per integer action."""
from dataclasses import dataclass
from enum import Enum
import math
import threading
import cvxpy as cp
import numpy as np
from scipy.optimize import linprog
from .model import ModelSpec, rational as R
from .bounds import upper_certificate, feasible_lower, outward


class Status(str,Enum):
    VERIFIED="verified"
    UNKNOWN="unknown"
    INFEASIBLE="infeasible"
    SOLVER_ERROR="solver_error"


@dataclass(frozen=True)
class ActionResult:
    x: int
    status: Status
    solver_status: str
    objective: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    gap: float | None = None
    certificate_correction: float | None = None
    witness: dict | None = None
    message: str = ""


@dataclass(frozen=True)
class PlanResult:
    """Plan-level bounds for integer optimization.

    lower_bound bounds the minimum objective over every enumerated action.
    upper_bound bounds the selected action's objective. Their difference
    bounds the selected plan's suboptimality under the supplied model.
    Per-action bounds are available in actions.
    """
    status: Status
    selected_x: int | None
    objective: float | None
    lower_bound: float | None
    upper_bound: float | None
    gap: float | None
    actions: tuple[ActionResult,...]
    message: str


class CapacityPlanner:
    """One cache owns one immutable spec. Only k and Y may change per call.

    Not thread-safe by mutation: solve calls are serialized with an instance lock.
    """
    def __init__(self,spec:ModelSpec,grid_size:int=401):
        if not isinstance(spec,ModelSpec): raise TypeError("spec must be ModelSpec")
        if isinstance(grid_size,bool) or not isinstance(grid_size,int) or not 3<=grid_size<=100001:
            raise ValueError("grid_size must be integer in [3,100001]")
        self._spec=spec;self._lock=threading.Lock()
        self._grid=np.unique(np.r_[np.linspace(-1,1,grid_size),spec.anchor,spec.mad_center,spec.mean_band[0],spec.mean_band[1]])
        self._x=cp.Parameter(nonneg=True);self._Y=cp.Parameter(nonneg=True)
        self._v=cp.Variable(3);v=self._v
        a=np.pad(spec.a,(0,3-len(spec.a)));b=np.pad(spec.b,(0,3-len(spec.b)));d=np.pad(spec.d,(0,3-len(spec.d)))
        residual=[d[i]-b[i]*self._x for i in range(3)]
        constraints=[v[2]>=0]
        for l,u,sign in ((-1,spec.mad_center,-1),(spec.mad_center,1,1)):
            if l == u: continue  # the remaining closed interval includes this endpoint
            q0=v[0]-sign*spec.mad_center*v[2];q1=v[1]+sign*v[2]
            polynomials=[cp.hstack([q0,q1,0,0]),cp.hstack([a[0]*q0-spec.p*residual[0],a[0]*q1+a[1]*q0-spec.p*residual[1],a[1]*q1+a[2]*q0-spec.p*residual[2],a[2]*q1]),cp.hstack([q0-spec.h*residual[0]-spec.p*self._Y+spec.h*a[0]*self._Y,q1-spec.h*residual[1]+spec.h*a[1]*self._Y,-spec.h*residual[2]+spec.h*a[2]*self._Y,0])]
            for coeff in polynomials:
                Q=cp.Variable((2,2),symmetric=True);S=cp.Variable((2,2),symmetric=True)
                rep=cp.hstack([-l*Q[0,0]+u*S[0,0],Q[0,0]-2*l*Q[0,1]+2*u*S[0,1]-S[0,0],2*Q[0,1]-l*Q[1,1]+u*S[1,1]-2*S[0,1],Q[1,1]-S[1,1]])
                constraints += [Q>>0,S>>0,coeff==rep]
        lo,hi=spec.mean_band
        objective=v[0]+.5*(lo+hi)*v[1]+.5*(hi-lo)*cp.abs(v[1])+spec.mad_upper*v[2]
        self._problem=cp.Problem(cp.Minimize(objective),constraints)
        if not self._problem.is_dpp(): raise RuntimeError("internal graph is not DPP")

    @property
    def spec(self): return self._spec

    @property
    def is_dpp(self): return self._problem.is_dpp()

    def recourse(self,x,Y,t):
        if isinstance(x,bool) or not isinstance(x,(int,np.integer)) or not 0<=x<=self.spec.nmax:
            raise ValueError("x outside enumerated integer domain")
        if not math.isfinite(Y) or Y<0: raise ValueError("Y must be nonnegative and finite")
        t=np.asarray(t,dtype=float)
        if not np.all(np.isfinite(t)) or np.any(abs(t)>1): raise ValueError("t outside support")
        s=self.spec;a,b,d=(np.polynomial.polynomial.polyval(t,c) for c in (s.a,s.b,s.d));r=d-b*x
        return np.maximum.reduce([np.zeros_like(t),s.p*r/a,s.h*r+(s.p-s.h*a)*Y])

    def solve(self,k:float,Y:float,*,gap_tolerance:float=0.05,solver:str="CLARABEL") -> PlanResult:
        for name,val in (("k",k),("Y",Y),("gap_tolerance",gap_tolerance)):
            if not math.isfinite(val) or val<0: raise ValueError(f"{name} must be finite and nonnegative")
        with self._lock:
            return self._solve(float(k),float(Y),float(gap_tolerance),solver)

    def _solve(self,k,Y,tol,solver):
        s=self.spec
        if not s.ambiguity_feasible:
            return PlanResult(Status.INFEASIBLE,None,None,None,None,None,(),"Ambiguity class empty: exact Dirac/Jensen test.")
        self._Y.value=Y;actions=[]
        for x in range(s.nmax+1):
            self._x.value=x
            try:
                self._problem.solve(solver=solver,warm_start=True,enforce_dpp=True)
            except Exception as exc:
                actions.append(ActionResult(x,Status.SOLVER_ERROR,"exception",message=f"{type(exc).__name__}: {exc}"));continue
            status=str(self._problem.status)
            if status not in (cp.OPTIMAL,cp.OPTIMAL_INACCURATE) or self._v.value is None or not np.all(np.isfinite(self._v.value)):
                actions.append(ActionResult(x,Status.UNKNOWN,status,message="No finite majorant; gap unavailable."));continue
            try:
                ub,correction=upper_certificate(s,x,Y,self._v.value)
                grid=self._grid;q=self.recourse(x,Y,grid)
                lp=linprog(-q,A_ub=np.array([grid,-grid,abs(grid-s.mad_center)]),b_ub=np.array([s.mean_band[1],-s.mean_band[0],s.mad_upper]),A_eq=np.ones((1,len(grid))),b_eq=[1],bounds=(0,None),method="highs")
                weights=lp.x if lp.success else np.zeros(len(grid))
                lb,witness=feasible_lower(s,x,Y,grid,weights)
                fixed=R(k)*x;lb+=fixed;ub+=fixed
                if ub<lb: raise ArithmeticError("certified bound ordering failed")
                lower=outward(lb,False);upper=outward(ub,True);gap=outward(ub-lb,True)
                actions.append(ActionResult(x,Status.VERIFIED if gap<=tol else Status.UNKNOWN,status,float(self._problem.value)+k*x,lower,upper,gap,float(correction),witness,"Exact-rational envelope and feasible law checked; grid LP "+str(lp.status)))
            except Exception as exc:
                actions.append(ActionResult(x,Status.UNKNOWN,status,message=f"Bound diagnostic unavailable: {type(exc).__name__}: {exc}"))
        bounded=[a for a in actions if a.upper_bound is not None]
        if not bounded:
            st=Status.SOLVER_ERROR if all(a.status==Status.SOLVER_ERROR for a in actions) else Status.UNKNOWN
            return PlanResult(st,None,None,None,None,None,tuple(actions),"No independently bounded action; gap unavailable.")
        chosen=min(bounded,key=lambda a:a.upper_bound)
        lower=min(a.lower_bound for a in actions) if len(bounded)==len(actions) else None
        gap=math.nextafter(chosen.upper_bound-lower,math.inf) if lower is not None else None
        st=Status.VERIFIED if gap is not None and gap<=tol else Status.UNKNOWN
        return PlanResult(st,chosen.x,chosen.objective,lower,chosen.upper_bound,gap,tuple(actions),"Integer enumeration; global lower bound is minimum across all actions. Verified means objective gap within requested tolerance, not operational safety.")
