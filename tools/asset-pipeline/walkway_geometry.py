"""Reusable authored rail assemblies with independently addressable mesh nodes.

Positions are artwork coordinates. This module does not round them onto the game
grid or claim navigation. A later explicit grid layout binds openings to nodes.
"""
import math
from mathutils import Vector
from frontier_architecture import Geometry,WOOD,IRON,BRASS
from industrial_geometry import steel_bolt
from housing_railing import post as housing_post,panel as housing_panel


from collections import namedtuple
GridPoint=namedtuple('GridPoint','x y')


class RailAssembly:
    def __init__(self,prefix,cap_material=BRASS):
        self.prefix=prefix
        self.cap_material=cap_material
        self.meshes=[]
        self.runs=[]
        self.posts={}
        self.ids=set()

    def post(self,p,z):
        key=(p.x,p.y,z)
        if key in self.posts:return self.posts[key]
        name=f'{self.prefix}.Post{len(self.posts):03d}'
        g=Geometry(name)
        housing_post(g,p,z)
        self.meshes.append(g);self.posts[key]=name
        return name

    def run(self,ident,a,b,z,*,segments=None):
        if ident in self.ids:raise ValueError('Duplicate rail-run ID: '+ident)
        a,b=Vector(a),Vector(b)
        if (b-a).length<.1:raise ValueError('Rail run is too short: '+ident)
        if segments is not None and (type(segments) is not int or segments<1):raise ValueError('Authored rail segment count must be a positive integer')
        self.ids.add(ident);count=math.ceil((b-a).length/.59) if segments is None else segments
        points=[a]+[a+(b-a)*i/count for i in range(1,count)]+[b]
        posts=[self.post(p,z) for p in points];panels=[]
        for i,(left,right) in enumerate(zip(points,points[1:])):
            name=f'{self.prefix}.{ident}.Panel{i:02d}';g=Geometry(name)
            housing_panel(g,left,right,z)
            self.meshes.append(g)
            panels.append({'node':name,'start':[left.x,left.y,z],'end':[right.x,right.y,z],
                           'startPost':posts[i],'endPost':posts[i+1]})
        self.runs.append({'id':ident,'panels':panels})

    def run_grid(self,ident,a,b,z,source_origin):
        """Inset deck-edge rail whose intermediate posts stand on tile boundaries.

        `a`/`b` are artwork endpoints (usually 0.10 inside the deck corners).
        Between them a post stands at every whole native grid coordinate along
        the run, so opening one cell's rail section leaves exactly that tile
        open and keeps both boundary posts. Nothing is rounded or inferred:
        the boundaries are the explicit integers strictly between the ends.
        """
        if ident in self.ids:raise ValueError('Duplicate rail-run ID: '+ident)
        if len(source_origin)!=3 or any(not math.isfinite(v) for v in source_origin):
            raise ValueError('Grid-post rail requires an explicit source origin')
        # Keep double precision: mathutils vectors are single precision, and a
        # boundary rounded to float32 no longer sums to the exact native
        # integer the exporter cuts at (it then emitted a zero-length piece).
        a=(float(a[0]),float(a[1]));b=(float(b[0]),float(b[1]))
        if math.dist(a,b)<.1:raise ValueError('Rail run is too short: '+ident)
        axes=[i for i in range(2) if abs(b[i]-a[i])>1e-9]
        if len(axes)!=1:raise ValueError('Grid-post rail requires one horizontal cardinal span: '+ident)
        axis=axes[0];offset=source_origin[axis]
        lo,hi=sorted((a[axis]+offset,b[axis]+offset))
        def boundary(k):
            # Author the exact double whose sum with the origin is the integer.
            v=k-offset
            for toward in (math.inf,-math.inf):
                w=v
                for _ in range(8):
                    if w+offset==k:return w
                    w=math.nextafter(w,toward)
            raise ValueError(f'No exact source coordinate for native boundary {k}: {ident}')
        cuts=[boundary(k) for k in range(math.floor(lo)+1,math.ceil(hi)) if lo+.05<k<hi-.05]
        if b[axis]<a[axis]:cuts.reverse()
        def at(value):
            q=list(a);q[axis]=value;return GridPoint(*q)
        points=[GridPoint(*a),*[at(v) for v in cuts],GridPoint(*b)]
        # The official exporter re-cuts every panel at whole native
        # coordinates; each authored panel must already be exactly one piece.
        for left,right in zip(points,points[1:]):
            l,r=sorted((left[axis],right[axis]))
            if any(True for _ in range(math.floor(l+offset)+1,math.ceil(r+offset))):
                raise ValueError(f'Grid-post rail panel {l}..{r} would be re-cut by the exporter: {ident}')
        self.ids.add(ident)
        posts=[self.post(p,z) for p in points];panels=[]
        for i,(left,right) in enumerate(zip(points,points[1:])):
            name=f'{self.prefix}.{ident}.Panel{i:02d}';g=Geometry(name)
            housing_panel(g,left,right,z)
            self.meshes.append(g)
            panels.append({'node':name,'start':[left.x,left.y,z],'end':[right.x,right.y,z],
                           'startPost':posts[i],'endPost':posts[i+1]})
        self.runs.append({'id':ident,'panels':panels})

    def manifest(self):
        return {'status':'Separate Blender nodes; game connection bindings are not authored yet',
                'coordinateSpace':'Authored artwork X/across Y/back Z/up; no grid conversion',
                'runs':self.runs,'nodes':[g.name for g in self.meshes]}

    def run_cells(self,ident,start,end,source_origin):
        """Author whole native-cell panels without deriving grid cells from floats."""
        if ident in self.ids:raise ValueError('Duplicate rail-run ID: '+ident)
        if len(start)!=3 or len(end)!=3 or any(type(v) is not int for v in (*start,*end)):
            raise ValueError('Grid rail endpoints require explicit integer XYZ')
        if len(source_origin)!=3 or any(not math.isfinite(v) for v in source_origin):
            raise ValueError('Grid rail requires an explicit source origin')
        axes=[i for i in range(3) if start[i]!=end[i]]
        if len(axes)!=1 or axes[0]==2:raise ValueError('Grid rail requires one horizontal cardinal span')
        axis=axes[0];count=abs(end[axis]-start[axis]);step=1 if end[axis]>start[axis] else -1
        native_points=[tuple(start[j]+(step*i if j==axis else 0) for j in range(3)) for i in range(count+1)]
        points=[tuple(p[j]-source_origin[j] for j in range(3)) for p in native_points]
        posts=[self.post(Vector(p[:2]),p[2]) for p in points];panels=[]
        self.ids.add(ident)
        for i,(left,right) in enumerate(zip(points,points[1:])):
            name=f'{self.prefix}.{ident}.Panel{i:02d}';g=Geometry(name)
            housing_panel(g,Vector(left[:2]),Vector(right[:2]),left[2])
            self.meshes.append(g)
            panels.append({'node':name,'start':list(left),'end':list(right),
                'startPost':posts[i],'endPost':posts[i+1],
                'gridAxis':axis,'gridCell':min(native_points[i][axis],native_points[i+1][axis]),
                'gridStart':list(native_points[i]),'gridEnd':list(native_points[i+1]),
                'gridOrigin':list(source_origin)})
        self.runs.append({'id':ident,'panels':panels})
