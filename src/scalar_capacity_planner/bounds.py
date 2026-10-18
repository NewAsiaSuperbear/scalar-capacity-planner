"""Independent exact-rational objective bounds and feasible probability laws."""
from fractions import Fraction as F
from math import comb, nextafter, inf
from .model import rational as R, minimum_quadratic


def poly(c,t):
    return sum((v*t**i for i,v in enumerate(c)),F(0))


def add(*polys):
    return [sum((p[i] if i<len(p) else F(0) for p in polys),F(0)) for i in range(max(map(len,polys)))]


def mul(a,b):
    out=[F(0)]*(len(a)+len(b)-1)
    for i,v in enumerate(a):
        for j,w in enumerate(b): out[i+j]+=v*w
    return out


def scale(a,s): return [s*v for v in a]


def bernstein_lower(c,lo,hi,parts=32):
    """Exact lower bound via convex hull of Bernstein coefficients on subintervals."""
    n=len(c)-1; answer=None
    for j in range(parts):
        l=lo+(hi-lo)*F(j,parts); width=(hi-lo)/parts
        power=[sum((c[i]*comb(i,k)*l**(i-k)*width**k for i in range(k,n+1)),F(0)) for k in range(n+1)]
        bern=[sum((power[k]*F(comb(i,k),comb(n,k)) for k in range(i+1)),F(0)) for i in range(n+1)]
        val=min(bern); answer=val if answer is None else min(answer,val)
    return answer


def upper_certificate(spec,x,Y,majorant):
    A,beta,gamma=map(R,majorant)
    gamma=max(F(0),gamma)
    a,b,d=map(lambda q:list(map(R,q)),(spec.a,spec.b,spec.d))
    p,h,y=R(spec.p),R(spec.h),R(Y); c=R(spec.mad_center)
    residual=add(d,scale(b,-F(x))); amin=minimum_quadratic(spec.a)
    correction=F(0)
    for lo,hi,sign in ((F(-1),c,-1),(c,F(1),1)):
        H=[A-sign*c*gamma,beta+sign*gamma]
        constraints=[H,add(mul(a,H),scale(residual,-p)),add(H,scale(residual,-h),[-p*y],scale(a,h*y))]
        for coeff,denom in zip(constraints,(F(1),amin,F(1))):
            correction=max(correction,-bernstein_lower(coeff,lo,hi)/denom)
    lo,hi=map(R,spec.mean_band)
    value=A+correction+max(beta*lo,beta*hi)+gamma*R(spec.mad_upper)
    return value, correction


def recourse_exact(spec,x,Y,t):
    a,b,d=(poly(list(map(R,c)),t) for c in (spec.a,spec.b,spec.d))
    r=d-b*x; p,h,y=R(spec.p),R(spec.h),R(Y)
    return max(F(0),p*r/a,h*r+(p-h*a)*y)


def feasible_lower(spec,x,Y,grid,weights):
    """Validate normalized rational weights; if necessary mix with feasible anchor."""
    points=list(map(R,grid)); w=[max(F(0),R(v)) for v in weights]
    total=sum(w,F(0))
    if total<=0: w=[F(1)];points=[R(spec.anchor)]
    else: w=[v/total for v in w]
    center=R(spec.mad_center);lo,hi=map(R,spec.mean_band);mad=R(spec.mad_upper)
    mean=sum((v*t for v,t in zip(w,points)),F(0)); dev=sum((v*abs(t-center) for v,t in zip(w,points)),F(0))
    anchor=(max(lo,center-mad)+min(hi,center+mad))/2
    anchor_dev=abs(anchor-center); mix=F(0)
    for violation,slack in ((lo-mean,anchor-lo),(mean-hi,hi-anchor),(dev-mad,mad-anchor_dev)):
        if violation>0: mix=max(mix,violation/(violation+slack))
    w=[v*(1-mix) for v in w]; points.append(anchor);w.append(mix)
    mean=sum((v*t for v,t in zip(w,points)),F(0));dev=sum((v*abs(t-center) for v,t in zip(w,points)),F(0))
    assert sum(w,F(0))==1 and lo<=mean<=hi and dev<=mad
    value=sum((v*recourse_exact(spec,x,Y,t) for v,t in zip(w,points)),F(0))
    return value, {"mean":float(mean),"mad":float(dev),"anchor_mix":float(mix),"atoms":sum(v>0 for v in w)}


def outward(value,upper):
    return nextafter(float(value),inf if upper else -inf)
