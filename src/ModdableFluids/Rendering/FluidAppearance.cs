using System;
using System.Collections.Generic;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.Rendering.Prototype {
  /// <summary>One column's resolved tint: colour and the strength with which it covers the native water look.</summary>
  public readonly struct FluidAppearance : IEquatable<FluidAppearance> {
    public byte Red { get; }
    public byte Green { get; }
    public byte Blue { get; }
    /// <summary>0 keeps the native water and badwater shading exactly; 255 is a fully opaque tint.</summary>
    public byte Strength { get; }
    public FluidAppearance(byte red, byte green, byte blue, byte strength) { Red = red; Green = green; Blue = blue; Strength = strength; }
    public bool Equals(FluidAppearance other) => Red == other.Red && Green == other.Green && Blue == other.Blue && Strength == other.Strength;
    public override bool Equals(object obj) => obj is FluidAppearance other && Equals(other);
    public override int GetHashCode() => Red | Green << 8 | Blue << 16 | Strength << 24;
    public override string ToString() => "(" + Red + ", " + Green + ", " + Blue + "; " + Strength + ")";
  }

  /// <summary>
  /// Resolves a mixture to one tint, independent of how many fluids are registered. Water and badwater
  /// keep the native shader's look (badwater stays on the native contamination channel), so a mixture
  /// of only those resolves to strength 0. Each extra fluid has a weight w = alpha * visibility(share),
  /// where visibility is the fluid's declared curve (<see cref="FluidVisibility"/>) or its share. Each
  /// fluid's tint covers what the others leave: strength = 1 - product(1 - w), which is in [0, 1] for any
  /// curves and equals w for a single fluid; the colour is the w-weighted mean. Nothing is clamped.
  /// </summary>
  public sealed class FluidAppearanceResolver {
    private readonly int[] _extras;
    private readonly double[] _red, _green, _blue, _alpha;
    private readonly FluidVisibility[] _visibility;
    public int ComponentCount { get; }

    public FluidAppearanceResolver(FluidRegistry registry) {
      if (registry == null) throw new ArgumentNullException(nameof(registry));
      ComponentCount = registry.Count;
      var extras = new List<int>();
      _red = new double[registry.Count]; _green = new double[registry.Count]; _blue = new double[registry.Count]; _alpha = new double[registry.Count];
      _visibility = new FluidVisibility[registry.Count];
      for (int c = 0; c < registry.Count; c++) {
        var definition = registry.Definitions[c];
        if (definition.NativeRole != FluidNativeRole.Extra) continue;
        if (!definition.HasColor) throw new InvalidOperationException("Extra fluid " + definition.Id + " has no colour");
        extras.Add(c);
        _red[c] = definition.Color.Red; _green[c] = definition.Color.Green; _blue[c] = definition.Color.Blue; _alpha[c] = definition.Color.Alpha;
        _visibility[c] = definition.Visibility;
      }
      _extras = extras.ToArray();
    }

    public FluidAppearance Resolve(FluidVolumes mixture) {
      if (mixture == null || mixture.ComponentCount != ComponentCount) throw new ArgumentException("Mixture layout differs from the registry");
      double total = mixture.TotalVolume;
      if (total == 0) return default;
      double red = 0, green = 0, blue = 0, weight = 0, uncovered = 1;
      foreach (int c in _extras) {
        double share = mixture.GetVolume(c) / total;
        double w = _alpha[c] * (_visibility[c] != null ? _visibility[c].At(share) : FluidVisibility.Linear(share));
        red += w * _red[c]; green += w * _green[c]; blue += w * _blue[c]; weight += w; uncovered *= 1 - w;
      }
      if (weight == 0) return default;
      return new FluidAppearance(Quantize(red / weight), Quantize(green / weight), Quantize(blue / weight), Quantize(1 - uncovered));
    }

    private static byte Quantize(double value) {
      if (double.IsNaN(value) || value < 0 || value > 1 + 1e-12) throw new InvalidOperationException("Resolved appearance channel " + value.ToString("R") + " is outside [0, 1]");
      return (byte)Math.Round(Math.Min(value, 1) * 255, MidpointRounding.AwayFromZero);
    }
  }

  /// <summary>
  /// RGBA8 texels laid out like the native water texture arrays: one layer per vertical column ordinal,
  /// texel (y * width + x) in unpadded map coordinates, four bytes per texel. Update writes the resolved
  /// appearance of every open column at a completed tick, clears texels whose column closed or dried,
  /// grows the layer count when native columns stack higher, and records which rows changed so a
  /// renderer uploads only those. It reads published session values and makes no Unity calls.
  /// </summary>
  public sealed class FluidAppearanceField {
    private readonly int _width, _height;
    private byte[] _texels;
    private readonly HashSet<int> _written = new HashSet<int>();
    private readonly SortedSet<long> _dirtyRows = new SortedSet<long>();
    public int Width => _width;
    public int Height => _height;
    public int Layers { get; private set; }
    public int Updates { get; private set; }

    public FluidAppearanceField(int width, int height) {
      if (width < 1 || height < 1) throw new ArgumentOutOfRangeException(nameof(width));
      _width = width; _height = height; Layers = 1; _texels = new byte[width * height * 4];
    }

    public FluidAppearance Get(int x, int y, int layer) {
      int i = Offset(x, y, layer);
      return new FluidAppearance(_texels[i], _texels[i + 1], _texels[i + 2], _texels[i + 3]);
    }

    /// <summary>A copy of the texels: <see cref="Layers"/> layers of width*height RGBA texels.</summary>
    public byte[] CopyTexels() => (byte[])_texels.Clone();

    /// <summary>Rows changed by the last update, as (layer, y) pairs in ascending order.</summary>
    public IReadOnlyList<(int Layer, int Row)> DirtyRows() {
      var rows = new List<(int, int)>(_dirtyRows.Count);
      foreach (long key in _dirtyRows) rows.Add(((int)(key >> 32), (int)(uint)key));
      return rows;
    }

    public void Update(NativeFluidTransportSession session, FluidAppearanceResolver resolver, int stride) {
      if (session == null || resolver == null) throw new ArgumentNullException("appearance input");
      if (session.Phase != "Ready") throw new InvalidOperationException("Appearance is resolved only at a completed tick; the session is " + session.Phase);
      if (session.ComponentCount != resolver.ComponentCount) throw new ArgumentException("Resolver and session layouts differ");
      if (stride != _width + 2) throw new ArgumentException("Native stride " + stride + " does not match the field width " + _width);
      int verticalStride = stride * (_height + 2);
      _dirtyRows.Clear();
      var now = new HashSet<int>();
      for (int slot = 0; slot < session.ColumnCount; slot++) {
        var geometry = session.GetGeometry(slot);
        int layer = geometry.NativeIndex / verticalStride, cell = geometry.NativeIndex % verticalStride;
        int x = cell % stride - 1, y = cell / stride - 1;
        if (x < 0 || x >= _width || y < 0 || y >= _height) throw new InvalidOperationException("Native column " + geometry.NativeIndex + " lies outside the map");
        if (layer >= Layers) Grow(layer + 1);
        var appearance = resolver.Resolve(session.Sample(geometry.NativeIndex));
        int offset = Offset(x, y, layer);
        if (appearance.Strength != 0) now.Add(offset);
        Write(offset, appearance, layer, y);
      }
      // Columns that closed or dried since the last update.
      foreach (int offset in _written) if (!now.Contains(offset)) {
        int texel = offset / 4, layer = texel / (_width * _height), y = texel % (_width * _height) / _width;
        Write(offset, default, layer, y);
      }
      _written.Clear(); _written.UnionWith(now);
      Updates++;
    }

    private void Write(int offset, FluidAppearance appearance, int layer, int y) {
      if (_texels[offset] == appearance.Red && _texels[offset + 1] == appearance.Green && _texels[offset + 2] == appearance.Blue && _texels[offset + 3] == appearance.Strength) return;
      _texels[offset] = appearance.Red; _texels[offset + 1] = appearance.Green; _texels[offset + 2] = appearance.Blue; _texels[offset + 3] = appearance.Strength;
      _dirtyRows.Add(((long)layer << 32) | (uint)y);
    }

    private void Grow(int layers) {
      var grown = new byte[_width * _height * 4 * layers];
      Buffer.BlockCopy(_texels, 0, grown, 0, _texels.Length);
      _texels = grown; Layers = layers;
    }

    private int Offset(int x, int y, int layer) {
      if (x < 0 || x >= _width || y < 0 || y >= _height || layer < 0 || layer >= Layers) throw new ArgumentOutOfRangeException(nameof(x));
      return ((layer * _height + y) * _width + x) * 4;
    }
  }
}
