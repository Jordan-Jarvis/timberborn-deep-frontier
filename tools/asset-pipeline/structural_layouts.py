"""Grid contracts for original modular structures, without mesh scaling.

Unlike the illustrated factories, these pieces are authored as tile modules.
Support planes are exact geometry surfaces. Runtime placement remains a
separate acceptance requirement.
"""
import json
from pathlib import Path


SIZES = {
    'SandstoneMasonryBlock': [1, 1, 1],
    'BrickMasonryBlock': [1, 1, 1],
    'ConcreteBlock': [1, 1, 1],
    'ConcreteOverhang8x1': [1, 8, 1],
    'ConcreteScaffold3x3': [3, 3, 4],
    'ReinforcedDamBlock': [1, 1, 1],
    'ConcreteOverflowDam': [1, 1, 1],
    # Concrete platform variants: [n, n, legs+1], the deck is the top layer.
    'ConcreteScaffold3x3H1': [3, 3, 2],
    'ConcreteScaffold3x3H2': [3, 3, 3],
    'ConcreteScaffold4x4H1': [4, 4, 2],
    'ConcreteScaffold4x4H2': [4, 4, 3],
    'ConcreteScaffold4x4H3': [4, 4, 4],
    'ConcreteScaffold5x5H1': [5, 5, 2],
    'ConcreteScaffold5x5H2': [5, 5, 3],
    'ConcreteScaffold5x5H3': [5, 5, 4],
    # Concrete side platforms: an n x n legless deck at layer 0 beside a
    # one-cell anchor row (y = n), plus the cleat layer above the anchor.
    # The grid width is odd (n, or n+1 with an empty column for even n) so
    # the anchor column x = n//2 is its own mirror image under native flip.
    'ConcreteSidePlatform3x3': [3, 4, 2],
    'ConcreteSidePlatform4x4': [5, 5, 2],
    'ConcreteSidePlatform5x5': [5, 6, 2],
}
# Steel structures (steel_structure_geometry.py): cantilevers [1, N, 1],
# bridges [1, N+1, 1] (N span tiles beyond the supported abutment tile),
# columns [1, 1, H] and corner-supported decks [n, n, 1].
from steel_structure_grid import SIZES as STEEL_SIZES, BRIDGES as STEEL_BRIDGES
SIZES.update(STEEL_SIZES)
# Side platforms use native BaseZ 1 so the placement tool picks them from the
# anchor's top face. Their art is authored with the deck at z 0..1; the
# export origin shifts it one layer down so the deck top is the model's z = 0.
SIDE_PLATFORMS = {name for name in SIZES if name.startswith('ConcreteSidePlatform')}
LAYOUTS = {
    name: {
        'origin': [0, 0, -1] if name in SIDE_PLATFORMS else [0, 0, 0], 'size': size,
        'baseZ': 1 if name in SIDE_PLATFORMS else 0,
        'idle': [], 'nodes': [], 'edges': [], 'ports': [], 'deckMode':'None',
        # Bridges carry no stackable top: their walking deck is the floor of
        # layer 0, like the vanilla suspension bridge.
        'supportLayer': 1 if name in SIDE_PLATFORMS else 0 if name in STEEL_BRIDGES else size[2],
    }
    for name, size in SIZES.items()
}

if __name__ == '__main__':
    target = Path(__file__).resolve().parents[1] / 'structural-layouts.json'
    target.write_text(json.dumps(LAYOUTS, indent=2) + '\n')
    print(target)
