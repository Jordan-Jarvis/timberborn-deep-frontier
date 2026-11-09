using System;
using System.Linq;
using Timberborn.Persistence;
using Timberborn.SerializationSystem;
using ModdableFluids.Runtime.Prototype;

namespace ModdableFluids.Native.Acceptance {
  /// <summary>
  /// The game-side save envelope through the game's own ObjectSaver, JSON writer/reader and
  /// ObjectLoader, under the installed Mono: the stored document must come back with the same
  /// content digest and provider state, and an absent or unknown envelope must stop loading.
  /// </summary>
  internal static class WorldSaveProbe {
    internal static int Run(FluidSaveDocument document) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var json = new SerializedObjectReaderWriter(new JsonMerger());
      FluidWorldSaveFormat.Loaded RoundTrip(Action<IObjectSaver> write, out string text) {
        var saved = new SerializedObject();
        write(new ObjectSaver(saved));
        text = json.WriteJson(saved);
        return FluidWorldSaveFormat.Read(new ObjectLoader(json.ReadJson(text)));
      }
      string digest = FluidWorldSaveFormat.ContentDigest(document);
      var loaded = RoundTrip(saver => FluidWorldSaveFormat.Write(saver, document), out string written);
      Check(!loaded.NativeOnly && FluidWorldSaveFormat.ContentDigest(loaded.Document) == digest, "Mono native save envelope round trip changed the fluid document");
      Check(document.EntryVolume.All(volume => written.Contains("\"" + volume + "\"")), "Saved volumes are not stored as their exact hex strings");
      var states = document.GetProviderStates();
      Check(loaded.ProviderStates.Count == states.Count && loaded.ProviderStates.Zip(states, (a, b) => a.ProviderId == b.ProviderId && a.OwnerModId == b.OwnerModId
        && a.SchemaVersion == b.SchemaVersion && a.Data == b.Data).All(same => same), "Provider state changed through the native save envelope");
      var nativeOnly = RoundTrip(saver => FluidWorldSaveFormat.WriteNativeOnly(saver, states, false), out _);
      Check(nativeOnly.NativeOnly && !nativeOnly.ImportPending && nativeOnly.ProviderStates.Count == states.Count, "Native-only envelope round trip");
      var pending = RoundTrip(saver => FluidWorldSaveFormat.WriteNativeOnly(saver, states, true), out _);
      Check(pending.NativeOnly && pending.ImportPending, "A pending import did not survive the native save envelope");
      // Envelope 1 (0.1.2) has no ImportPending key and reads as no pending import.
      var first = new SerializedObject();
      var firstSaver = new ObjectSaver(first);
      firstSaver.Set(new PropertyKey<int>("EnvelopeVersion"), 1); firstSaver.Set(new PropertyKey<bool>("NativeOnly"), true);
      foreach (var name in new[] { "ProviderIds", "ProviderOwners", "ProviderData" }) firstSaver.Set(new ListKey<string>(name), Array.Empty<string>());
      firstSaver.Set(new ListKey<int>("ProviderSchemas"), Array.Empty<int>());
      var firstLoaded = FluidWorldSaveFormat.Read(new ObjectLoader(json.ReadJson(json.WriteJson(first))));
      Check(firstLoaded.NativeOnly && !firstLoaded.ImportPending, "Envelope 1 did not load as written");
      Check(FluidWorldSaveFormat.ContentDigest(FluidWorldSaveFormat.WithProviderStates(document, Array.Empty<FluidProviderState>())) == digest,
        "Provider state is part of the content digest");
      bool missing = false;
      try { FluidWorldSaveFormat.Read(new ObjectLoader(new SerializedObject())); } catch (FluidSaveException e) { missing = e.Message.Contains("EnvelopeVersion"); }
      Check(missing, "A save entry without an envelope version loaded");
      bool newer = false;
      var future = new SerializedObject();
      new ObjectSaver(future).Set(new PropertyKey<int>("EnvelopeVersion"), 3);
      try { FluidWorldSaveFormat.Read(new ObjectLoader(future)); } catch (FluidSaveException e) { newer = e.Message.Contains("envelope 3"); }
      Check(newer, "An unknown save envelope version loaded");
      return checks;
    }
  }
}
