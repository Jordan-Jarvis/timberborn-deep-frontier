"""Decode a rendered reference preview and save actual video frames for review."""
import argparse
import json
from pathlib import Path
import sys
import bpy

parser=argparse.ArgumentParser()
parser.add_argument('--model',required=True,choices=['MineralQuarry','StoneCrusher','CementKiln','Hospital','Restaurant','GroceryStore','FisheryWorks'])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root=Path(__file__).resolve().parents[2]
output=root/'outputs/reference-studies'
video=output/(args.model+'-motion.mp4')
report=json.loads((output/(args.model+'-motion-check.json')).read_text())
clip=bpy.data.movieclips.load(str(video))
if list(clip.size)!=[640,640]:raise ValueError('Unexpected video dimensions')
if clip.frame_duration!=report['previewFrames']:raise ValueError('Video frame count differs from render report')
if abs(clip.fps-report['previewFps'])>1e-4:raise ValueError('Video frame rate differs from render report')
scene=bpy.context.scene
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.fps=30;scene.render.fps_base=30/report['previewFps']
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard'
editor=scene.sequence_editor_create()
strip=editor.strips.new_movie('Rendered preview',str(video),channel=1,frame_start=1)
scene.render.use_sequencer=True
samples=[1,round(clip.frame_duration*.46),round(clip.frame_duration*.70)]
for frame in samples:
    scene.frame_set(frame)
    scene.render.filepath=str(output/f'{args.model}-video-frame-{frame:03d}.png')
    bpy.ops.render.render(write_still=True)
result={'source':video.name,'dimensions':list(clip.size),'frames':clip.frame_duration,
        'fps':clip.fps,'decodedReviewFrames':samples}
(output/(args.model+'-video-check.json')).write_text(json.dumps(result,indent=2)+'\n')
print('DECODED VIDEO VERIFIED',json.dumps(result),flush=True)
