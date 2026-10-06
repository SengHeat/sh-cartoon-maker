from __future__ import annotations

import math
from dataclasses import dataclass


def _smoothstep(value: float) -> float:
    value=max(0.0,min(1.0,value)); return value*value*(3-2*value)


def motion_progress(t: float, acceleration: float=.12, deceleration: float=.20) -> float:
    """Normalized trapezoidal travel with eased acceleration and braking."""
    t=max(0.0,min(1.0,t)); a=max(.01,min(.4,acceleration)); d=max(.01,min(.4,deceleration))
    vmax=1/(1-(a+d)/2)
    if t<a:return vmax*a*(t/a)**2/2
    before=vmax*a/2
    if t<=1-d:return before+vmax*(t-a)
    u=(t-(1-d))/d; at_brake=before+vmax*(1-d-a)
    return min(1.0,at_brake+vmax*d*(u-u*u/2))


def step_count(distance: float, step_length: float) -> int:
    if step_length<=0:raise ValueError("step_length must be positive")
    return max(1,math.ceil(abs(distance)/step_length))


@dataclass(frozen=True)
class FootState:
    planted: bool
    longitudinal: float
    lift: float
    phase: float


def foot_state(t: float, cycles: float, side_offset: float, distance: float, *, run: bool=False) -> FootState:
    """World-space foot trajectory: stance anchors are exactly constant."""
    g=max(0.0,t)*cycles+side_offset; index=math.floor(g); phase=g-index
    stance=.32 if run else .62; start=min(distance,index/cycles*distance); end=min(distance,(index+1)/cycles*distance)
    if phase<stance:return FootState(True,start,0.0,phase)
    u=_smoothstep((phase-stance)/(1-stance)); lift=math.sin(u*math.pi)*(.28 if run else .16)
    return FootState(False,start+(end-start)*u,lift,phase)


def jump_height(t: float, height: float) -> float:
    t=max(0.0,min(1.0,t)); return 4*height*t*(1-t)


def turn_progress(t: float) -> float:return _smoothstep(t)


def volume_preserving_scale(amount: float) -> tuple[float,float,float]:
    z=max(.85,min(1.20,1+amount)); xy=max(.85,min(1.20,1/math.sqrt(z))); return xy,xy,z
