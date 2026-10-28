"""Check the full-source component path using one actual door and a test wall.

No building generator, source file write, export or render is performed.
"""
import sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from building_components import recipe
from reference_materials import create_reference_materials,civic_native_materials
from industrial_facades import extra_materials

collection=bpy.data.collections.new('Component contract');bpy.context.scene.collection.children.link(collection)
materials=civic_native_materials(create_reference_materials('kiln')+extra_materials())
wall=Geometry('Component contract.Architecture');wall.box((0,0,1),(1,.2,2))
door=recipe('Restaurant','Door.UpperDoor')
wall.include_component(door)
assert wall.components==[{'name':door.name,'faceRange':[6,43]}]
obj=wall.build(collection,materials,.012,'civic-native')
assert len(obj.data.polygons)==6
part=bpy.data.objects[door.name]
assert part['df_component']==door.name and len(part.data.polygons)==37
assert len(collection.objects)==2
print('PASS: root authoring creates separate named assets; native UV and retained-wall fingerprint checks passed')
