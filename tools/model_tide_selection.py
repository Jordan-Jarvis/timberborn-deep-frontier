"""Long-run hazardous-weather shares for the proposed combined tide-selection policies.

Exact Markov model of the installed Timberborn 1.1.2.8 selection, not a simulation:
- native HazardousWeatherRandomizer: badtide chance from ChanceForBadtide and the current
  streak (StreakChanceDecreaseThreshold 0.05, StreakChanceResetThreshold 0.025, DecreaseRatio 0.5);
  a tide in the history is a non-badtide streak, exactly as the native history records its ID;
- Deep Frontier RadioactiveTideService.Choose: one tide chance per eligible cycle and
  CooldownCycles = 1 (a tide never follows the same tide).
Long-run shares assume every weather is past its first eligible cycle. Writes
outputs/fluids-api-prototype/tide-policy-model.json and prints the Markdown tables.
"""
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BADTIDE, DROUGHT = 'Badtide', 'Drought'
MODES = {  # vanilla GameMode blueprints and Deep Frontier RadioactiveTideTuning.GameModeCurve
    'Easy': {'badtide': 0.4, 'df': 0.15}, 'Normal': {'badtide': 0.4, 'df': 0.25}, 'Hard': {'badtide': 0.4, 'df': 0.35},
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
            # CooldownCycles = 1 per tide; a '-global' policy also blocks every tide after any tide.
            eligible = [] if policy.endswith('-global') and last in tides else [t for t in tides if t != last]
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
    output = ROOT / 'outputs' / 'fluids-api-prototype' / 'tide-policy-model.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'source': __doc__.strip().splitlines()[0], 'rows': rows}, indent=2) + '\n', encoding='utf-8')
    print('| Mode | Case | Policy | Drought | Badtide | DF tide | MF tide |')
    print('| --- | --- | --- | ---: | ---: | ---: | ---: |')
    for row in rows:
        s = row['shares']
        cells = [f"{100 * s.get(k, 0):.1f}%" if k in s else '-' for k in (DROUGHT, BADTIDE, 'DF tide', 'MF tide')]
        print(f"| {row['mode']} | {row['case']} | {row['policy']} | " + ' | '.join(cells) + ' |')
    print(f'Report: {output}')


if __name__ == '__main__':
    main()
