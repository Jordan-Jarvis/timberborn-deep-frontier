"""Extract local preview textures; runtime references the installed native assets."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
import UnityPy
game=dev.game_data()
env=UnityPy.load(str(game/'resources.assets'));objects={o.path_id:o for o in env.objects}
out=ROOT/'outputs/native-civic-assets';(out/'textures').mkdir(parents=True,exist_ok=True)
names={'BaseWood_DarkBrown.IronTeeth','BaseWood_Indigo.IronTeeth','BaseWood_Grey.IronTeeth',
       'IrregularPlanks_DarkBrown.IronTeeth','PaintedMetal.IronTeeth','Paper.IronTeeth',
       'WindowsAtlas.IronTeeth','BeaverCarryingModels','Water',
       'BaseMetal.IronTeeth','Plaster_White.IronTeeth','Plaster_Orange.IronTeeth','PlasteredWood_Orange.IronTeeth','IrregularPlanks_Grey.IronTeeth',
       'IrregularPlanks_MetalForged.IronTeeth','Details.IronTeeth','RoofPlanks.IronTeeth',
       'Shrub.IronTeeth','Blueberry','CoffeeBush','Dandelion','Sunflower',
       'BaseWood_Brown.Folktails','PlasteredWood_White.Folktails','IrregularPlanks_Mossy.Folktails','WindowsAtlas.Folktails','BaseWood_LightBrown.Folktails',
       # Fountain of Joy (Folktails) preview for the Town Plaza fountain review.
       'IrregularPlanks_Brown.Folktails','BaseWood_White.Folktails','BaseMetal.Folktails','FountainWater'}
manifest={}
for obj in env.objects:
    if obj.type.name!='Material':continue
    data=obj.parse_as_dict();name=data['m_Name']
    if name not in names:continue
    record={'id':obj.path_id,'properties':data['m_SavedProperties'],'textures':{}}
    for slot,info in data['m_SavedProperties']['m_TexEnvs']:
        ptr=info['m_Texture']
        if ptr['m_PathID']==0:continue
        if ptr['m_FileID']!=0:raise ValueError('Explicit native texture is outside resources.assets')
        tex=objects[ptr['m_PathID']].parse_as_object()
        path=out/'textures'/(str(ptr['m_PathID'])+'-'+tex.m_Name+'.png')
        tex.image.save(path)
        record['textures'][slot]={'file':str(path.relative_to(out)).replace('\\','/'),
                                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest[name]=record
if set(manifest)!=names:raise ValueError('Missing exact native materials: '+str(names-set(manifest)))
(out/'materials.json').write_text(json.dumps(manifest,indent=2))
env=UnityPy.load(str(game/'globalgamemanagers'))
for obj in env.objects:
    if obj.type.name=='ResourceManager':
        (out/'resource-paths.json').write_text(json.dumps(obj.parse_as_dict(),indent=2))
print('Native preview materials exported:',','.join(manifest))
