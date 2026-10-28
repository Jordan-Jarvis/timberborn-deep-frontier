"""ChemicalWorks: oil-derived resins, plastics and sulfur (8 workers, 3500 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the barrel store.

HERO: a 13-layer riveted fractionating column ringed by three steel platforms
      with a caged ladder, its vapour line dropping into a fin-fan cooler,
      beside a lattice flare stack with a live flame.
ROOF: one long teal gable (ridge along X) on the steel-framed reactor hall, a
      small cross-gable on the timber control shed.

Plan (10 x 9 tiles): control shed front-left with the door; a row of three
agitated reactors on a concrete apron in front of a steel pipe-rack catwalk;
the reactor hall behind; a spherical product tank front-right; the fin-fan
cooler, the column and the flare stack along the right side.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, CYAN, GLOW, LAYER_GAP
import lategame_industry_parts as P
from industrial_facades import building_portal
from architectural_windows import window

IDENT = 'ChemicalWorks'
FOOTPRINT = (10, 9)
HEIGHT = 14
FRAME_END = 121
HERO = ('A 13-layer riveted fractionating column with three ring platforms and a caged ladder, '
        'its vapour line dropping into a fin-fan cooler, beside a lattice flare stack with a live flame.')

DOOR_X = 1.5
COLUMN = (8.3, 6.45)
COLUMN_R = .62
REACTORS = (3.68, 5.0, 6.32)   # footing rings (r + .1) stay apart
REACTOR_Y = 1.05
REACTOR_R = .55


def room(g, x0, y0, x1, y1, bottom, top, *, infill, post, post_w=.16, windows=None, style='factory',
         scale=.8, bays=None):
    """Four framed walls meeting at closed corners (front/back walls run past
    the side walls, side walls butt into them)."""
    windows = windows or {}
    for name, axis, plane, start, end, out in (
            ('front', 'X', y0, x0 - .05, x1 + .05, -1), ('back', 'X', y1, x0 - .05, x1 + .05, 1),
            ('left', 'Y', x0, y0 + .05, y1 - .05, -1), ('right', 'Y', x1, y0 + .05, y1 - .05, 1)):
        K.frame_wall(g, axis, plane, start, end, bottom, top, outward=out, infill=infill, post=post,
                     post_w=post_w, windows=windows.get(name), window_style=style, window_scale=scale,
                     bays=(bays or {}).get(name))


# ---------------------------------------------------------------- control shed

def control_shed(g):
    # Front face .15 off the tile edge so the native path stub meets the door.
    # x1 .05 short of x = 3 so the shed's plinth foot never overlaps the apron's.
    x0, y0, x1, y1 = 0.0, .15, 2.95, 3.0
    P.plinth(g, x0, y0, x1, y1, 1.3, door=(DOOR_X, 1.0, 1.0))
    building_portal(g, DOOR_X, y0 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0, 0], 'outward': [0, -1]})
    # Timber upper storey with orange plaster infill.
    wx0, wy0, wx1, wy1 = x0 + .12, y0 + .12, x1 - .12, y1 - .12
    bottom, eave = 1.32, 3.05
    room(g, wx0, wy0, wx1, wy1, bottom, eave + .03, infill=ORANGE, post=WOOD, post_w=.15,
         style='grand', scale=.72,
         windows={'front': [(.95, 2.2), (2.55, 2.2)], 'left': [(1.5, 2.2)], 'right': [(1.0, 2.2), (2.0, 2.2)]},
         bays={'front': 3, 'back': 3, 'left': 2, 'right': 2})
    P.plank_roof(g, wx0, wy0, wx1, wy1, eave, eave + 1.05, ridge_axis='Y', overhang=.18, plank=.28)
    # Instrument board beside the door: gauges on a painted panel.
    g.box((2.45, y0 - .03, .72), (.62, .06, .5), PAINTED)
    for i, gx in enumerate((2.27, 2.63)):
        P.gauge(g, gx, y0 - .06, .82, 'front', .085)
    g.box((2.45, y0 - .075, .52), (.36, .03, .05), BRASS)
    for k, lx in enumerate((2.25, 2.4, 2.55, 2.7)):
        g.cylinder((lx, y0 - .09, .62), .022, .03, CYAN if k % 2 == 0 else IRON, 'Y', 8)
    K.lamp(g, DOOR_X - .62, y0 - .04, 1.12, face='front')
    K.lamp(g, DOOR_X + .62, y0 - .04, 1.12, face='front')
    # Stovepipe chimney on the rear roof slope.
    K.stack(g, 1.0, 2.0, 3.55, 1.1, emits='smoke', r=.11, taper=.9, bands=2)


# ---------------------------------------------------------------- reactors

def reactors(g, parts):
    ax0, ay0, ax1, ay1 = 3.0, 0.0, 7.0, 2.0   # apron on whole tiles
    base = P.plinth(g, ax0, ay0, ax1, ay1, .42)
    for i, x in enumerate(REACTORS):
        top = K.tank(g, x, REACTOR_Y, base, REACTOR_R, 2.55, mat=PAINTED, bands=3, roof='dome')
        dome_top = top + (REACTOR_R + .03) * .45
        # Bolted manway on the front.
        mz = base + .95
        g.cylinder((x, REACTOR_Y - REACTOR_R - .035, mz), .2, .07, IRON, 'Y', 16)
        P.hoop(g, (x, REACTOR_Y - REACTOR_R - .075, mz), .22, .05, .03, BRASS, axis='Y', segments=16)
        for k in range(8):
            a = k * math.pi / 4
            K.stud(g, (x + math.cos(a) * .17, REACTOR_Y - REACTOR_R - .075, mz + math.sin(a) * .17), 'Y', .02)
        # Bottom outlet with a valve, running to the front.
        P.pipe(g, [(x + .25, REACTOR_Y - .3, base + .45), (x + .25, ay0 - .02 + .0, base + .45)], .055, flanges=False)
        P.valve(g, (x + .25, REACTOR_Y - REACTOR_R - .12, base + .45), 'up', .1, stem=.18)
        # Sight gauge and dial on the shell.
        P.gauge(g, x - .3, REACTOR_Y - REACTOR_R + .07, base + 1.75, 'front', .08)
        # Agitator drive: motor and gearbox on a steel saddle over the dome.
        sz = dome_top - .02
        g.box((x, REACTOR_Y, sz + .05), (.62, .5, .1), IRON)
        g.box((x, REACTOR_Y, sz + .25), (.36, .36, .3), PAINTED)
        for dx in (-.16, .16):
            K.stud(g, (x + dx, REACTOR_Y - .181 - .01, sz + .25), 'Y', .02)
        P.motor(g, (x, REACTOR_Y, sz + .95), .16, .42, axis='Z')
        # Spinning coupling (visible between gearbox and motor).
        c = Geometry(f'ChemicalWorks.Agitator{i + 1}', (x, REACTOR_Y, sz + .55))
        P.lathe(c, (x, REACTOR_Y, sz + .55), [(.06, -.16), (.06, -.07), (.17, -.07), (.17, -.02),
                                               (.06, -.02), (.06, .02), (.17, .02), (.17, .07),
                                               (.06, .07), (.06, .16)], IRON, segments=12)
        for k in range(4):
            a = k * math.pi / 2
            c.box((x + math.cos(a) * .12, REACTOR_Y + math.sin(a) * .12, sz + .55), (.045, .045, .17), BRASS)
        parts.append((c, 'SPIN_Z', 3))
        # Vapour nozzle from the dome up to the rack.
        P.pipe(g, [(x - .26, REACTOR_Y + .1, dome_top - .12), (x - .26, REACTOR_Y + .1, 3.75),
                   (x - .26, 3.3, 3.75)], .06)


# ---------------------------------------------------------------- pipe rack

def pipe_rack(g):
    x0, x1 = 3.3, 7.3
    ya, yb = 2.72, 3.42
    bents = (3.45, 4.7, 5.95, 7.15)
    for x in bents:
        for y in (ya, yb):
            P.pier(g, x, y, 0, .5, .3)
            g.box((x, y, (.55 + 2.92) / 2), (.16, .16, 2.92 - .55), IRON)
        g.box((x, (ya + yb) / 2, 2.89), (.14, yb - ya + .12, .14), IRON)
        g.beam((x, ya + .08, 2.3), (x, ya + .4, 2.82), .07, mat=IRON)
    # Longitudinal stringers under the catwalk.
    for y in (ya + .1, yb - .1):
        g.box(((x0 + x1) / 2, y, 2.915), (x1 - x0 - .1, .1, .1), IRON)
    P.grating(g, x0, ya - .08, x1, ya + .45, 3)
    P.rail(g, [(x0, ya - .045), (x1 - .03, ya - .045)], 3)
    # Pipe bundle on chairs behind the walkway.
    for k, (r, mat) in enumerate(((.075, IRON), (.06, PAINTED), (.05, IRON))):
        y = ya + .55 + k * .17
        z = 3.0 + r + .01
        P.pipe(g, [(x0 - .12 + .14 * k, y, z), (x1 + .05 - .15 * k, y, z)], r, mat)
    for x in bents:
        g.box((x, yb - .12, 3.03), (.2, .3, .06), IRON)
    # Ladder from the yard to the catwalk at the left end.
    K.ladder(g, x0 + .3, ya - .08, 0, 3, face='front', cage=True)


# ---------------------------------------------------------------- reactor hall

def hall(g, parts):
    x0, y0, x1, y1 = .1, 4.1, 5.9, 8.9   # plinth (walls + .1) on tiles 0..6 x 4..9
    P.plinth(g, x0 - .1, y0 - .1, x1 + .1, y1 + .1, 1.2)
    bottom, eave = 1.222, 4.35
    room(g, x0, y0, x1, y1, bottom, eave + .03, infill=FORGED, post=IRON, post_w=.16, style='factory', scale=.9,
         windows={'front': [(1.0, 2.0), (2.0, 2.0), (4.0, 2.0), (5.0, 2.0)],
                  'left': [(4.8, 2.2), (5.8, 2.2), (6.8, 2.2), (7.8, 2.2), (4.8, 3.5), (7.8, 3.5)],
                  'back': [(1.0, 2.6), (3.0, 2.6), (5.0, 2.6)],
                  'right': [(5.3, 2.6), (7.3, 2.6)]},
         bays={'front': 6, 'back': 6, 'left': 5, 'right': 5})
    # Orange plaster band at the gable ends is the native accent; ridge along X.
    ridge = P.plank_roof(g, x0, y0, x1, y1, eave, eave + 1.55, ridge_axis='X', overhang=.2, plank=.32,
                         gable_mat=ORANGE)
    # Turbine roof ventilators on the ridge.
    for i, x in enumerate((1.9, 3.5, 5.1)):
        g.cylinder((x, (y0 + y1) / 2, ridge + .18), .16, .36, IRON, 'Z', 12)
        g.cylinder((x, (y0 + y1) / 2, ridge + .375), .2, .03, BRASS, 'Z', 12)
        v = Geometry(f'ChemicalWorks.RoofVent{i + 1}', (x, (y0 + y1) / 2, ridge + .52))
        P.lathe(v, (x, (y0 + y1) / 2, ridge + .52), [(.2, -.13), (.24, -.05), (.24, .05), (.16, .12), (0, .17)],
                FORGED, segments=12)
        parts.append((v, 'SPIN_Z', 2 if i != 1 else -2))
    # Process steam pipe along the left gable wall to a wall valve station.
    # (The gable now stands on the footprint edge: pipe kept close, valve
    # wheel up and the lamp on the front wall, inside the envelope.)
    P.pipe(g, [(x0 - .2, 4.4, .5), (x0 - .2, 4.4, 3.4), (x0 - .2, 7.4, 3.4), (x0 - .2, 7.4, 1.6)], .07)
    P.valve(g, (x0 - .2, 5.8, 3.4), 'up', .13)
    for y in (4.4, 7.4):
        g.box((x0 - .145, y, 3.4), (.13, .1, .1), IRON)
    P.gauge(g, x0 - .16, 6.2, 1.75, 'left', .1)
    K.lamp(g, 3.0, y0 - .16, 1.85, face='front')


# ---------------------------------------------------------------- column

def column(g, parts):
    cx, cy = COLUMN
    r = COLUMN_R
    # Octagonal concrete footing and flared steel skirt.
    K.revolve(g, (cx, cy, 0), [(1.05, 0), (1.05, .45), (.95, .55)], CONCRETE, segments=8, phase=math.pi / 8)
    K.revolve(g, (cx, cy, .55), [(r + .14, 0), (r + .14, .5), (r, .9)], IRON, segments=16)
    top = 12.4
    K.revolve(g, (cx, cy, 1.4), [(r, 0), (r, top - 1.4)], IRON, segments=16, cap_bottom=False, cap_top=False)
    K.dome(g, (cx, cy, top), r + .025, IRON, segments=16, squash=.55)
    # Painted bands at each tray section; rivet seams between.
    for z in [1.9 + 1.1 * k for k in range(10)]:
        if not 4.2 < z < 7.8:
            K.band(g, (cx, cy, 0), r, z, .08, PAINTED, segments=16)
    # Timber-lagged insulation jacket round the hot middle section, strapped.
    K.revolve(g, (cx, cy, 4.25), [(r + .045, 0), (r + .045, 3.5)], FORGED, segments=16, phase=math.pi / 24)
    for z in (4.45, 5.6, 6.75, 7.55):
        K.band(g, (cx, cy, 0), r + .045, z, .07, IRON, segments=16)
    # Ring platforms at whole layers with rails and knee brackets.
    for z in (4, 8, 12):
        P.annulus(g, (cx, cy), r - .1, 1.18, z - .08, z, IRON, segments=16)
        for k in range(8):
            a = k * math.pi / 4 + math.pi / 8
            g.beam((cx + math.cos(a) * r, cy + math.sin(a) * r, z - .7),
                   (cx + math.cos(a) * 1.08, cy + math.sin(a) * 1.08, z - .1), .07, mat=IRON)
        P.ring_rail(g, (cx, cy), 1.12, z, height=.62, posts=12, gap=(math.pi * .88, math.pi * 1.12))
    # Caged ladder up the front face, through the rail gaps.
    K.ladder(g, cx - 1.2, cy, 0, 12.6, face='left', cage=True)
    # Side-draw nozzles with flanges and a reflux line down the right side.
    for z, a in ((3.2, -.25), (5.6, .35), (7.3, -.6), (9.6, .2)):
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        P.pipe(g, [(px - .02, py, z), (cx + math.cos(a) * (r + .32), cy + math.sin(a) * (r + .32), z)], .06)
    P.pipe(g, [(cx + r + .32, cy + .2, 9.6), (cx + r + .32, cy + .2, .8), (cx + r - .05, cy + .2, .8)], .055)
    for z in (2.2, 6.2, 10.2):
        g.box((cx + r + .17, cy + .2, z), (.3, .08, .08), IRON)
    P.gauge(g, cx - .2, cy - r - .015, 2.3, 'front', .09)
    # Bolted manways just above each platform, facing the yard.
    for z, a in ((1.7, 1.3 * math.pi), (4.75, 1.25 * math.pi), (8.75, 1.32 * math.pi)):
        ux, uy = math.cos(a), math.sin(a)
        at = lambda d: (cx + ux * d, cy + uy * d, z)
        P.tube(g, at(r - .08), at(r + .1), .19, IRON, segments=16)
        P.tube(g, at(r + .1), at(r + .16), .24, PAINTED, segments=16)
        for k in range(8):
            b = k * math.pi / 4
            off = (-uy * math.cos(b) * .2, ux * math.cos(b) * .2, math.sin(b) * .2)
            p = at(r + .16)
            P.tube(g, (p[0] + off[0], p[1] + off[1], p[2] + off[2]),
                   (p[0] + off[0] + ux * .025, p[1] + off[1] + uy * .025, p[2] + off[2]), .022, BRASS, segments=6)
        p = at(r + .16)
        P.tube(g, (p[0] - uy * .1, p[1] + ux * .1, z), (p[0] - uy * .1 + ux * .06, p[1] + ux * .1 + uy * .06, z),
               .03, IRON, segments=6)
    # Vapour line: out of the crown, over and down to the cooler header.
    vz = top + .62
    P.pipe(g, [(cx, cy, top + .3), (cx, cy, vz), (cx, 4.0 + .0, vz), (cx, 4.0, 3.55)], .1)
    for z in (5.0, 8.0, 11.0):
        g.box((cx, 4.0 + .13, z), (.1, .2, .1), IRON)
    # Beacon on a short mast at the crown.
    g.box((cx + .3, cy + .3, top + .55), (.07, .07, .9), IRON)
    pivot = K.beacon(g, cx + .3, cy + .3, top + 1.0)
    parts.append((K.beacon_shutter(*pivot, 'ChemicalWorks.Beacon'), 'SPIN_Z', 2))


# ---------------------------------------------------------------- cooler

def cooler(g, parts):
    x0, y0, x1, y1 = 7.55, 3.7, 9.85, 5.2
    zt = 2.7
    for x in (x0 + .15, x1 - .15):
        for y in (y0 + .15, y1 - .15):
            P.pier(g, x, y, 0, .4, .3)
            g.box((x, y, (.45 + zt) / 2), (.14, .14, zt - .45), IRON)
    for x in (x0 + .15, x1 - .15):
        g.beam((x, y0 + .15, .6), (x, y1 - .15, zt - .2), .07, mat=IRON)
    # Header boxes and fin bank.
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, zt + .08), (x1 - x0, y1 - y0, .16), IRON)
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, zt + .36), (x1 - x0 - .3, y1 - y0 - .1, .4), FORGED)
    for x in (x0 + .07, x1 - .07):
        g.box((x, (y0 + y1) / 2, zt + .36), (.18, y1 - y0 + .04, .46), PAINTED)
    # Fan rings and rotors.
    for i, x in enumerate((x0 + .6, x1 - .6)):
        cy = (y0 + y1) / 2
        P.hoop(g, (x, cy, zt + .7), .5, .04, .26, IRON, segments=12)
        P.hoop(g, (x, cy, zt + .85), .53, .06, .05, PAINTED, segments=12)
        g.box((x, cy, zt + .62), (.94, .06, .05), IRON)
        g.cylinder((x, cy, zt + .7), .08, .14, IRON, 'Z', 10)
        parts.append((P.fan(f'ChemicalWorks.CoolerFan{i + 1}', x, cy, zt + .78, .42, blades=5), 'SPIN_Z', 4 if i else -4))
    # Outlet line down to the spherical tank.
    P.pipe(g, [(x0 + .2, y0 + .1, zt + .1), (x0 + .2, 2.7, zt + .1), (x0 + .2, 2.7, 2.7)], .07)


# ---------------------------------------------------------------- sphere

def product_sphere(g):
    cx, cy, cz, r = 8.65, 1.45, 2.05, 1.08
    legs = 6
    for k in range(legs):
        a = k * 2 * math.pi / legs + math.pi / 6
        lx, ly = cx + math.cos(a) * (r - .02), cy + math.sin(a) * (r - .02)
        P.pier(g, lx, ly, 0, .35, .28)
        g.box((lx, ly, (.4 + cz) / 2), (.14, .14, cz - .4), IRON)
    for k in range(legs):
        a0 = k * 2 * math.pi / legs + math.pi / 6
        a1 = a0 + 2 * math.pi / legs
        p = (cx + math.cos(a0) * (r + .05), cy + math.sin(a0) * (r + .05))
        q = (cx + math.cos(a1) * (r + .05), cy + math.sin(a1) * (r + .05))
        if k % 2 == 0:
            g.beam((p[0], p[1], .5), (q[0], q[1], cz - .35), .05, mat=IRON)
        else:
            g.beam((q[0], q[1], .5), (p[0], p[1], cz - .35), .05, mat=IRON)
    P.sphere(g, (cx, cy, cz), r, IRON, segments=16, rings=14)
    P.hoop(g, (cx, cy, cz), r + .035, .07, .1, PAINTED, segments=16)
    # Top nozzle, relief valve and a small crown platform.
    g.cylinder((cx, cy, cz + r + .08), .14, .2, IRON, 'Z', 12)
    P.hoop(g, (cx, cy, cz + r + .19), .2, .06, .04, BRASS)
    P.pipe(g, [(cx + .25, cy, cz + r - .03), (cx + .25, cy, cz + r + .35)], .045, flanges=False)
    g.cylinder((cx + .25, cy, cz + r + .42), .07, .12, BRASS, 'Z', 10)
    P.gauge(g, cx - .45, cy - .87, cz - .1, 'front', .08)
    # Bottom draw-off to a filling valve at the front.
    P.pipe(g, [(cx, cy, cz - r + .02), (cx, cy, .55), (cx, .25, .55)], .06)
    P.valve(g, (cx, .55, .55), 'up', .11, stem=.2)
    K.ladder(g, cx + r + .02, cy, 0, cz + .2, face='right', cage=False)


# ---------------------------------------------------------------- flare

def flare(g, parts):
    x0, y0, x1, y1 = 9.15, 8.15, 9.8, 8.8
    top = 10.8
    P.lattice_tower(g, x0, y0, x1, y1, 0, top, bays=8, w=.09)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    g.cylinder((cx, cy, .3), .22, .6, CONCRETE, 'Z', 12)
    K.revolve(g, (cx, cy, .6), [(.12, 0), (.12, top + .5 - .6)], IRON, segments=12)
    K.revolve(g, (cx, cy, top + .5), [(.12, 0), (.19, .1), (.19, .45), (.16, .5)], IRON, segments=12)
    g.ring((cx, cy, top + .93), .2, .05, .08, BRASS, 'Z', 12)
    # Pilot line up the tower.
    P.pipe(g, [(x1 - .02, cy, .3), (x1 - .02, cy, top + .7), (cx + .16, cy, top + .7)], .03, flanges=False)
    for k in range(3):
        g.box((cx, cy, 2.8 + k * 3), (.36, .36, .06), IRON)
    flame = Geometry('ChemicalWorks.FlareFlame', (cx, cy, top + .95))
    K.revolve(flame, (cx, cy, top + .95), [(.13, 0), (.15, .12), (.1, .4), (.04, .62), (0, .72)], GLOW, segments=8)
    parts.append((flame, 'FLAME', 0))
    # Vanilla smoke above the flame tip (the flame itself is the animated part).
    K.emitter(g, 'smoke', cx, cy, top + .95 + .72, .15)
    # Knock-out drum feeding the flare, between it and the column.
    K.revolve(g, (8.8, 8.45, 0), [(.42, 0), (.42, .2)], CONCRETE, segments=16)
    K.tank(g, 8.65, 8.45, .2, .3, 1.0, mat=PAINTED, bands=2, roof='dome', segments=16)
    P.pipe(g, [(8.65, 8.45, 1.55), (8.65, 8.45, 1.9), (cx, 8.45, 1.9), (cx, 8.45, 1.0)], .06, flanges=False)


def build(g, parts):
    control_shed(g)
    reactors(g, parts)
    pipe_rack(g)
    hall(g, parts)
    column(g, parts)
    cooler(g, parts)
    product_sphere(g)
    flare(g, parts)
