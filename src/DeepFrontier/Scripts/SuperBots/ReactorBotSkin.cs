using System;
using System.Collections.Generic;
using Timberborn.SingletonSystem;
using UnityEngine;
using Object = UnityEngine.Object;

namespace DeepFrontier.Scripts.SuperBots {
  // The Reactor Bot skin: radioactive-yellow eyes and dark plating.
  //
  // Native contract (Timberborn 1.1.2.8; the official BotURP.shadergraph in the
  // modding tools, Resources/Shaders): the bot body has one BotURP material
  // (Bot.IronTeeth: _BaseMap BotIronTeeth_2K_D, _BaseMap_1 BotIronTeeth_2K_E).
  //   BaseColor = lerp(1, _TintColor, _TintEnabled) * _BaseMap * _BaseColor
  //   Emission  = _BaseMap_1 * bloom + _EmissionColor + 0.35 * _TintColor * _TintEnabled
  // The graph has no _LightingColor, so the native bot illumination colour
  // (MaterialColorer) never reaches the eyes: their cyan is painted in
  // _BaseMap and baked into the _BaseMap_1 emission map, which is black
  // everywhere else. A tint multiplies the whole body and adds 0.35 x the tint
  // as glow, which washes a light tint out (build 252's steel tint).
  //
  // So the skin is a texture set, applied per bot through the native
  // CharacterMaterialModifier.SetTexture, the mechanism native
  // CharacterTextureSetter uses for character variants. The textures are
  // made at runtime from the bot material's own maps, so the mod ships no
  // copy of a game texture:
  //   eye mask = emission brightness over its peak (0 at or below EyeFloor);
  //   Emission = EyeColor x mask;
  //   Unplated = _BaseMap with the eye blended to EyeColor by the mask;
  //   Plated   = the same over dark plating: (c/255)^Gamma x Scale x Color per channel.
  // One set per source texture pair, shared by every Reactor Bot.
  internal sealed class ReactorBotSkin : IUnloadableSingleton {
    // BotURP reference names (BotURP.shadergraph m_OverrideReferenceName of Base Map and Emission Map).
    internal const string BaseMapProperty="_BaseMap";
    internal const string EmissionMapProperty="_BaseMap_1";
    internal static readonly int BaseMapId=Shader.PropertyToID(BaseMapProperty);
    internal static readonly int EmissionMapId=Shader.PropertyToID(EmissionMapProperty);
    // Emission values at or below this (of 255) are not eye (the black map's noise).
    private const int EyeFloor=4;

    internal sealed record Textures(Texture2D Plated, Texture2D Unplated, Texture2D Emission);

    private readonly ReactorBotSettings _settings;
    private readonly Dictionary<(Texture, Texture), Textures> _made=new();

    public ReactorBotSkin(ReactorBotSettings settings) {_settings=settings;}

    // The skin for a bot whose body material is source (its vanilla BotURP maps).
    public Textures For(Material source) {
      if(!source.HasProperty(BaseMapId)||!source.HasProperty(EmissionMapId))
        throw new InvalidOperationException($"Reactor bots: bot material {source.name} ({source.shader.name}) has no {BaseMapProperty}/{EmissionMapProperty}; the BotURP contract changed");
      var baseMap=source.GetTexture(BaseMapId);
      var emissionMap=source.GetTexture(EmissionMapId);
      if(!baseMap||!emissionMap)throw new InvalidOperationException($"Reactor bots: bot material {source.name} has no base or emission map");
      if(_made.TryGetValue((baseMap,emissionMap),out var made))return made;
      foreach(var set in _made.Values)
        if(baseMap==set.Plated||baseMap==set.Unplated||emissionMap==set.Emission)
          throw new InvalidOperationException($"Reactor bots: {source.name} already carries the Reactor Bot skin; read the vanilla maps before applying it");
      made=Make(baseMap,emissionMap);
      _made.Add((baseMap,emissionMap),made);
      return made;
    }

    public void Unload() {
      foreach(var set in _made.Values) {
        Object.Destroy(set.Plated);
        Object.Destroy(set.Unplated);
        Object.Destroy(set.Emission);
      }
      _made.Clear();
    }

    private Textures Make(Texture baseMap, Texture emissionMap) {
      var spec=_settings.Spec;
      if(baseMap.width!=emissionMap.width||baseMap.height!=emissionMap.height)
        throw new InvalidOperationException($"Reactor bots: base map {baseMap.width}x{baseMap.height} and emission map {emissionMap.width}x{emissionMap.height} differ in size");
      var source=Pixels(baseMap);
      var emission=Pixels(emissionMap);
      int peak=0;
      foreach(var p in emission)peak=Math.Max(peak,Math.Max(p.r,Math.Max(p.g,p.b)));
      if(peak<=EyeFloor)throw new InvalidOperationException($"Reactor bots: the bot emission map {emissionMap.name} has no eye (peak {peak})");
      Color32 eye=spec.EyeColor;
      var dark=new byte[3][];
      for(int c=0;c<3;c++) {
        dark[c]=new byte[256];
        for(int v=0;v<256;v++)dark[c][v]=(byte)Mathf.Clamp(Mathf.RoundToInt(Mathf.Pow(v/255f,spec.DarkPlatingGamma)*spec.DarkPlatingScale*spec.DarkPlatingColor[c]*255f),0,255);
      }
      var plated=new Color32[source.Length];
      var unplated=new Color32[source.Length];
      var glow=new Color32[source.Length];
      for(int i=0;i<source.Length;i++) {
        var s=source[i];
        var e=emission[i];
        int v=Math.Max(e.r,Math.Max(e.g,e.b));
        float m=v<=EyeFloor?0f:Mathf.Min(1f,(v-EyeFloor)/(float)(peak-EyeFloor));
        var darkened=new Color32(dark[0][s.r],dark[1][s.g],dark[2][s.b],s.a);
        unplated[i]=Color32.Lerp(s,new Color32(eye.r,eye.g,eye.b,s.a),m);
        plated[i]=Color32.Lerp(darkened,new Color32(eye.r,eye.g,eye.b,s.a),m);
        glow[i]=new Color32((byte)Mathf.RoundToInt(eye.r*m),(byte)Mathf.RoundToInt(eye.g*m),(byte)Mathf.RoundToInt(eye.b*m),e.a);
      }
      return new Textures(Texture("DeepFrontier.ReactorBot.Plated",baseMap,plated),Texture("DeepFrontier.ReactorBot.Unplated",baseMap,unplated),
        Texture("DeepFrontier.ReactorBot.Emission",emissionMap,glow));
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

    private static Texture2D Texture(string name, Texture like, Color32[] pixels) {
      var texture=new Texture2D(like.width,like.height,TextureFormat.RGBA32,true,false) {
        name=name, filterMode=like.filterMode, anisoLevel=like.anisoLevel, wrapMode=like.wrapMode,
      };
      texture.SetPixels32(pixels);
      texture.Apply(true,false);
      texture.Compress(false);
      texture.Apply(false,true);
      return texture;
    }
  }
}
