"""Windows cut straight from the shipped WindowsAtlas.IronTeeth cells.

The Iron Teeth window atlas holds more than the four New Styles assemblies in
architectural_windows.py: a nine-pane grid, a large single pane, a three-pane
vertical, a four-pane band, a long ribbon, a framed cross, tall slits, a
steel-ringed porthole and a plain glazing tile. Each cell carries its own
painted frame plus the native emission (night glow) map, so a correctly
proportioned quad on the cell reads exactly like vanilla glazing.

Rules: a piece keeps its cell's aspect ratio (no stretching); it is seated on
an explicit wall skin with a physical reveal back to that plane; mounts are
recorded in g.window_mounts like the native assemblies. Large glazing uses
the plain glass tile per pane behind a proud steel mullion grid.

Cell bounds were measured from the atlas emission map (glowing panes) and the
diffuse layout; UV v is bottom-up.
"""
# Palette slots (frontier_architecture.WOOD / IRON). Declared here so the UV
# contract can import this module outside Blender, without bpy.
WOOD, IRON = 0, 2

WINDOW = 30
INSET = .004
# name: (u0, u1, v0, v1) full painted cell, frame included.
CELLS = {
    'grid9':    (0.0, .25, .75, 1.0),
    'single':   (.25, .5, .75, 1.0),
    'triple':   (.5, .625, .75, 1.0),
    'band4':    (0.0, .375, .625, .75),
    'ribbon':   (0.0, .375, .5, .625),
    'cross':    (.375, .625, .5, .75),
    'slit':     (.5, .625, .25, .5),
    'slit2':    (.5, .625, 0.0, .25),
    'porthole': (.75, 1.0, .25, .5),
    'glass':    (.75, 1.0, 0.0, .25),
}
FACES = {'front': (0, -1), 'back': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


def _f32(value):
    """Round to the float32 Blender stores, so UV contracts compare exactly."""
    import struct
    return struct.unpack('f', struct.pack('f', value))[0]


def cell_rect(piece):
    u0, u1, v0, v1 = CELLS[piece]
    return tuple(_f32(v) for v in (u0 + INSET, u1 - INSET, v0 + INSET, v1 - INSET))


def cell_uvs():
    """Every UV corner this module authors: the inset corners of each cell."""
    result = set()
    for piece in CELLS:
        u0, u1, v0, v1 = cell_rect(piece)
        result.update({(u0, v0), (u1, v0), (u1, v1), (u0, v1)})
    return result
# Panes stand 56 mm off the wall skin: clear of the 40 mm projecting timber
# frame members on civic walls, so pane and frame never share a plane.
MOUNT_DEPTH = .056


def aspect(piece):
    """Width / height of a piece's cell (atlas texels are square)."""
    u0, u1, v0, v1 = CELLS[piece]
    return (u1 - u0) / (v1 - v0)


def _frame(face):
    if face not in FACES:
        raise ValueError('Unknown window face ' + str(face))
    nx, ny = FACES[face]
    return nx, ny, -ny, nx   # outward normal and in-wall tangent (u to the right)


def _quad(g, x, y, z, w, h, face, uv, depth, reveal_mat, style):
    nx, ny, tx, ty = _frame(face)
    def p(u, v, d):
        return (x + u * tx + d * nx, y + u * ty + d * ny, z + v)
    u0, u1, v0, v1 = uv
    first = len(g.faces)
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    front = [p(a, b, depth) for a, b in corners]
    g.native_piece(front, [(0, 1, 2, 3)], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], WINDOW)
    rear = [p(a, b, 0) for a, b in corners]
    edges = []
    for i in range(4):
        j = (i + 1) % 4
        g.add([rear[i], rear[j], front[j], front[i]], [(0, 1, 2, 3)], reveal_mat)
        edges.append([rear[i], rear[j]])
    g.window_mounts.append({'style': 'atlas:' + style, 'face': face, 'anchor': [x, y, z], 'scale': w,
                            'outward': [nx, ny, 0], 'mountDepth': depth,
                            'faceRange': [first, len(g.faces)], 'rearEdges': edges})


def atlas_window(g, x, y, z, width, face, piece, *, reveal=WOOD, depth=MOUNT_DEPTH):
    """One native atlas window centred at (x, z) on the wall skin at `y`
    (or `x` for side faces); height follows the piece's own aspect."""
    if piece not in CELLS or piece == 'glass':
        raise ValueError('Use glass_curtain for plain glazing; unknown piece ' + str(piece))
    if width <= 0:
        raise ValueError('Window width must be positive')
    _quad(g, x, y, z, width, width / aspect(piece), face, cell_rect(piece), depth, reveal, piece)


def glass_curtain(g, x, y, z0, z1, width, face, *, cols, rows, mullion=.07, frame=IRON, depth=.05):
    """Big industrial glazing: square-ish native glass panes in a proud steel
    grid. (x, y) is the centre of the opening on the wall skin; z0..z1 its
    sill and head. Panes sit `depth` out from the skin; mullions stand proud
    of the panes by 30 mm so no glazing and steel share a plane."""
    if cols < 1 or rows < 1 or z1 <= z0 or width <= 0:
        raise ValueError('Curtain glazing needs a positive grid and opening')
    nx, ny, tx, ty = _frame(face)
    pw = (width - (cols + 1) * mullion) / cols
    ph = (z1 - z0 - (rows + 1) * mullion) / rows
    if pw <= .05 or ph <= .05:
        raise ValueError('Curtain glazing panes are too small for its mullions')
    first = len(g.faces)
    for c in range(cols):
        for r in range(rows):
            u = -width / 2 + mullion + c * (pw + mullion) + pw / 2
            v = z0 + mullion + r * (ph + mullion) + ph / 2
            _quad(g, x + u * tx, y + u * ty, v, pw, ph, face, cell_rect('glass'), depth, frame, 'glass')
    # Steel mullions, transoms, sill and head: boxes proud of the glazing.
    out = depth + .03
    def box(u, v, du, dv, back, front):
        mid, thick = (back + front) / 2, front - back
        cx, cy = x + u * tx + mid * nx, y + u * ty + mid * ny
        sx = abs(du * tx) + abs(thick * nx)
        sy = abs(du * ty) + abs(thick * ny)
        g.box((cx, cy, v), (sx, sy, dv), frame)
    for c in range(cols + 1):
        u = -width / 2 + mullion / 2 + c * (pw + mullion)
        box(u, (z0 + z1) / 2, mullion, z1 - z0, 0, out)
    # Transoms stand 15 mm behind the mullion faces and 10 mm off the skin,
    # so neither their front nor back face shares a plane with a mullion.
    for r in range(rows + 1):
        v = z0 + mullion / 2 + r * (ph + mullion)
        box(0, v, width - 2 * mullion - .004, mullion * .8, .01, out - .015)
    # Projecting sill.
    cx, cy = x + (out + .03) / 2 * nx, y + (out + .03) / 2 * ny
    g.box((cx, cy, z0 - .03), (abs(width * tx) + abs((out + .03) * nx) + .08 * abs(tx),
                               abs(width * ty) + abs((out + .03) * ny) + .08 * abs(ty), .06), frame)
    return first
