"""Explicit material palette for standalone art studies; no game data writes."""
from pathlib import Path
import bpy
from frontier_architecture import create_materials

ROOT=Path(__file__).resolve().parents[2]
GLOW,GLASS,LEAF,WATER,CLOTH=range(8,13)
CRUSHER_STEEL=13
KILN_STONE,KILN_STONE_LIGHT,KILN_SOOT,KILN_EMBER,KILN_FLAME,KILN_CEMENT,KILN_SHELL=range(14,21)
KILN_RUST,KILN_WOOD_SPLIT,KILN_WOOD_WEAR,KILN_DUST=range(21,25)
CIVIC_CONCRETE,CIVIC_ORANGE_PANEL,CIVIC_FORGED_PANEL=range(27,30)
NATIVE_INDUSTRIAL_MATERIALS={0:'BaseWood_DarkBrown.IronTeeth',1:'IrregularPlanks_DarkBrown.IronTeeth',3:'RoofPlanks.IronTeeth'}

def kiln_weather(mat,source,kind):
    """Layer authored roughness, pitting, faded grain and oxidation in Blender."""
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF']
    coord=nodes.new('ShaderNodeTexCoord')
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5.5
    noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.73
    links.new(coord.outputs['Object'],noise.inputs['Vector'])
    mask=nodes.new('ShaderNodeValToRGB')
    threshold={'wood':(.32,.68),'iron':(.53,.68),'roof':(.49,.69)}[kind]
    mask.color_ramp.elements[0].position=threshold[0];mask.color_ramp.elements[0].color=(0,0,0,1)
    mask.color_ramp.elements[1].position=threshold[1];mask.color_ramp.elements[1].color=(1,1,1,1)
    links.new(noise.outputs['Fac'],mask.inputs[0])
    amount=nodes.new('ShaderNodeMath');amount.operation='MULTIPLY'
    amount.inputs[1].default_value={'wood':.30,'iron':.73,'roof':.80}[kind]
    links.new(mask.outputs[0],amount.inputs[0])
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
    mix.inputs[2].default_value={'wood':(.24,.20,.145,1),'iron':(.14,.053,.019,1),'roof':(.19,.105,.044,1)}[kind]
    links.new(amount.outputs[0],mix.inputs[0]);links.new(source,mix.inputs[1]);links.new(mix.outputs[0],bs.inputs['Base Color'])
    fine=nodes.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=94;fine.inputs['Detail'].default_value=3
    links.new(coord.outputs['Object'],fine.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=.013
    links.new(fine.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],bs.inputs['Normal'])
    rough=nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0;rough.inputs['From Max'].default_value=1
    rough.inputs['To Min'].default_value=.66 if kind=='wood' else .48
    rough.inputs['To Max'].default_value=.96
    links.new(noise.outputs['Fac'],rough.inputs['Value']);links.new(rough.outputs['Result'],bs.inputs['Roughness'])

