"""Cache the exact native 1x1 stored-liquid mesh for local Blender preview."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
env=UnityPy.load(str(dev.resources_assets()))
obj=next(o for o in env.objects if o.path_id==1647)
mesh=obj.parse_as_object()
if obj.type.name!='Mesh' or mesh.m_Name!='SmallLiquidPlane':raise ValueError('Native resource identity changed')
handler=MeshHandler(mesh);handler.process()
data={'resource':'StockpileGoodModels/SmallLiquidPlane','vertices':handler.m_Vertices,
      'uv':handler.m_UV0,'faces':[f for sub in handler.get_triangles() for f in sub]}
(ROOT/'outputs/native-civic-assets/SmallLiquidPlane.json').write_text(json.dumps(data,indent=2))
print('Native liquid mesh:',len(data['vertices']),'vertices',len(data['faces']),'faces')
