"""Long-run hazardous-weather shares for the combined tide-selection policies.

Exact Markov model of the installed Timberborn 1.1.2.8 selection, not a simulation:
- native HazardousWeatherRandomizer: badtide chance from ChanceForBadtide and the current
  streak (StreakChanceDecreaseThreshold 0.05, StreakChanceResetThreshold 0.025, DecreaseRatio 0.5);
  a tide in the history is a non-badtide streak, exactly as the native history records its ID;
- Deep Frontier RadioactiveTideService.Choose: one tide chance per eligible cycle and
  CooldownCycles = 1 (a tide never follows the same tide);
- the implemented policy C' (ModdableFluids FluidTideSelection.Select, policy 'shared'): the
  budget is the largest installed chance; each eligible tide gets its own slice of it,
  budget x weight / total weight of every installed tide (weights default to the chances,
  decision 1b), the cycle capped at budget x largest eligible weight / largest weight (1c),
  and no tide in the cycle after any tide.
Long-run shares assume every weather is past its first eligible cycle. Probabilities are the
exact decimals (0.4, 15%), not the game's float values. Writes
outputs/fluids-api-prototype/tide-policy-model.json and prints the Markdown tables.
"""
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BADTIDE, DROUGHT = 'Badtide', 'Drought'
MODES = {  # vanilla GameMode blueprints, Deep Frontier RadioactiveTideTuning.GameModeCurve, docs/more-fluids-design.md
    'Easy': {'badtide': 0.4, 'df': 0.15, 'coffee': 0.10, 'salt': 0.10},
    'Normal': {'badtide': 0.4, 'df': 0.25, 'coffee': 0.15, 'salt': 0.15},
    'Hard': {'badtide': 0.4, 'df': 0.35, 'coffee': 0.20, 'salt': 0.20},
}
# Tide IDs as registered, so ordinal order matches FluidTideSelection.
RADIOACTIVE, COFFEE, SALT = 'DeepFrontier.RadioactiveTide', 'MoreFluids.CoffeeTide', 'MoreFluids.SaltTide'
INSTALLS = {  # installed content -> tide chances per mode
    'Vanilla only': {},
    'Deep Frontier': {RADIOACTIVE: 'df'},
    'More Fluids': {COFFEE: 'coffee', SALT: 'salt'},
    'Deep Frontier + More Fluids': {RADIOACTIVE: 'df', COFFEE: 'coffee', SALT: 'salt'},
}


def native_badtide_chance(base, last, streak):
    """HazardousWeatherRandomizer.GetBadtideChance, float thresholds as in 1.1.2.8."""
    if streak <= 0:
        return base
    is_badtide = last == BADTIDE
    value = base if is_badtide else 1 - base
    power = value ** (streak + 1)
    if power < 0.025:
        value = 0.0
    elif power < 0.05:
        value *= 0.5
    return value if is_badtide else 1 - value


def tide_shares(policy, tides, eligible):
    """Probability of each eligible tide this cycle; the remainder goes to the native randomizer."""
    chances = {t: tides[t] for t in eligible}
    if not chances:
        return {}
    if policy == 'single':
        assert len(tides) == 1
        return dict(chances)
    if policy == 'additive':
        if sum(chances.values()) > 1:
            raise ValueError('Additive shares exceed one')
        return dict(chances)
    if policy in ('budget', 'budget-global'):
        budget = max(tides.values())  # the largest registered chance, whether or not eligible
        total = sum(chances.values())
        return {t: budget * c / total for t, c in chances.items()}
    if policy == 'shared':
        # Implemented C' (decisions 1b, 1c): p = B x min(We / W, me / m), split by weight over the eligible tides.
        budget, total, largest = max(tides.values()), sum(tides.values()), max(tides.values())
        eligible_total, eligible_largest = sum(chances.values()), max(chances.values())
        p = budget * min(eligible_total / total, eligible_largest / largest)
        return {t: p * c / eligible_total for t, c in chances.items()}
    if policy == 'independent':
        result = {t: 0.0 for t in chances}
        names = sorted(chances)
        for outcome in itertools.product([False, True], repeat=len(names)):
            weight = 1.0
            for name, hit in zip(names, outcome):
                weight *= chances[name] if hit else 1 - chances[name]
            hits = [n for n, h in zip(names, outcome) if h]
            if hits:
                total = sum(chances[n] for n in hits)
                for n in hits:
                    result[n] += weight * chances[n] / total
        return result
    if policy == 'load-order':
        # Status-quo hazard: each later postfix overrides the earlier one (list order = load order).
        result, remaining = {}, 1.0
        for name in reversed(list(tides)):
            if name in chances:
                result[name] = remaining * chances[name]
                remaining *= 1 - chances[name]
        return result
    raise ValueError(policy)


