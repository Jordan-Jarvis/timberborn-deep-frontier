using System;
using System.Collections.Generic;
using Timberborn.SingletonSystem;
using UnityEngine;
using Object = UnityEngine.Object;

namespace DeepFrontier.Scripts.SuperBots {
  // The Reactor Bot skin: near-black plating, and neon-yellow glowing eyes and
  // joint seams; the vanilla light body (still glowing) while unplated.
  //
  // Native contract (Timberborn 1.1.2.8; the official BotURP.shadergraph in the
  // modding tools, Resources/Shaders): the bot body has one BotURP material
  // (Bot.IronTeeth: _BaseMap BotIronTeeth_2K_D, _BaseMap_1 BotIronTeeth_2K_E).
  //   BaseColor = lerp(1, _TintColor, _TintEnabled) * _BaseMap * _BaseColor
  //   Emission  = _BaseMap_1 * (BLOOM_ENABLED ? 2 : 1) + _EmissionColor + 0.35 * _TintColor * _TintEnabled
  // Everything goes through the native per-character material instance
  // (CharacterMaterialModifier, as native CharacterTextureSetter does):
  // - Plating is the material's own _BaseColor: while the plating need is
  //   favourable ReactorBot sets it to the settings' PlatingColor (a dark
  //   multiplier of the game's base map), otherwise back to the material's own
  //   value. No base texture is generated or replaced.
  // - The glow is the one texture made at run time, because the BotURP graph
  //   has no colour for its emission map and no mask for joint seams, and the
  //   mod may not ship a copy or a derivative of a game texture or mesh:
  //   eye mask   = the game emission map's brightness over its peak (0 at or below EyeFloor);
  //   joint mask = near each GlowJoint pivot, the surface within GlowRim of
  //                another part of the mesh (the seams between the bot's
  //                pieces): (1 - d / rim)^2 x clamp01(2 (1 - |p - pivot| / radius)),
  //                x GlowJointGain;
  //   Emission   = linear GlowColor x GlowIntensity x max(eye, joint), an HDR
  //                (half float, linear) map at half resolution, so the glow can
  //                exceed what an 8-bit map holds and blooms.
  // The body mesh is Timbermesh's StaticMeshBuilder mesh: built with new Mesh(),
  // never made non-readable, and not Optimize()d when vertex-animated (the bot),
  // so its vertices are the bind pose in model space with uv0 intact. Parts are
  // the mesh's welded connected pieces. One glow map per source emission map
  // and mesh, shared by every Reactor Bot, destroyed on unload.
  internal sealed class ReactorBotSkin : IUnloadableSingleton {
    // BotURP reference names (BotURP.shadergraph m_OverrideReferenceName of Base Color and Emission Map).
    internal const string BaseColorProperty="_BaseColor";
    internal const string EmissionMapProperty="_BaseMap_1";
    internal static readonly int BaseColorId=Shader.PropertyToID(BaseColorProperty);
    internal static readonly int EmissionMapId=Shader.PropertyToID(EmissionMapProperty);
    // Emission values at or below this (of 255) are not eye (the black map's noise).
    private const int EyeFloor=4;
    // Positions closer than this are one vertex when splitting the mesh into parts.
    private const float WeldStep=1e-4f;

    private readonly ReactorBotSettings _settings;
    private readonly Dictionary<(Texture, Mesh), Texture2D> _made=new();

    public ReactorBotSkin(ReactorBotSettings settings) {_settings=settings;}

    // The material's own base colour, which the unplated body keeps.
    public static Color NativeBaseColor(Material source) {
      if(!source.HasProperty(BaseColorId))
        throw new InvalidOperationException($"Reactor bots: bot material {source.name} ({source.shader.name}) has no {BaseColorProperty}; the BotURP contract changed");
      return source.GetColor(BaseColorId);
    }

    // The glow emission map for a bot whose body is mesh drawn with source (its vanilla BotURP maps).
    public Texture2D For(Material source, Mesh mesh) {
      if(!source.HasProperty(EmissionMapId))
        throw new InvalidOperationException($"Reactor bots: bot material {source.name} ({source.shader.name}) has no {EmissionMapProperty}; the BotURP contract changed");
      var emissionMap=source.GetTexture(EmissionMapId);
      if(!emissionMap)throw new InvalidOperationException($"Reactor bots: bot material {source.name} has no emission map");
      if(!mesh||!mesh.isReadable)throw new InvalidOperationException($"Reactor bots: the bot body mesh {(mesh?mesh.name:"(none)")} is not readable; the Timbermesh contract changed");
      if(_made.TryGetValue((emissionMap,mesh),out var made))return made;
      foreach(var glow in _made.Values)
        if(emissionMap==glow)throw new InvalidOperationException($"Reactor bots: {source.name} already carries the Reactor Bot glow; read the vanilla map before applying it");
      made=Make(emissionMap,mesh);
      _made.Add((emissionMap,mesh),made);
      return made;
    }

