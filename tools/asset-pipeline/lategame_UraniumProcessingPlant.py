"""Uranium Processing Plant: late-game study (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose drums and barrels on the dock.

HERO: the centrifuge cascade hall, an open-fronted steel gallery on a two-storey
concrete podium where two rows of tall spinning gas centrifuges stand under a
long monitor roof with a clerestory of native factory windows.
ROOF: teal plank monitor roof (twin lean-to slopes plus a raised clerestory
with its own gable).

Supporting masses: an orange-slurry settling thickener with a rotating rake
and a fixed worker bridge, a yellowcake drum dock with a jib hoist, the
lead-lined fuel vault, two riveted acid tanks, and the scrubber house with a
packed scrubber column and a 13-layer stack.

Animated: 12 centrifuge rotor drums (SPIN_Z), thickener rake arms (SPIN_Z),
jib hoist hook and drum (SLIDE_Z) with a stretching hoist cable
(CUSTOM_STRETCH), scrubber roof fan (SPIN_Z), three warning beacons (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from lategame_kit import (stud, CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW, plinth, frame_wall,
                          extrude_profile, revolve, band, dome, tank, stack, hollow_revolve, catwalk,
                          steel_rail, ladder, lamp, beacon, beacon_shutter, fan, bolt_row, redic_prop,
                          valve_wheel)
from lategame_nuclear_parts import (bx, Facer, trefoil, gauge, drum, riveted_panel, straight_pipe,
                                    pipe_path, valve, plank_slope, slope_quad, plank_gable,
                                    board_gable, frustum)
from industrial_facades import building_portal
from architectural_windows import window
import native_building_assets as native

IDENT = 'UraniumProcessingPlant'
FOOTPRINT = (12, 11)
HEIGHT = 14
HERO = ('Centrifuge cascade hall: an open-fronted steel gallery on a two-storey concrete podium '
        'with two rows of tall spinning centrifuges under a long monitor roof.')
FRAME_END = 121

# Hall frame lines
HX0, HX1 = .62, 7.68        # end wall planes
FY = .78                    # open cascade bay: front gantry column line
HYF, HYB = 2.6, 5.9         # hall front column line, back wall plane
DECK = 2.012                # podium coping top (hall work floor)
WALL_TOP = 6.2
SLOPE = .43
MON_F, MON_B = 3.5, 5.0     # monitor wall planes
MON_EAVE, MON_RIDGE = 7.75, 8.3
ROWS = (1.45, 3.45, 4.85)   # one open-air row, two rows inside the hall
COLS = [1.25 + i * 1.1 for i in range(6)]
CASING = 2.5                # centrifuge casing height above its pedestal
HEAD = DECK + .16 + CASING + .12 + .5   # top of the rotor drums
GANTRY = 6.0                # underside of the gantry cross beams


def roof_under(y):
    """Underside height of the lower roof slopes at depth y."""
    if y <= (HYF + HYB) / 2:
        return WALL_TOP + (y - HYF) * SLOPE
    return WALL_TOP + (HYB - y) * SLOPE


def podium(g):
    y0 = .15   # podium front (door) face .15 off the tile edge
    plinth(g, 0.0, y0, 8.0, 6.0, 2.0, door=(3.5, 1.0, 1.0))   # podium on tiles 0..8 x 0..6
    building_portal(g, 3.5, y0 - .12, 0)
    g.doorways.append({'id': 'Main', 'position': [3.5, y0, 0], 'outward': [0, -1]})
    for x in (.87, 1.81, 4.62, 5.56, 6.5, 7.43):
        window(g, x, y0, 1.12, .72, 'front', 'grand')
    # Side windows centred between the plinth's six pilaster bays.
    for i in range(6):
        y = y0 + (i + .5) * (6.0 - y0) / 6
        window(g, 0.0, y, 1.12, .72, 'left', 'grand')
        window(g, 8.0, y, 1.12, .72, 'right', 'grand')
    for x in (2.74, 4.62):
        window(g, x, 6.0, 1.12, .72, 'back', 'grand')
    lamp(g, 2.85, y0, 1.25, face='front')
    lamp(g, 4.4, y0, 1.25, face='front')
    trefoil(g, 3.5, y0, 1.55, face='front', r=.2)


def column(g, x, y, top):
    bx(g, x - .14, y - .14, DECK + .16, x + .14, y + .14, top, IRON)
    bx(g, x - .19, y - .19, DECK, x + .19, y + .19, DECK + .16, PAINTED)


def cascade_bay(g, parts):
    """Open-air front row under a steel pipe gantry, on the podium deck."""
    cols = [HX0, 2.4, 4.15, 5.9, HX1]
    for x in cols:
        column(g, x, FY, GANTRY + .14)
    # Lattice girder along the front: chords and alternating web diagonals.
    bx(g, HX0 - .2, FY - .08, GANTRY + .14, HX1 + .2, FY + .08, GANTRY + .28, IRON)
    bx(g, HX0 + .14, FY - .07, GANTRY - .62, HX1 - .14, FY + .07, GANTRY - .5, IRON)
    for a, b in zip(cols, cols[1:]):
        n = 3
        for k in range(n):
            xa = a + .14 + (b - a - .28) * k / n
            xb = a + .14 + (b - a - .28) * (k + 1) / n
            lo, hi = (GANTRY - .5, GANTRY + .14) if k % 2 == 0 else (GANTRY + .14, GANTRY - .5)
            # Alternate diagonals 12 mm thinner: consecutive ones meet at a
            # joint, where equal widths would share their side planes.
            g.beam((xa, FY, lo), (xb, FY, hi), .06 if k % 2 == 0 else .048, mat=IRON)
        steel_rail(g, (a + .19, FY - .22), (b - .19, FY - .22), DECK, pitch=.8)
    # Cross beams back to the hall columns, with hangers for the header.
    for x in cols:
        bx(g, x - .07, FY + .14, GANTRY, x + .07, HYF - .14, GANTRY + .14, IRON)
        g.beam((x, FY + .14, GANTRY - .45), (x, FY + .55, GANTRY), .07, mat=IRON)
    # Orange board on the girder.
    f = Facer(4.15, FY - .14, 0, 'front')
    riveted_panel(g, f, -.7, .7, GANTRY - .44, GANTRY + .06, 0, .04, ORANGE)
    for x in (2.4, 5.9):
        lamp(g, x, FY - .14, GANTRY - .9, face='front')
    # Side rails on the open bay ends.
    for x in (HX0 - .1, HX1 + .1):
        steel_rail(g, (x, FY + .2), (x, HYF - .2), DECK, pitch=.8)
    # Maintenance catwalk behind the open row at layer 4.
    catwalk(g, .9, 1.85, 7.4, 2.44, 4, rails=('front',), brackets=None)
    for x in (1.0, 2.75, 4.5, 6.25, 7.15):
        bx(g, x - .05, 2.3, DECK, x + .05, 2.4, 3.92, IRON)
    ladder(g, 7.55, 2.15, DECK, 4.0, face='right', cage=False)
    # Control desk at the left end of the bay.
    bx(g, .78, 1.98, DECK, 1.28, 2.28, DECK + .7, PAINTED)
    for x in (.9, 1.16):
        gauge(g, x, 1.98, DECK + .5, face='front', r=.08)
    bx(g, .83, 1.94, DECK + .25, 1.23, 1.98, DECK + .3, CYAN)


def hall(g, parts):
    podium(g)
    cascade_bay(g, parts)
    # Hall front colonnade, lintel and knee braces.
    cols = [HX0, 2.4, 4.15, 5.9, HX1]
    for x in cols:
        column(g, x, HYF, WALL_TOP - .1)
    bx(g, HX0 - .2, HYF - .15, WALL_TOP - .24, HX1 + .2, HYF + .15, WALL_TOP - .02, IRON)
    for a, b in zip(cols, cols[1:]):
        g.beam((a + .14, HYF, WALL_TOP - .9), (a + .7, HYF, WALL_TOP - .2), .09, mat=IRON)
        g.beam((b - .14, HYF, WALL_TOP - .9), (b - .7, HYF, WALL_TOP - .2), .09, mat=IRON)

    # Closed ends and back: steel frames, forged and orange infill.
    tiers = (3.35, 5.05)
    end_windows = [(u, z) for z in tiers for u in (3.26, 4.29, 5.33)]
    frame_wall(g, 'Y', HX0, HYF + .14, HYB - .05, DECK, WALL_TOP, outward=-1, infill=FORGED,
               bays=3, windows=end_windows, window_style='factory', window_scale=.9)
    frame_wall(g, 'Y', HX1, HYF + .14, HYB - .05, DECK, WALL_TOP, outward=1, infill=FORGED,
               bays=3, windows=end_windows, window_style='factory', window_scale=.9)
    frame_wall(g, 'X', HYB, HX0, HX1, DECK, WALL_TOP, outward=1, infill=ORANGE,
               windows=[(x, z) for z in tiers for x in (1.12, 3.14, 5.16, 7.18)], window_style='factory',
               window_scale=.9)

    # Lower roof slopes in native planks, buried into the monitor walls.
    t = .075
    yf_e, yb_e = HYF - .36, HYB + .24
    plank_slope(g, slope_quad(yf_e, roof_under(yf_e), MON_F, roof_under(MON_F), t), HX0 - .3, HX1 + .3)
    plank_slope(g, slope_quad(MON_B, roof_under(MON_B), yb_e, roof_under(yb_e), t), HX0 - .3, HX1 + .3)
    bx(g, HX0 - .27, yf_e - .02, roof_under(yf_e) - .1, HX1 + .27, yf_e + .05, roof_under(yf_e) + .02, WOOD)
    bx(g, HX0 - .27, yb_e - .05, roof_under(yb_e) - .1, HX1 + .27, yb_e + .02, roof_under(yb_e) + .02, WOOD)
    for ya, yb in ((yf_e, MON_F), (MON_B, yb_e)):
        y = (ya + yb) / 2
        g.box(((HX0 + HX1) / 2, y, roof_under(y) + t + .012 + .035), (HX1 - HX0 + .5, .07, .05), IRON)

    # Timber gable ends under the slopes and monitor.
    for x in (HX0, HX1):
        ya, yb = HYF + .14, HYB - .05
        board_gable(g, x, [(ya, MON_F, roof_under(ya) + .02, roof_under(MON_F) + .02),
                           (MON_F, MON_B, MON_EAVE - .13, MON_EAVE - .13),
                           (MON_B, yb, roof_under(MON_B) + .02, roof_under(yb) + .02)], WALL_TOP - .05,
                    thick=(.06, .08))
        s = -1 if x == HX0 else 1
        for y in (3.0, 3.9, 4.6, 5.5):
            top = MON_EAVE - .15 if MON_F < y < MON_B else roof_under(y) - .02
            bx(g, x + s * .06 - .02, y - .05, WALL_TOP - .02, x + s * .06 + .02, y + .05, top, WOOD)

    # Clerestory monitor: forged walls with native factory windows.
    for y, out in ((MON_F, -1), (MON_B, 1)):
        frame_wall(g, 'X', y, HX0, HX1, roof_under(MON_F) - .08, MON_EAVE, outward=out, infill=FORGED,
                   bays=7, windows=[(HX0 + (i + .5) * (HX1 - HX0) / 7, 7.2) for i in range(7)],
                   window_style='factory', window_scale=.8)
    plank_gable(g, HX0, MON_F, HX1, MON_B, MON_EAVE, MON_RIDGE, overhang=.18)
    mid = (MON_F + MON_B) / 2
    for x in (2.0, 4.15, 6.3):
        bx(g, x - .2, mid - .15, MON_RIDGE + .12, x + .2, mid + .15, MON_RIDGE + .36, IRON)
        bx(g, x - .26, mid - .21, MON_RIDGE + .36, x + .26, mid + .21, MON_RIDGE + .42, PAINTED)
    beacon_part(g, parts, 'MonitorBeacon', HX1 - .3, mid, MON_RIDGE + .155)

    # Centrifuge cascade: three rows of six.
    for row, y in enumerate(ROWS):
        for i, x in enumerate(COLS):
            centrifuge(g, parts, f'Centrifuge{row}{i}', x, y, dial=row == 0)
        hz = HEAD + .42
        straight_pipe(g, (HX0 + .1, y, hz), (HX1 - .1, y, hz), .075, flanges=False)
        if row == 0:   # the inner rows' collars stand under the roof, unseen
            for x in COLS:
                g.cylinder((x, y, HEAD + .22), .045, .3, BRASS, 'Z', 8)
        hang_top = GANTRY if y < HYF else roof_under(y) + .02
        for x in ((2.4, 4.15, 5.9) if y < HYF else (HX0 + .35, HX1 - .35)):
            bx(g, x - .04, y - .04, hz + .07, x + .04, y + .04, hang_top, IRON)
    # Cascade cross-over down the right end of the bay with a valve.
    pipe_path(g, [(HX1 - .3, ROWS[0], HEAD + .42), (HX1 - .3, ROWS[0], DECK + .4),
                  (HX1 - .3, ROWS[1], DECK + .4), (HX1 - .3, ROWS[1], HEAD + .42)], .07)
    valve(g, (HX1 - .3, 2.0, DECK + .4), .07, 'Y', wheel_face='left')
    # Pendant work lamps over the inner rows.
    for x in (1.8, 3.6, 5.4, 7.0):
        y = (ROWS[1] + ROWS[2]) / 2
        g.box((x, y, (5.55 + 7.6) / 2), (.03, .03, 7.6 - 5.55), IRON)
        revolve(g, (x, y, 5.4), [(.16, 0), (.06, .14), (.03, .16)], IRON, segments=8, cap_bottom=True)
        g.cylinder((x, y, 5.37), .07, .06, GLOW, 'Z', 8)


def beacon_part(g, parts, name, x, y, z):
    px, py, pz = beacon(g, x, y, z)
    parts.append((beacon_shutter(px, py, pz, name), 'SPIN_Z', 2))


def centrifuge(g, parts, name, x, y, *, dial=False):
    # Cast pedestal, iron casing with painted bands, brass collar. (Triangle
    # budget: eight sides, no splayed feet, which stood hidden inside the
    # pedestal; a gauge only on the open-air row.)
    bx(g, x - .3, y - .3, DECK, x + .3, y + .3, DECK + .16, CONCRETE)
    z0 = DECK + .16
    revolve(g, (x, y, z0), [(.26, 0), (.26, CASING), (.29, CASING + .12)], CONCRETE, segments=8)
    if dial:   # the open-air row; the inner rows' bands and dials stand unseen under the roof
        band(g, (x, y, 0), .26, z0 + 1.9, .07, BRASS, segments=8)
        gauge(g, x, y - .26, z0 + .95, face='front', r=.07)
    base = z0 + CASING + .12
    # Spinning rotor drum and domed cap in one surface, three strakes and an
    # orange index strip (the spin reads from those).
    r = Geometry(name, (x, y, base))
    # 12 sides: a vertex under every strake (strakes every 120 degrees).
    revolve(r, (x, y, base + .012), [(.3, 0), (.3, .5), (0, .62)], IRON, segments=12,
            cap_bottom=False)   # its underside sits on the casing
    for k in range(3):
        a = k * 2 * math.pi / 3
        r.box((x + math.cos(a) * .315, y + math.sin(a) * .315, base + .26), (.05, .05, .46), IRON)
    a = math.pi / 6
    r.box((x + math.cos(a) * .315, y + math.sin(a) * .315, base + .26), (.04, .04, .22), ORANGE)
    band(r, (x, y, 0), .3, base + .42, .05, BRASS, segments=12)
    parts.append((r, 'SPIN_Z', 4))


def thickener(g, parts):
    cx, cy = 10.0, 2.3
    hollow_revolve(g, (cx, cy, 0), [(1.6, 0), (1.6, 1.4)], .24, CONCRETE, segments=12)
    revolve(g, (cx, cy, .012), [(1.72, 0), (1.72, .21)], CONCRETE, segments=12)
    # Hoop on a hollow wall: a ring, not the kit's solid band.
    g.ring((cx, cy, 1.28), 1.63, .05, .1, IRON, 'Z', 12)
    # Orange yellowcake slurry, its edge buried in the wall (only its top shows).
    revolve(g, (cx, cy, .03), [(1.39, 0), (1.39, 1.12)], ORANGE, segments=12, cap_bottom=False)
    # Central drive pier and gear head.
    revolve(g, (cx, cy, 1.15), [(.22, 0), (.22, .45)], CONCRETE, segments=12)
    revolve(g, (cx, cy, 1.6), [(.3, 0), (.3, .22), (.2, .3), (.2, .42)], IRON, segments=12)
    g.ring((cx, cy, 1.71), .34, .06, .1, BRASS, 'Z', 12)
    g.box((cx + .3, cy, 1.85), (.3, .22, .2), PAINTED)
    # Fixed worker bridge from the rim to the drive head (steel grating).
    y0, y1 = cy - .28, cy + .28
    bx(g, cx + .3, y0, 1.88, cx + 1.85, y1, 1.96, IRON)
    for x in (cx + .5, cx + 1.0, cx + 1.5):
        g.box((x, cy, 1.966), (.03, .5, .012), IRON)
    for y in (y0 + .03, y1 - .03):
        steel_rail(g, (cx + .36, y), (cx + 1.82, y), 1.96, pitch=.5)
    for y in (y0 + .05, y1 - .05):
        g.beam((cx + 1.48, y, 1.4), (cx + 1.48, y, 1.88), .1, mat=IRON)
    # Rotating rake arms with hanging blades and a feed well ring.
    rake = Geometry('ThickenerRake', (cx, cy, 1.3))
    for s in (-1, 1):
        rake.beam((cx, cy, 1.36), (cx + s * 1.3, cy, 1.36), .09, .09, IRON)
        rake.beam((cx, cy, 1.5), (cx + s * 1.25, cy, 1.38), .05, .05, IRON)
        for k in range(4):
            xx = cx + s * (.4 + k * .27)
            rake.beam((xx, cy, 1.32), (xx, cy, 1.0), .04, mat=IRON)
            rake.box((xx, cy, 1.15), (.06, .2, .06), PAINTED)
    rake.ring((cx, cy, 1.33), .5, .05, .14, IRON, 'Z', 12)
    parts.append((rake, 'SPIN_Z', 1))
    # Overflow launder and outlet pipe to the dock.
    pipe_path(g, [(cx - 1.0, cy + 1.2, .9), (cx - 1.0, cy + 1.75, .9), (cx - 1.0, cy + 1.75, .35),
                  (7.85, cy + 1.75, .35)], .08)
    gauge(g, cx - 1.6, cy - .25, 1.0, face='left', r=.09)


def drum_dock(g, parts):
    x0, y0, x1, y1 = 8.03, 5.0, 12.0, 7.0   # drum dock on tiles 8..12 x 5..7, clear of the podium foot
    bx(g, x0, y0, 0, x1, y1, 1.0, CONCRETE)
    bx(g, x0 - .04, y0 - .04, .94, x1 + .04, y1 + .04, 1.012, CONCRETE)
    for x in (8.7, 9.6, 10.5, 11.4):
        bx(g, x - .07, y0 - .1, .15, x + .07, y0 - .04, .85, WOOD)
    # (Loose drums and barrels on the dock removed; the dock and jib hoist stay.)
    # Jib hoist: post, arm and tie, trolley; animated hook with a drum.
    px, py = 8.62, 5.35
    bx(g, px - .12, py - .12, 1.012, px + .12, py + .12, 4.6, IRON)
    bx(g, px - .2, py - .2, 1.012, px + .2, py + .2, 1.2, PAINTED)
    bx(g, px - .08, py - .1, 4.2, 11.3, py + .1, 4.38, IRON)
    g.beam((px, py, 4.55), (10.6, py, 4.38), .05, mat=IRON)
    bx(g, 10.0, py - .16, 3.98, 10.4, py + .16, 4.2, PAINTED)
    g.cylinder((10.2, py - .18, 4.09), .08, .05, BRASS, 'Y', 12)
    cable = Geometry('HoistCable', (10.2, py, 3.98))
    cable.box((10.2, py, 3.98 - .55), (.025, .025, 1.1), IRON)
    parts.append((cable, 'CUSTOM_STRETCH', .96 / 1.1))
    hook = Geometry('HoistHook', (10.2, py, 2.88))
    hook.box((10.2, py, 2.82), (.16, .1, .12), PAINTED)
    hook.beam((10.2, py, 2.76), (10.2, py, 2.62), .04, mat=IRON)
    for s in (-1, 1):
        hook.beam((10.2, py, 2.62), (10.2 + s * .2, py, 2.5), .025, mat=IRON)
    drum(hook, 10.2, py, 1.99, r=.18, h=.44)
    parts.append((hook, 'SLIDE_Z', -.96))
    lamp(g, px, py - .12, 3.4, face='front')


def fuel_vault(g, parts):
    x0, y0, x1, y1 = 8.0, 7.0, 11.0, 11.0   # fuel vault on tiles 8..11 x 7..11
    bx(g, x0, y0, 0, x1, y1, 3.3, CONCRETE)
    bx(g, x0 - .06, y0 - .06, 3.2, x1 + .06, y1 + .06, 3.42, CONCRETE)
    frustum(g, x0, y0, x1, y1, .02, .7, .22, top=False)
    # Proud cast ribs (shield pilasters) on the front and right faces.
    for x in (x0 + .6, x0 + 1.5, x0 + 2.5):
        bx(g, x - .09, y0 - .07, .3, x + .09, y0, 3.2, CONCRETE)
    for y in (7.7, 10.2):
        bx(g, x1, y - .09, .3, x1 + .07, y + .09, 3.2, CONCRETE)
    # Lead sheet frieze: forged plates high on the walls.
    front = Facer(x0, y0, 0, 'front')
    for u0, u1 in ((.08, .49), (.71, 1.39), (1.61, 2.39), (2.61, 2.92)):
        riveted_panel(g, front, u0, u1, 2.55, 3.1, 0, .05, FORGED)
    trefoil(g, 9.5, y0, 2.0, face='front', r=.26)
    # Lead-lined door on the right face: forged leaves in a steel frame.
    f = Facer(x1, 8.95, 0, 'right')
    f.box(g, 0, 1.0, .1, 1.7, 2.0, .2, IRON)
    for u in (-.4, .4):
        riveted_panel(g, f, u - .36, u + .36, .1, 1.85, .2, .26, FORGED)
    f.box(g, 0, 1.0, .275, .04, 1.8, .03, IRON)
    valve_wheel(g, *f.p(0, 1.05, .36), face='right', r=.2)
    g.cylinder(f.p(0, 1.05, .29), .05, .08, IRON, 'X', 8)
    lamp(g, x1, 8.0, 2.35, face='right')
    # Flat roof with parapet and an exhaust vent box.
    for (a, b, c, d) in ((x0, y0, x1, y0 + .16), (x0, y1 - .16, x1, y1), (x0, y0 + .16, x0 + .16, y1 - .16),
                         (x1 - .16, y0 + .16, x1, y1 - .16)):
        bx(g, a, b, 3.42, c, d, 3.72, CONCRETE)
    bx(g, 9.6, 8.5, 3.42, 10.5, 9.4, 4.0, FORGED)
    bx(g, 9.52, 8.42, 4.0, 10.58, 9.48, 4.08, IRON)
    for vx, vy in ((8.75, 10.3), (10.4, 10.3), (10.4, 7.6)):
        revolve(g, (vx, vy, 3.42), [(.09, 0), (.09, .45), (.26, .47), (.26, .55), (0, .66)], IRON, segments=8)
    trefoil(g, 10.05, 8.5, 3.7, face='front', r=.14)


def acid_tanks(g, parts):
    for x, mat in ((1.5, IRON), (3.75, PAINTED)):
        y = 8.9
        top = tank(g, x, y, 0, .95, 5.0, mat=mat, bands=4, roof='cone', segments=12)
        ladder(g, x, y - .95 - .02, .22, top, face='front', width=.32, cage=False)
        pipe_path(g, [(x, y - .9, 1.1), (x, 5.95, 1.1)], .08)
        valve(g, (x, 7.2, 1.1), .08, 'Y', wheel_face='up')
        bx(g, x - .14, 6.5, .012, x + .14, 6.8, 1.0, CONCRETE)
        gauge(g, x + .5, y - .82, 1.6, face='front', r=.1)
    pipe_path(g, [(2.3, 8.9, 3.6), (2.95, 8.9, 3.6)], .07)


def scrubber(g, parts):
    x0, y0, x1, y1 = 5.0, 6.03, 8.0, 11.0   # scrubber house on tiles 5..8 x 6..11, clear of the podium foot
    bx(g, x0, y0, 0, x1, y1, 3.0, CONCRETE)
    bx(g, x0 - .05, y0 - .05, 2.92, x1 + .05, y1 + .05, 3.012, CONCRETE)
    for x in (5.7, 6.45, 7.2):
        window(g, x, y1, 1.7, .62, 'back', 'factory')
    window(g, x1, 8.0, 1.7, .62, 'right', 'factory')
    window(g, x1, 9.3, 1.7, .62, 'right', 'factory')
    # Packed scrubber column.
    cx, cy = 5.85, 8.0
    revolve(g, (cx, cy, 3.012), [(.7, 0), (.7, .2), (.55, .25), (.55, 5.6)], IRON, segments=12)
    for z in (4.0, 5.8, 7.6):
        band(g, (cx, cy, 0), .55, z, .08, PAINTED, segments=12)
    dome(g, (cx, cy, 8.612), .56, IRON, segments=12, squash=.5)
    ladder(g, cx - .55 - .01, cy, 3.012, 8.5, face='left', width=.3, cage=False)
    for z in (4.6, 6.9):
        gauge(g, cx, cy - .55, z, face='front', r=.1)
    # Stack on a cast pedestal, joined to the column by a duct.
    sx, sy = 7.05, 9.75
    bx(g, sx - .62, sy - .62, 3.012, sx + .62, sy + .62, 3.8, CONCRETE)
    bx(g, sx - .67, sy - .67, 3.72, sx + .67, sy + .67, 3.84, CONCRETE)
    stack(g, sx, sy, 3.84, 9.4, emits='steam', r=.42, taper=.82, bands=3)   # scrubber plume
    pipe_path(g, [(cx, cy, 8.0), (cx, sy, 8.0), (sx - .3, sy, 8.0)], .16, flanges=True)
    beacon_part(g, parts, 'ColumnBeacon', cx, cy, 8.612 + .27)
    # Off-gas duct from the hall to the scrubber column on a steel trestle.
    pipe_path(g, [(6.17, 5.9, 4.6), (6.17, 7.7, 4.6)], .2)
    for xx in (5.95, 6.39):
        bx(g, xx - .05, 6.85, 3.012, xx + .05, 6.95, 4.36, IRON)
    bx(g, 5.88, 6.82, 4.36, 6.46, 6.98, 4.42, IRON)
    # Stack work ring at layer 12 with a beacon.
    rz = 12.0
    g.ring((sx, sy, rz - .04), .85, .44, .08, IRON, 'Z', 12)
    for k in range(8):
        a = k * math.pi / 4
        p = (sx + math.cos(a) * .82, sy + math.sin(a) * .82)
        g.box((p[0], p[1], rz + .3), (.04, .04, .6), IRON)
        g.beam((sx + math.cos(a) * .4, sy + math.sin(a) * .4, rz - .5), (p[0], p[1], rz - .08), .05, mat=IRON)
    g.ring((sx, sy, rz + .6), .84, .04, .05, IRON, 'Z', 12)
    ladder(g, sx, sy + .4, 3.84, rz, face='back', width=.3, cage=False)
    beacon_part(g, parts, 'StackBeacon', sx - .62, sy, rz)
    # Induced-draught fan in a ring housing on the roof.
    fx, fy = 7.0, 7.35
    hollow_revolve(g, (fx, fy, 3.012), [(.55, 0), (.55, .5)], .06, IRON, segments=12)
    parts.append((fan('ScrubberFan', fx, fy, 3.32, .46, blades=5), 'SPIN_Z', 3))
    g.cylinder((fx, fy, 3.15), .09, .27, IRON, 'Z', 10)


def build(g, parts):
    hall(g, parts)
    thickener(g, parts)
    drum_dock(g, parts)
    fuel_vault(g, parts)
    acid_tanks(g, parts)
    scrubber(g, parts)


def animate(obj, kind, value, frame_end):
    """CUSTOM_STRETCH: hoist cable scales in Z from its top, in step with SLIDE_Z."""
    if kind != 'CUSTOM_STRETCH':
        raise ValueError(kind)
    span = frame_end - 1
    for frame, t in ((1, 0), (1 + span * .4, 1), (1 + span * .5, 1), (1 + span * .9, 0), (frame_end, 0)):
        obj.scale = (1, 1, 1 + value * t)
        obj.keyframe_insert(data_path='scale', frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'BEZIER'
