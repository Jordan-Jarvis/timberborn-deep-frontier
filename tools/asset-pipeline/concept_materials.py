"""Original, deterministic painted textures shared by Blender and Unity.

The image files are production assets, not a studio-only procedural shader.
All material IDs are explicitly registered in the Common material collection.
"""
import json
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
TEXTURES=ROOT/'src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierArt'
CATALOG=[
    ('DFArtTimber', (.37,.225,.12),0,.69,'wood'),
    ('DFArtPlank', (.49,.315,.17),0,.70,'wood'),
    ('DFArtIron', (.235,.25,.245),.65,.43,'metal'),
    ('DFArtRoof', (.21,.36,.345),.35,.62,'roof'),
    ('DFArtSandstone', (.65,.48,.29),0,.81,'stone'),
    ('DFArtLimestone', (.67,.65,.56),0,.84,'stone'),
    ('DFArtAggregate', (.43,.425,.38),0,.85,'stone'),
    ('DFArtBronze', (.53,.385,.20),.55,.46,'metal'),
]

def create_concept_materials():
    TEXTURES.mkdir(parents=True,exist_ok=True)
    result=[]; manifest=[]
    n=512;v,u=np.mgrid[0:n,0:n]/n
    for index,(name,color,metal,rough,kind) in enumerate(CATALOG):
        rng=np.random.default_rng(921+index)
        fine=rng.random((n,n))-.5
        coarse=np.sin(2*np.pi*u*3+.6*np.sin(2*np.pi*v*2))*np.cos(2*np.pi*v*4)
        if kind=='wood':
            bend=u+.009*np.sin(v*2*np.pi)+.005*np.sin(v*8*np.pi)
            rings=np.sin(2*np.pi*(bend*43+.18*np.sin(v*2*np.pi)))
            grain=np.maximum(0,rings)**14
            grain2=np.maximum(0,np.sin(2*np.pi*bend*117))**20
            knot=np.zeros((n,n))
            for x,y in ((.24,.34),(.73,.81)):
                radius=np.sqrt(((u-x)*2.8)**2+((v-y)*.65)**2)
                knot+=np.exp(-radius*25)*(.4+.6*np.sin(radius*180)**2)
            value=.96+.09*coarse+.07*fine-.22*grain-.09*grain2-.25*knot
        elif kind=='roof':
            scratches=np.maximum(0,np.sin(u*2*np.pi*61+.1*np.sin(v*8*np.pi)))**40
            wear=(np.sin(u*2*np.pi*5)*np.sin(v*2*np.pi*7)>.91)
            value=.95+.12*coarse+.12*fine-.13*scratches+.24*wear
        elif kind=='metal':
            scratches=np.maximum(0,np.sin(v*2*np.pi*127+.2*np.sin(u*12*np.pi)))**40
            value=.96+.07*coarse+.10*fine+.08*scratches
        else:
            value=.96+.09*coarse+.11*fine
        pixels=np.ones((n,n,4),dtype=np.float32)
        pixels[:,:,:3]=np.array(color)[None,None,:]*value[:,:,None]
        if pixels.min()<0 or pixels.max()>1:raise ValueError(f'Authored {name} pixels outside RGB range')
        image=bpy.data.images.new(name,width=n,height=n,alpha=True)
        image.colorspace_settings.name='sRGB';image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw=str(TEXTURES/(name+'.BaseColor.png'));image.file_format='PNG';image.save()
        # Reload stored PNG so preview and shipped texture use the same decoded bytes.
        image.reload()
        material=bpy.data.materials.new(name);material.use_nodes=True
        material.diffuse_color=(*color,1)
        bs=material.node_tree.nodes['Principled BSDF'];bs.inputs['Metallic'].default_value=metal
        bs.inputs['Roughness'].default_value=rough
        texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image
        texture.extension='REPEAT';material.node_tree.links.new(texture.outputs['Color'],bs.inputs['Base Color'])
        result.append(material)
        manifest.append(dict(name=name,metallic=metal,smoothness=1-rough))
    (TEXTURES/'material-catalog.json').write_text(json.dumps(manifest,indent=2)+'\n')
    target=ROOT/'src/DeepFrontier/Data/MaterialCollections/MaterialCollection.DeepFrontierArt.blueprint.json'
    target.write_text(json.dumps({'MaterialCollectionSpec':{'CollectionId':'Common','Materials':[
        'Materials/DeepFrontierArt/'+entry['name'] for entry in manifest]}},indent=2)+'\n')
    return result
