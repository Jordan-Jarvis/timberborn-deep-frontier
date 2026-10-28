"""industrial_budget.py helpers as the industrial family uses them.

CementKiln, ConcreteMixer, StoneCrusher, MineralQuarry and the two pits import
their detail kit from here. Everything is industrial_budget.py; the fastener
helpers carry FASTENERS_INDUSTRIAL (see there): longer heads and diagonal
square heads, because these models have no bevel modifier. Other families
import industrial_budget.py directly and keep FASTENERS_SHARED.
"""
import industrial_budget as _b
from industrial_budget import (MODELS, BEVEL, open_box, prism, band, open_beam, rock, rock_heap, cask, round_pipe,
                               cage_lamp, machinery_shell, wheel, gauge)

_F = _b.FASTENERS_INDUSTRIAL


def bolt(g, p, axis='Y', r=.022, outward=None, n=6):
    _b.bolt(g, p, axis, r, outward, n, fasteners=_F)


def steel_bolt(g, p, axis='Y', r=.022):
    _b.steel_bolt(g, p, axis, r, fasteners=_F)


def square_nut(g, p, axis, r, outward):
    _b.square_nut(g, p, axis, r, outward, fasteners=_F)


def bracket(g, x, y, z, w=.22):
    _b.bracket(g, x, y, z, w, fasteners=_F)


def timber_column(g, x, y, bottom, top, w=.19):
    _b.timber_column(g, x, y, bottom, top, w, fasteners=_F)


def beam_joint(g, a, b, w=.18, depth=.18):
    _b.beam_joint(g, a, b, w, depth, fasteners=_F)


def sheet_roof(g, x0, y0, x1, y1, z0, z1, seed):
    _b.sheet_roof(g, x0, y0, x1, y1, z0, z1, seed, fasteners=_F)


def bin(g, p, size, stone=None, seed=0, *, proud_rivets=False):
    _b.bin(g, p, size, stone, seed, proud_rivets=proud_rivets, fasteners=_F)