    public void Unload() {
      foreach(var glow in _made.Values)Object.Destroy(glow);
      _made.Clear();
    }

    private Texture2D Make(Texture emissionMap, Mesh mesh) {
      var spec=_settings.Spec;
      int w=emissionMap.width,h=emissionMap.height;
      if(w%2!=0||h%2!=0)throw new InvalidOperationException($"Reactor bots: emission map {w}x{h} must be even");
      var emission=Pixels(emissionMap);
      int peak=0;
      foreach(var p in emission)peak=Math.Max(peak,Math.Max(p.r,Math.Max(p.g,p.b)));
      if(peak<=EyeFloor)throw new InvalidOperationException($"Reactor bots: the bot emission map {emissionMap.name} has no eye (peak {peak})");
      int hw=w/2,hh=h/2;
      var joints=JointMask(mesh,hw,hh,spec);
      var hot=spec.GlowColor.linear*spec.GlowIntensity;
      var light=new Color[hw*hh];
      for(int y=0;y<hh;y++)for(int x=0;x<hw;x++) {
        float joint=Mathf.Min(1f,joints[y*hw+x]*spec.GlowJointGain);
        float g=0f;
        for(int dy=0;dy<2;dy++)for(int dx=0;dx<2;dx++) {
          var e=emission[(2*y+dy)*w+2*x+dx];
          int v=Math.Max(e.r,Math.Max(e.g,e.b));
          float eye=v<=EyeFloor?0f:Mathf.Min(1f,(v-EyeFloor)/(float)(peak-EyeFloor));
          g+=Mathf.Max(eye,joint);
        }
        g/=4f;
        light[y*hw+x]=new Color(hot.r*g,hot.g*g,hot.b*g,1f);
      }
      return Hdr("DeepFrontier.ReactorBot.Glow",emissionMap,hw,hh,light);
    }

    // Joint seams at half resolution (rows bottom-up, as texture pixels): near each
    // pivot, the surface of each part within GlowRim of another part.
    private static float[] JointMask(Mesh mesh, int width, int height, FrontierReactorBotSettingsSpec spec) {
      var vertices=mesh.vertices;
      var uv=mesh.uv;
      var triangles=mesh.triangles;
      if(uv.Length!=vertices.Length)throw new InvalidOperationException($"Reactor bots: the bot body mesh {mesh.name} has no uv0");
      int count=triangles.Length/3;
      var part=Parts(vertices,triangles);
      var mask=new float[width*height];
      var rim=spec.GlowRim;
      foreach(var joint in spec.GlowJoints) {
        var c=joint.Pivot;
        var local=new List<int>();
        for(int t=0;t<count;t++)if(BoundsDistance(vertices,triangles,t,c)<joint.Radius+rim)local.Add(t);
        foreach(var t in local) {
          if(BoundsDistance(vertices,triangles,t,c)>=joint.Radius)continue;
          var others=local.FindAll(o=>part[o]!=part[t]);
          if(others.Count==0)continue;
          Vector3 a=vertices[triangles[3*t]],b=vertices[triangles[3*t+1]],d=vertices[triangles[3*t+2]];
          Vector2 ua=Scale(uv[triangles[3*t]],width,height),ub=Scale(uv[triangles[3*t+1]],width,height),ud=Scale(uv[triangles[3*t+2]],width,height);
          float den=(ub.y-ud.y)*(ua.x-ud.x)+(ud.x-ub.x)*(ua.y-ud.y);
          if(Mathf.Abs(den)<1e-9f)continue;
          int x0=Math.Max(0,Mathf.FloorToInt(Mathf.Min(ua.x,Mathf.Min(ub.x,ud.x)))),x1=Math.Min(width-1,Mathf.CeilToInt(Mathf.Max(ua.x,Mathf.Max(ub.x,ud.x))));
          int y0=Math.Max(0,Mathf.FloorToInt(Mathf.Min(ua.y,Mathf.Min(ub.y,ud.y)))),y1=Math.Min(height-1,Mathf.CeilToInt(Mathf.Max(ua.y,Mathf.Max(ub.y,ud.y))));
          for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++) {
            float px=x+0.5f,py=y+0.5f;
            float l0=((ub.y-ud.y)*(px-ud.x)+(ud.x-ub.x)*(py-ud.y))/den;
            float l1=((ud.y-ua.y)*(px-ud.x)+(ua.x-ud.x)*(py-ud.y))/den;
            float l2=1f-l0-l1;
            if(l0<-0.002f||l1<-0.002f||l2<-0.002f)continue;
            var p=l0*a+l1*b+l2*d;
            float region=1f-Vector3.Distance(p,c)/joint.Radius;
            if(region<=0f)continue;
            float near=float.MaxValue;
            foreach(var o in others)near=Mathf.Min(near,Vector3.Distance(p,ClosestPoint(p,vertices[triangles[3*o]],vertices[triangles[3*o+1]],vertices[triangles[3*o+2]])));
            if(near>=rim)continue;
            float m=(1f-near/rim)*(1f-near/rim)*Mathf.Clamp01(region*2f);
            int i=y*width+x;
            if(m>mask[i])mask[i]=m;
          }
        }
      }
      return mask;
    }

