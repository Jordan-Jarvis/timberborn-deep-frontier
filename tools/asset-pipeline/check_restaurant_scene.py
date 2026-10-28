"""Recheck the saved restaurant scene, including its entire sign animation."""
import json
import sys
from pathlib import Path
import bpy

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/asset-pipeline'))
from civic_validation import validate_civic_walks
bpy.ops.wm.open_mainfile(filepath=str(root/'src/DeepFrontier/Art/Source/Restaurant-ReferenceStudy.blend'))
result=validate_civic_walks('Restaurant',bpy.data.collections['Restaurant.ReferenceStudy'],bpy.context.scene)
(root/'outputs/reference-studies/Restaurant-clearance-check.json').write_text(json.dumps(result,indent=2)+'\n')
print('Restaurant saved scene passed; sign-to-deck minimum gap:',result['animatedSignDeckClearance'])
