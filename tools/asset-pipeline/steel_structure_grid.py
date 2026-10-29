"""Grid families of the steel structures (no Blender dependency).

Shared by steel_structure_geometry.py (art) and structural_layouts.py
(registration); tools/structural_building_content.mjs holds the matching
native block contracts and refuses any other size.
"""
CANTILEVERS = {10: 1, 12: 2, 15: 3}          # length -> anchor tiles
BRIDGE_SPANS = (8, 10, 12, 15)               # span tiles beyond the abutment tile
COLUMN_HEIGHTS = (1, 2, 3, 4, 5, 6)
DECK_SPANS = (3, 5)


def cantilever_ident(length):
    return f'SteelCantilever{length}x1'


def bridge_ident(span):
    return f'SteelBridge{span}x1'


def column_ident(height):
    return f'SteelColumnH{height}'


def deck_ident(n):
    return f'SteelDeck{n}x{n}'


SIZES = {cantilever_ident(n): [1, n, 1] for n in CANTILEVERS}
SIZES.update({bridge_ident(n): [1, n + 1, 1] for n in BRIDGE_SPANS})
SIZES.update({column_ident(h): [1, 1, h] for h in COLUMN_HEIGHTS})
SIZES.update({deck_ident(n): [n, n, 1] for n in DECK_SPANS})
BRIDGES = {bridge_ident(n) for n in BRIDGE_SPANS}