    private static Vector2 Scale(Vector2 uv, int width, int height)=>new(uv.x*width,uv.y*height);

    // The welded connected piece each triangle belongs to.
    private static int[] Parts(Vector3[] vertices, int[] triangles) {
      var weld=new int[vertices.Length];
      var ids=new Dictionary<Vector3Int, int>();
      for(int v=0;v<vertices.Length;v++) {
        var key=Vector3Int.RoundToInt(vertices[v]/WeldStep);
        if(!ids.TryGetValue(key,out var id)) { id=ids.Count; ids.Add(key,id); }
        weld[v]=id;
      }
      var parent=new int[ids.Count];
      for(int i=0;i<parent.Length;i++)parent[i]=i;
      int Find(int i) { while(parent[i]!=i) { parent[i]=parent[parent[i]]; i=parent[i]; } return i; }
      int count=triangles.Length/3;
      for(int t=0;t<count;t++) {
        int root=Find(weld[triangles[3*t]]);
        parent[Find(weld[triangles[3*t+1]])]=root;
        parent[Find(weld[triangles[3*t+2]])]=root;
      }
      var part=new int[count];
      for(int t=0;t<count;t++)part[t]=Find(weld[triangles[3*t]]);
      return part;
    }

    private static float BoundsDistance(Vector3[] vertices, int[] triangles, int t, Vector3 point) {
      Vector3 a=vertices[triangles[3*t]],b=vertices[triangles[3*t+1]],c=vertices[triangles[3*t+2]];
      var lo=Vector3.Min(a,Vector3.Min(b,c));
      var hi=Vector3.Max(a,Vector3.Max(b,c));
      return Vector3.Max(Vector3.zero,Vector3.Max(lo-point,point-hi)).magnitude;
    }

    // Closest point on triangle abc to p (Ericson, Real-Time Collision Detection 5.1.5).
    private static Vector3 ClosestPoint(Vector3 p, Vector3 a, Vector3 b, Vector3 c) {
      Vector3 ab=b-a,ac=c-a,ap=p-a;
      float d1=Vector3.Dot(ab,ap),d2=Vector3.Dot(ac,ap);
      if(d1<=0f&&d2<=0f)return a;
      Vector3 bp=p-b;
      float d3=Vector3.Dot(ab,bp),d4=Vector3.Dot(ac,bp);
      if(d3>=0f&&d4<=d3)return b;
      float vc=d1*d4-d3*d2;
      if(vc<=0f&&d1>=0f&&d3<=0f)return a+d1/(d1-d3)*ab;
      Vector3 cp=p-c;
      float d5=Vector3.Dot(ab,cp),d6=Vector3.Dot(ac,cp);
      if(d6>=0f&&d5<=d6)return c;
      float vb=d5*d2-d1*d6;
      if(vb<=0f&&d2>=0f&&d6<=0f)return a+d2/(d2-d6)*ac;
      float va=d3*d6-d5*d4;
      if(va<=0f&&d4-d3>=0f&&d5-d6>=0f)return b+(d4-d3)/(d4-d3+(d5-d6))*(c-b);
      float denom=1f/(va+vb+vc);
      return a+ab*(vb*denom)+ac*(vc*denom);
    }

    // The texture's pixels as sampled (GPU copy; game textures are not CPU-readable).
    // Both the copy and the textures made from it are sRGB, so sampling them
    // gives what sampling the source gives.
    private static Color32[] Pixels(Texture source) {
      var target=RenderTexture.GetTemporary(source.width,source.height,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);
      var active=RenderTexture.active;
      try {
        Graphics.Blit(source,target);
        RenderTexture.active=target;
        var copy=new Texture2D(source.width,source.height,TextureFormat.RGBA32,false,false);
        try {
          copy.ReadPixels(new Rect(0,0,source.width,source.height),0,0,false);
          return copy.GetPixels32();
        } finally {Object.Destroy(copy);}
      } finally {
        RenderTexture.active=active;
        RenderTexture.ReleaseTemporary(target);
      }
    }

    // Linear half-float texture: sampled values are the stored ones, above 1 where the glow is hot.
    private static Texture2D Hdr(string name, Texture like, int width, int height, Color[] pixels) {
      var texture=new Texture2D(width,height,TextureFormat.RGBAHalf,true,true) {
        name=name, filterMode=like.filterMode, anisoLevel=like.anisoLevel, wrapMode=like.wrapMode,
      };
      texture.SetPixels(pixels);
      texture.Apply(true,true);
      return texture;
    }
  }
}