def create_reference_materials(palette='standard'):
    art=ROOT/'src/DeepFrontier/Art/Textures/Reference'
    existing=ROOT/'src/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierArt'
    colors={
        'standard':[(.65,.62,.58),(.86,.82,.75),(.72,.76,.78),(1,1,1)],
        'crusher':[(.38,.35,.28),(.53,.47,.36),(.66,.68,.65),(.34,.49,.42)],
        'kiln':[(.38,.35,.28),(.53,.47,.36),(.66,.68,.65),(.34,.49,.42)],
    }[palette]
    entries=[
        ('ReferenceTimber',art/'PaintedTimber-v1.png',colors[0],0,.78),
        ('ReferencePlank',art/'PaintedTimber-v1.png',colors[1],0,.77),
        ('ReferenceIron',existing/'DFArtIron.BaseColor.png',colors[2],.55,.55),
        ('ReferenceRoof',art/'WeatheredTeal-v1.png',colors[3],.24,.70),
        ('ReferenceSandstone',existing/'DFArtSandstone.BaseColor.png',(1,1,1),0,.85),
        ('ReferenceLimestone',existing/'DFArtLimestone.BaseColor.png',(1,1,1),0,.87),
        ('ReferenceAggregate',existing/'DFArtAggregate.BaseColor.png',(1,1,1),0,.87),
        ('ReferenceBronze',existing/'DFArtBronze.BaseColor.png',(.86,.88,.90),.50,.56),
    ]
    result=[]
    from native_building_assets import native_material
    for index,(name,path,tint,metal,rough) in enumerate(entries):
        if index in NATIVE_INDUSTRIAL_MATERIALS:
            # The preview uses the shipped texture maps. The game still resolves
            # the original native material and shader by its exact name.
            material=native_material(NATIVE_INDUSTRIAL_MATERIALS[index])
            if material.name!=NATIVE_INDUSTRIAL_MATERIALS[index]:raise ValueError('Native material identity changed')
            result.append(material)
            continue
        if not path.is_file():raise FileNotFoundError(path)
        image=bpy.data.images.load(str(path),check_existing=True);image.colorspace_settings.name='sRGB';image.pack()
        mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF']
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT'
        if palette in ('crusher','kiln') and name in ('ReferenceTimber','ReferencePlank'):
            uv=mat.node_tree.nodes.new('ShaderNodeTexCoord')
            scale=mat.node_tree.nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
            scale.inputs[1].default_value=(.42,.65,1)
            mat.node_tree.links.new(uv.outputs['UV'],scale.inputs[0]);mat.node_tree.links.new(scale.outputs[0],tex.inputs['Vector'])
        multiply=mat.node_tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
        multiply.inputs[2].default_value=(*tint,1)
        mat.node_tree.links.new(tex.outputs['Color'],multiply.inputs[1]);mat.node_tree.links.new(multiply.outputs[0],bs.inputs['Base Color'])
        bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
        if palette in ('crusher','kiln') and name in ('ReferenceTimber','ReferencePlank','ReferenceIron','ReferenceRoof'):
            kind={'ReferenceTimber':'wood','ReferencePlank':'wood','ReferenceIron':'iron','ReferenceRoof':'roof'}[name]
            kiln_weather(mat,multiply.outputs[0],kind)
        mat.diffuse_color=(*tint,1);result.append(mat)
    for name,color,rough,emission in [('ReferenceWarmLight',(.95,.41,.07),.45,1.3),
                                    ('ReferenceWindow',(.45,.26,.07),.32,.18),
                                    ('ReferenceFoliage',(.12,.25,.065),.9,0),
                                    ('ReferenceWater',(.035,.20,.25),.22,0),
                                    ('ReferenceAwning',(.58,.47,.29),.92,0)]:
        if name=='ReferenceWater':
            result.append(native_material('Water'))
            continue
        mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
        bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
        if name=='ReferenceWindow':
            # Native-style opaque panes; the architecture never exposes rooms.
            bs.inputs['Alpha'].default_value=1
            bs.inputs['Transmission Weight'].default_value=0
        result.append(mat)
    if palette in ('crusher','kiln'):
        mat=bpy.data.materials.new('Crusher tooth steel');mat.use_nodes=True
        bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.245,.255,.24,1)
        bs.inputs['Metallic'].default_value=.65;bs.inputs['Roughness'].default_value=.57
        result.append(mat)
    if palette in ('crusher','kiln'):
        for name,color,metal,rough,emission in [
            ('Kiln grey masonry',(.16,.165,.14),0,.92,0),
            ('Kiln pale masonry',(.23,.23,.19),0,.91,0),
            ('Kiln soot and charcoal',(.018,.015,.012),0,.95,0),
            ('Kiln orange embers',(.95,.13,.008),0,.74,2),
            ('Kiln yellow flame', (1,.24,.008),0,.45,2.4),
            ('Kiln cement powder',(.43,.40,.33),0,1,0),
            ('Kiln worn steel plate',(.085,.079,.066),.65,.58,0),
            ('Kiln exposed rust',(.065,.027,.012),.25,.91,0),
            ('Kiln timber checks',(.038,.026,.014),0,.96,0),
            ('Kiln exposed timber grain',(.29,.245,.16),0,.89,0),
            ('Kiln deposited cement dust',(.30,.285,.24),0,1,0),
        ]:
            mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF']
            bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal
            bs.inputs['Roughness'].default_value=rough
            bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
            if emission==0:
                coord=mat.node_tree.nodes.new('ShaderNodeTexCoord')
                noise=mat.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=16
                noise.inputs['Detail'].default_value=2.5
                mat.node_tree.links.new(coord.outputs['Object'],noise.inputs['Vector'])
                ramp=mat.node_tree.nodes.new('ShaderNodeValToRGB')
                ramp.color_ramp.elements[0].color=(*(v*.70 for v in color),1)
                ramp.color_ramp.elements[1].color=(*(v*1.18 for v in color),1)
                mat.node_tree.links.new(noise.outputs['Fac'],ramp.inputs[0]);mat.node_tree.links.new(ramp.outputs[0],bs.inputs['Base Color'])
                bump=mat.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.17
                bump.inputs['Distance'].default_value=.025
                mat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);mat.node_tree.links.new(bump.outputs[0],bs.inputs['Normal'])
                if name=='Kiln worn steel plate':kiln_weather(mat,ramp.outputs[0],'iron')
            result.append(mat)
    return result


def civic_native_materials(materials):
    """The Iron Teeth palette, extended with explicit concrete/metal surfaces."""
    from native_building_assets import native_material
    if len(materials)!=27:raise ValueError('Civic palette requires the complete 27-slot workshop palette')
    materials[2]=native_material('BaseMetal.IronTeeth')
    materials[7]=native_material('Details.IronTeeth')
    materials.extend(native_material(name) for name in (
        'Plaster_White.IronTeeth','Plaster_Orange.IronTeeth','IrregularPlanks_MetalForged.IronTeeth',
        'WindowsAtlas.IronTeeth','BaseWood_Brown.Folktails'))
    return materials
