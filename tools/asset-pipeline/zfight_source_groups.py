"""Group diagnostic conflicts by their recorded authoring call sites."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--models',required=True);parser.add_argument('--limit',type=int,default=20)
args=parser.parse_args()
for model in args.models.split(','):
    report=json.loads((ROOT/f'outputs/zfight/{model}-frame1.json').read_text(encoding='utf-8'))
    groups={}
    for conflict in report['conflicts']:
        if not conflict['visible']:continue
        key=tuple(sorted(p['source'] if 'source' in p else 'Untagged mesh: '+p['object'] for p in (conflict['a'],conflict['b'])))
        if key not in groups:groups[key]={'pairs':0,'area':0,'example':conflict}
        groups[key]['pairs']+=1;groups[key]['area']+=conflict['overlapArea']
    print(model,report['visibleConflicts'])
    for key,value in sorted(groups.items(),key=lambda item:-item[1]['area'])[:args.limit]:
        c=value['example']
        display=[' > '.join(s for s in source.split(' > ') if not s.startswith('industrial_levels.py')).split(' > ')[:2] for source in key]
        print(json.dumps({'sources':display,'pairs':value['pairs'],'area':round(value['area'],4),
                          'center':c['center'],'normal':c['normal'],'materials':[c[p]['material'] for p in ('a','b')]}))
