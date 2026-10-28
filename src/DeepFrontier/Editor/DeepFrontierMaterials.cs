#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace DeepFrontier.Editor {
  public static class DeepFrontierMaterials {
    private const string ResourceRoot = "Assets/Mods/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontier";

    [MenuItem("Deep Frontier/Create Materials")]
    public static void CreateMaterials() {
      CreateMaterial("DeepFrontierMetal", new Color(0.18f, 0.22f, 0.25f, 1f), 0.7f, 0.55f);
      CreateMaterial("DeepFrontierPainted", new Color(0.08f, 0.28f, 0.34f, 1f), 0.7f, 0.55f);
      CreateMaterial("DeepFrontierRock", new Color(0.11f, 0.12f, 0.13f, 1f), 0.05f, 0.3f);
      const string artRoot = "Assets/Mods/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierArt";
      var json = File.ReadAllText($"{artRoot}/material-catalog.json");
      var catalog = JsonUtility.FromJson<ArtCatalog>("{\"materials\":" + json + "}");
      if (catalog.materials.Length != 8) throw new InvalidOperationException("Expected eight authored art materials.");
      foreach (var entry in catalog.materials) {
        CreateMaterialAt(artRoot, entry.name, Color.white, entry.metallic, entry.smoothness);
      }
      const string industrialRoot = "Assets/Mods/DeepFrontier/AssetBundles/Resources/Materials/DeepFrontierIndustrial";
      var industrial = JsonUtility.FromJson<ArtCatalog>("{\"materials\":" + File.ReadAllText($"{industrialRoot}/material-catalog.json") + "}");
      if (industrial.materials.Length != 27) throw new InvalidOperationException("Expected 27 industrial material slots.");
      foreach (var entry in industrial.materials) {
        CreateMaterialAt(industrialRoot, entry.name, Color.white, entry.metallic, entry.smoothness);
        var material = AssetDatabase.LoadAssetAtPath<Material>($"{industrialRoot}/{entry.name}.mat");
        bool emissive = entry.emission > 0;
        var emissionMap = emissive ? material.GetTexture("_BaseMap") : material.GetTexture("_EmissionMap");
        var emissionColor = emissive ? Color.white * entry.emission : Color.black;
        if (material.IsKeywordEnabled("_EMISSION") != emissive || material.GetTexture("_EmissionMap") != emissionMap
            || material.GetColor("_EmissionColor") != emissionColor) {
          if (emissive) material.EnableKeyword("_EMISSION"); else material.DisableKeyword("_EMISSION");
          material.SetTexture("_EmissionMap", emissionMap);
          material.SetColor("_EmissionColor", emissionColor);
          EditorUtility.SetDirty(material);
        }
      }
      CreateReservoirMesh();
      ImportPileMeshes();
      AssetDatabase.SaveAssets();
    }

    // Stockpile pile meshes (GoodVisualizationSpec PrimaryMesh/SecondaryMesh) are
    // AssetRef<Mesh>: the bundle must hold a UnityEngine.Mesh at the resource
    // path. The official Timbermesh importer (Timberborn.TimbermeshTools.Editor
    // TimbermeshScriptedImporter) adds a Mesh sub-asset only with its
    // _createMeshAsset option; by default it stores the BinaryData GameObject
    // alone, which build 167 could not load as a Mesh. Bob Storage 1.1 ships
    // StockpileGoodModels/18BoxColumn this way (GameObject + Mesh at one path).
    public const string PileMeshRoot = "Assets/Mods/DeepFrontier/AssetBundles/Resources/StockpileGoodModels";

    private static void ImportPileMeshes() {
      var paths = AssetDatabase.FindAssets("", new[] { PileMeshRoot })
        .Select(AssetDatabase.GUIDToAssetPath)
        .Where(path => path.EndsWith(".timbermesh", StringComparison.Ordinal))
        .Distinct().OrderBy(path => path, StringComparer.Ordinal).ToArray();
      if (paths.Length == 0) throw new InvalidOperationException($"No pile meshes under {PileMeshRoot}.");
      foreach (var path in paths) {
        var importer = AssetImporter.GetAtPath(path);
        if (importer == null || importer.GetType().Name != "TimbermeshScriptedImporter")
          throw new InvalidOperationException($"{path} is not imported by the official TimbermeshScriptedImporter ({importer?.GetType().FullName}).");
        var serialized = new SerializedObject(importer);
        var option = serialized.FindProperty("_createMeshAsset");
        if (option == null) throw new InvalidOperationException($"TimbermeshScriptedImporter no longer has _createMeshAsset ({path}).");
        if (!option.boolValue) {
          option.boolValue = true;
          serialized.ApplyModifiedPropertiesWithoutUndo();
          importer.SaveAndReimport();
        }
        var meshes = AssetDatabase.LoadAllAssetsAtPath(path).OfType<Mesh>().ToArray();
        if (meshes.Length != 1 || meshes[0].subMeshCount != 1 || !meshes[0].isReadable || meshes[0].vertexCount == 0)
          throw new InvalidOperationException($"{path} must import as exactly one readable single-submesh Mesh; found {meshes.Length}.");
      }
    }

    private static void CreateReservoirMesh() {
      const string folder="Assets/Mods/DeepFrontier/AssetBundles/Resources/Meshes/DeepFrontier";
      Directory.CreateDirectory(folder);
      const string path=folder+"/ReservoirRectangle.asset";
      // Authored once: the geometry below is constant, so an existing asset is
      // current (delete it to re-author after changing this method).
      if(AssetDatabase.LoadAssetAtPath<Mesh>(path)!=null) return;
      var mesh=new Mesh {name="ReservoirRectangle"};
      AssetDatabase.CreateAsset(mesh,path);
      mesh.vertices=new[]{new Vector3(-.5f,0,-.5f),new Vector3(-.5f,0,.5f),new Vector3(.5f,0,.5f),new Vector3(.5f,0,-.5f)};
      mesh.triangles=new[]{0,1,2,0,2,3};
      mesh.uv=new[]{new Vector2(0,0),new Vector2(0,1),new Vector2(1,1),new Vector2(1,0)};
      mesh.colors=new[]{Color.white,Color.white,Color.white,Color.white};
      mesh.RecalculateNormals();mesh.RecalculateTangents();mesh.RecalculateBounds();
      EditorUtility.SetDirty(mesh);
    }

    [Serializable] private sealed class ArtCatalog { public ArtMaterial[] materials; }
    [Serializable] private sealed class ArtMaterial { public string name; public float metallic; public float smoothness; public float emission; }

    private static void CreateMaterial(string name, Color tint, float metallic, float smoothness) {
      CreateMaterialAt(ResourceRoot, name, tint, metallic, smoothness);
    }

    private static void CreateMaterialAt(string root, string name, Color tint, float metallic, float smoothness) {
      var texturePath = $"{root}/{name}.BaseColor.png";
      var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
      if (texture == null) {
        throw new InvalidOperationException($"Required material texture is missing: {texturePath}");
      }
      var shader = Shader.Find("Universal Render Pipeline/Lit");
      if (shader == null) {
        throw new InvalidOperationException("Required shader is missing: Universal Render Pipeline/Lit");
      }
      // Unity reimports a changed image on its own; only wrong import settings
      // need a forced reimport.
      var importer = (TextureImporter)AssetImporter.GetAtPath(texturePath);
      if (!importer.sRGBTexture || importer.wrapMode != TextureWrapMode.Repeat) {
        importer.sRGBTexture = true;
        importer.wrapMode = TextureWrapMode.Repeat;
        importer.SaveAndReimport();
      }
      var materialPath = $"{root}/{name}.mat";
      var material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
      if (material == null) {
        material = new Material(shader) { name = name };
        AssetDatabase.CreateAsset(material, materialPath);
      }
      // Written only when a property differs, so unchanged materials stay as saved.
      if (material.shader == shader && material.GetColor("_BaseColor") == tint && material.GetTexture("_BaseMap") == texture
          && material.GetFloat("_Metallic") == metallic && material.GetFloat("_Smoothness") == smoothness) return;
      material.shader = shader;
      material.SetColor("_BaseColor", tint);
      material.SetTexture("_BaseMap", texture);
      material.SetFloat("_Metallic", metallic);
      material.SetFloat("_Smoothness", smoothness);
      EditorUtility.SetDirty(material);
    }
  }
}
#endif
