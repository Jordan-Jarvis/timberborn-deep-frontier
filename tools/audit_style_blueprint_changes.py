"""Compare generated data with the captured pre-style source, without repairing it."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = root / 'src/DeepFrontier/Data'
before = json.loads((root / 'outputs/style-before-blueprints.json').read_text(encoding='utf-8-sig'))
after = {str(p.relative_to(data)): json.loads(p.read_text(encoding='utf-8'))
         for p in data.rglob('*.blueprint.json')}
assert set(before) == set(after), 'Style pass unexpectedly added or removed blueprint files'
changes = []
for name, text in before.items():
    old, new = json.loads(text), after[name]
    if old == new:
        continue
    fields = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    changes.append({'path': name, 'changedComponents': fields,
                    'before': {k: old.get(k) for k in fields},
                    'after': {k: new.get(k) for k in fields}})
report = {'blueprints': len(after), 'changed': changes}
(root / 'outputs/style-blueprint-changes.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'blueprints': len(after), 'changes': [
    {k: c[k] for k in ('path', 'changedComponents')} for c in changes]}, indent=2))
