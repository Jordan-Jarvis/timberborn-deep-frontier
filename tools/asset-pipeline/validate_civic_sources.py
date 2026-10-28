"""Check saved civic scenes without regenerating or changing reviewed geometry."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from civic_validation import validate_civic_walks
parser=argparse.ArgumentParser();parser.add_argument('--models',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
for ident in args.models.split(','):
    source=ROOT/f'src/DeepFrontier/Art/Source/{ident}-ReferenceStudy.blend'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    report=validate_civic_walks(ident,bpy.data.collections[ident+'.ReferenceStudy'],bpy.context.scene)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    report.update(model=ident,sourceSha256=digest)
    (ROOT/f'outputs/reference-studies/{ident}-saved-source-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('SAVED CIVIC SOURCE PASSED',ident,digest,flush=True)
