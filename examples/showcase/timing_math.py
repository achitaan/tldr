"""Exact interval arithmetic for the authored lesson, not a circuit simulator."""
from fractions import Fraction
import math


def timing_window(edge, setup, hold, valid_from, valid_until):
    values=(edge,setup,hold,valid_from,valid_until)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1000000 for v in values):
        raise ValueError('Finite nonnegative nanosecond values at most 1,000,000 required.')
    e,s,h,a,b=(Fraction(str(v)) for v in values)
    if b<a or e<s:
        raise ValueError('Ordered validity interval and nonnegative setup boundary required.')
    left,right=e-s,e+h
    before,after=left-a,b-right
    return {'required_start':float(left),'required_end':float(right),
            'setup_margin':float(before),'hold_margin':float(after),
            'passes':before>=0 and after>=0,'units':'ns',
            'scope':'receiving-register interval containment; not a physical simulation'}