def stationary(base, tides, policy, cap=12):
    ids = [BADTIDE, DROUGHT] + list(tides)
    states = [(w, s) for w in ids for s in range(1, cap + 1)]
    index = {state: i for i, state in enumerate(states)}

    def step(distribution):
        nxt = [0.0] * len(states)
        for (last, streak), p in zip(states, distribution):
            if p == 0:
                continue
            # CooldownCycles = 1 per tide; a '-global' policy (and 'shared') also blocks every tide after any tide.
            blocked = (policy.endswith('-global') or policy == 'shared') and last in tides
            eligible = [] if blocked else [t for t in tides if t != last]
            shares = tide_shares(policy, tides, eligible)
            native = 1 - sum(shares.values())
            beta = native_badtide_chance(base, last, streak)
            outcomes = dict(shares)
            outcomes[BADTIDE] = native * beta
            outcomes[DROUGHT] = native * (1 - beta)
            for weather, q in outcomes.items():
                s = min(streak + 1, cap) if weather == last else 1
                nxt[index[(weather, s)]] += p * q
        return nxt

    distribution = [1.0 / len(states)] * len(states)
    for _ in range(20000):
        nxt = step(distribution)
        delta = max(abs(a - b) for a, b in zip(nxt, distribution))
        distribution = nxt
        if delta < 1e-15:
            break
    else:
        raise RuntimeError('No convergence')
    shares = {w: 0.0 for w in ids}
    for (weather, _), p in zip(states, distribution):
        shares[weather] += p
    return shares


def main():
    rows = []
    for mode, values in MODES.items():
        rows.append({'mode': mode, 'case': 'Vanilla only', 'policy': 'native', 'shares': stationary(values['badtide'], {}, 'single')})
        rows.append({'mode': mode, 'case': 'Deep Frontier only', 'policy': 'current DF', 'shares': stationary(values['badtide'], {'DF tide': values['df']}, 'single')})
    normal = MODES['Normal']
    for mf in (0.25, 0.15):
        tides = {'DF tide': normal['df'], 'MF tide': mf}
        for policy in ('load-order', 'additive', 'budget', 'budget-global', 'independent'):
            rows.append({'mode': 'Normal', 'case': f'DF + More Fluids (MF chance {mf:.0%})', 'policy': policy,
                         'shares': stationary(normal['badtide'], tides, policy)})
    implemented = []
    for mode, values in MODES.items():
        for install, tides in INSTALLS.items():
            chances = {tide: values[key] for tide, key in tides.items()}
            shares = stationary(values['badtide'], chances, 'shared' if chances else 'single')
            if len(chances) > 1:  # every tide eligible in the long run: the slices are the whole budget split by weight
                renormalized = stationary(values['badtide'], chances, 'budget-global')
                assert all(abs(shares[k] - renormalized[k]) < 1e-12 for k in shares), (mode, install)
            if len(chances) == 1:  # C' with one tide is today's Deep Frontier rule
                single = stationary(values['badtide'], chances, 'single')
                assert all(abs(shares[k] - single[k]) < 1e-12 for k in shares), (mode, install)
            implemented.append({'mode': mode, 'installed': install, 'policy': "C'", 'budget': max(chances.values(), default=0),
                                'shares': shares})
    output = ROOT / 'outputs' / 'fluids-api-prototype' / 'tide-policy-model.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'source': __doc__.strip().splitlines()[0], 'rows': rows, 'implemented': implemented}, indent=2) + '\n',
                      encoding='utf-8')
    print('| Mode | Case | Policy | Drought | Badtide | DF tide | MF tide |')
    print('| --- | --- | --- | ---: | ---: | ---: | ---: |')
    for row in rows:
        s = row['shares']
        cells = [f"{100 * s.get(k, 0):.1f}%" if k in s else '-' for k in (DROUGHT, BADTIDE, 'DF tide', 'MF tide')]
        print(f"| {row['mode']} | {row['case']} | {row['policy']} | " + ' | '.join(cells) + ' |')
    print()
    print("Implemented policy C' (budget = largest chance, weights = chances, global one-cycle cooldown):")
    print()
    print('| Mode | Installed | Budget | Drought | Badtide | Radioactive | Coffee | Salt |')
    print('| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |')
    for row in implemented:
        s = row['shares']
        cells = [f"{100 * s[k]:.1f}%" if k in s else '-' for k in (DROUGHT, BADTIDE, RADIOACTIVE, COFFEE, SALT)]
        budget = f"{100 * row['budget']:.0f}%" if row['budget'] else '-'
        print(f"| {row['mode']} | {row['installed']} | {budget} | " + ' | '.join(cells) + ' |')
    print()
    print("Implemented C' per cycle, Normal, before the long run: the chance that an eligible cycle (no tide just before) is a tide.")
    print()
    normal = MODES['Normal']
    cycles_without = {RADIOACTIVE: 14, COFFEE: 8, SALT: 7}
    print('| Cycle | ' + ' | '.join(INSTALLS) + ' |')
    print('| ---: |' + ' ---: |' * len(INSTALLS))
    for cycle in (8, 9, 15):
        cells = []
        for install, tides in INSTALLS.items():
            chances = {tide: normal[key] for tide, key in tides.items()}
            eligible = [t for t in chances if cycle > cycles_without[t]]
            shares = tide_shares('shared', chances, eligible) if chances else {}
            cells.append(f"{100 * sum(shares.values()):.1f}%")
        print(f'| {cycle} | ' + ' | '.join(cells) + ' |')
    capped = tide_shares('shared', {'A': 0.5, 'B': 0.1, 'C': 0.1}, ['B', 'C'])
    assert abs(sum(capped.values()) - 0.1) < 1e-12, capped  # 1c: the largest eligible chance, not 50 x 20 / 70
    print()
    print('Exact values for the C# harness (HarnessExtensions.Tides.cs):')
    for row in implemented:
        print(row['mode'], row['installed'], ' '.join(f"{k}={v!r}" for k, v in row['shares'].items()))
    print(f'Report: {output}')


if __name__ == '__main__':
    main()
