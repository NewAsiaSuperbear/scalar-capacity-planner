"""Immutable inputs; coefficient order is constant, linear, quadratic."""
from dataclasses import dataclass
from fractions import Fraction as F
import math


def rational(value):
    return F(float(value))


def minimum_quadratic(coefficients):
    c = tuple(map(rational, coefficients)) + (F(0),) * (3-len(coefficients))
    points = [F(-1), F(1)]
    if c[2] > 0:
        vertex = -c[1]/(2*c[2])
        if -1 <= vertex <= 1:
            points.append(vertex)
    return min(c[0]+c[1]*t+c[2]*t*t for t in points)


@dataclass(frozen=True)
class ModelSpec:
    a: tuple[float, ...]
    b: tuple[float, ...]
    d: tuple[float, ...]
    p: float
    h: float
    mean_band: tuple[float, float]
    mad_center: float
    mad_upper: float
    nmax: int
    support: tuple[float, float] = (-1.0, 1.0)

    def __post_init__(self):
        for name, length in (("a",3),("b",3),("d",2)):
            vals = tuple(float(v) for v in getattr(self,name))
            if not 1 <= len(vals) <= length or not all(map(math.isfinite,vals)):
                raise ValueError(f"{name} must have 1..{length} finite coefficients")
            object.__setattr__(self,name,vals)
        for name in ("mean_band","support"):
            vals=tuple(float(v) for v in getattr(self,name))
            if len(vals)!=2 or not all(map(math.isfinite, vals)):
                raise ValueError(f"{name} must contain two finite numbers")
            object.__setattr__(self,name,vals)
        for name in ("p","h","mad_center","mad_upper"):
            value=float(getattr(self,name))
            if not math.isfinite(value): raise ValueError(f"{name} must be finite")
            object.__setattr__(self,name,value)
        if self.support != (-1.,1.): raise ValueError("Supported uncertainty interval must equal [-1,1]")
        if self.p<=0 or self.h<=0: raise ValueError("p,h must be positive")
        if not -1<=self.mad_center<=1 or self.mad_upper<0: raise ValueError("invalid MAD")
        lo,hi=self.mean_band
        if not -1<=lo<=hi<=1: raise ValueError("invalid mean band")
        if isinstance(self.nmax,bool) or not isinstance(self.nmax,int) or not 0<=self.nmax<=1000:
            raise ValueError("nmax must be an integer in [0,1000]")
        if minimum_quadratic(self.a)<=rational(self.p)/rational(self.h):
            raise ValueError("Supported model requires certified min(a)>p/h")
        if minimum_quadratic(self.b)<=0: raise ValueError("b must be positive on support")
        if minimum_quadratic(self.d)<0: raise ValueError("demand must be nonnegative on support")

    @property
    def anchor(self):
        return min(max(self.mad_center,self.mean_band[0]),self.mean_band[1])

    @property
    def ambiguity_feasible(self):
        return abs(rational(self.anchor)-rational(self.mad_center))<=rational(self.mad_upper)
