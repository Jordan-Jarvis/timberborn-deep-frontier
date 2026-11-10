using System;
using System.Collections.Generic;

namespace ModdableFluids.Rendering.Prototype {
  /// <summary>
  /// One game scene's terrain overlay surface, CPU half (no Unity calls; the runtime's FluidTerrainRendering uploads it).
  /// It stores every registered overlay's level bytes per terrain cell and resolves them into two texture layouts:
  /// <list type="bullet">
  /// <item><b>Levels</b>, the native <c>TerrainMaterialMap</c> soil-contamination layout: one RG16 layer per terrain z,
  /// texel x + y * width, R old and G new. The drawn level of a cell is the highest of its overlays' levels.</item>
  /// <item><b>Colours</b>, the same addressing in RGBA half floats: sum(level * colour) and sum(level) over the cell's
  /// overlays (levels as byte / 255), so the shader's blended colour sum over its blended level sum is the
  /// level-weighted mean colour.</item>
  /// </list>
  /// <see cref="Publish"/> applies the native update rule once per tick: a cell whose drawn level changed takes R = the
  /// previous G and G = the new level (the native shader interpolates R to G over the tick), and the publish after it
  /// settles R = G. The first publish of a scene, before its first tick, writes R = G at once, as the native PostLoad
  /// settles a loaded map. A cell fading to 0 keeps its colour until it settles, then its colour texel is cleared.
  /// Writes mark their rows; only changed rows are resolved, and only rows whose texels changed are reported for upload.
  /// Layers are allocated on first use; a layer never written stays all zero (the runtime clears every GPU layer once).
  /// </summary>
  public sealed class FluidTerrainOverlayField : IFluidTerrainOverlaySink {
    /// <summary>Bytes per level texel (R old, G new) and half floats per colour texel.</summary>
    public const int LevelBytesPerTexel = 2, ColorHalvesPerTexel = 4;
    private readonly int _mainThread, _overlays, _cells;
    private readonly float[] _red, _green, _blue;
    private readonly byte[][][] _levels;      // [overlay][z][x + y * width]
    private readonly byte[][] _texels;        // [z][2 * cell]: R old, G new
    private readonly ushort[][] _colors;      // [z][4 * cell]: sum(level * colour) RGB, sum(level)
    private readonly Rows[] _written, _unsettled, _levelUploads, _colorUploads;

    public int Width { get; }
    public int Height { get; }
    public int Depth { get; }
    public int OverlayCount => _overlays;
    /// <summary>Texels whose old or new level is not 0: the shader's overlay keyword is needed while this is positive.</summary>
    public int NonZeroTexels { get; private set; }
    /// <summary>Whether any write is waiting for <see cref="Publish"/> or any cell for its settling publish.</summary>
    public bool HasPendingWork { get { for (int z = 0; z < Depth; z++) if (!_written[z].Empty || !_unsettled[z].Empty) return true; return false; } }

    /// <param name="colors">Each overlay's colour in shader space (the runtime linearises material colours in a linear project).</param>
    public FluidTerrainOverlayField(int width, int height, int depth, IReadOnlyList<FluidTerrainOverlayColor> colors, int mainThreadId) {
      if (width < 1 || height < 1 || depth < 1) throw new ArgumentOutOfRangeException(nameof(width), "The terrain overlay surface needs a terrain of at least 1 x 1 x 1, got " + width + " x " + height + " x " + depth);
      if (colors == null) throw new ArgumentNullException(nameof(colors));
      Width = width; Height = height; Depth = depth; _cells = width * height; _mainThread = mainThreadId;
      _overlays = colors.Count;
      _red = new float[_overlays]; _green = new float[_overlays]; _blue = new float[_overlays];
      for (int k = 0; k < _overlays; k++) { _red[k] = colors[k].Red; _green[k] = colors[k].Green; _blue[k] = colors[k].Blue; }
      _levels = new byte[_overlays][][];
      for (int k = 0; k < _overlays; k++) _levels[k] = new byte[depth][];
      _texels = new byte[depth][]; _colors = new ushort[depth][];
      _written = NewRows(depth); _unsettled = NewRows(depth); _levelUploads = NewRows(depth); _colorUploads = NewRows(depth);
    }

    private static Rows[] NewRows(int depth) {
      var rows = new Rows[depth];
      for (int z = 0; z < depth; z++) rows[z] = Rows.None;
      return rows;
    }

    public void SetLevel(int overlay, int x, int y, int z, byte level) {
      int p = Cell(overlay, x, y, z);
      var layer = _levels[overlay][z];
      if (layer == null) {
        if (level == 0) return;
        layer = _levels[overlay][z] = new byte[_cells];
      }
      if (layer[p] == level) return;
      layer[p] = level;
      _written[z].Include(y);
    }

    public byte GetLevel(int overlay, int x, int y, int z) {
      int p = Cell(overlay, x, y, z);
      var layer = _levels[overlay][z];
      return layer == null ? (byte)0 : layer[p];
    }

    private int Cell(int overlay, int x, int y, int z) {
      if (Environment.CurrentManagedThreadId != _mainThread)
        throw new InvalidOperationException("Terrain overlays are written and read on the main thread only (thread " + Environment.CurrentManagedThreadId + ", main thread " + _mainThread + ")");
      if (overlay < 0 || overlay >= _overlays) throw new ArgumentOutOfRangeException(nameof(overlay), overlay, "No terrain overlay has slot " + overlay + " (" + _overlays + " registered)");
      if (x < 0 || x >= Width || y < 0 || y >= Height || z < 0 || z >= Depth)
        throw new ArgumentOutOfRangeException(nameof(x), "Terrain overlay cell (" + x + ", " + y + ", " + z + ") is outside the terrain (" + Width + " x " + Height + " x " + Depth + ")");
      return x + y * Width;
    }

    /// <summary>
    /// The native update for one tick (<paramref name="interpolate"/>) or, before a scene's first tick, the settled one.
    /// Settles what the previous publish changed, then applies every write since.
    /// </summary>
    public void Publish(bool interpolate) {
      if (Environment.CurrentManagedThreadId != _mainThread) throw new InvalidOperationException("Terrain overlays are published on the main thread only");
      if (!interpolate && HasUnsettled()) throw new InvalidOperationException("A settled publish cannot follow an interpolated one whose cells are still settling");
      for (int z = 0; z < Depth; z++) {
        if (!_unsettled[z].Empty) Settle(z);
        if (!_written[z].Empty) Apply(z, interpolate);
      }
    }

    private bool HasUnsettled() { for (int z = 0; z < Depth; z++) if (!_unsettled[z].Empty) return true; return false; }

    private void Settle(int z) {
      var rows = _unsettled[z]; _unsettled[z] = Rows.None;
      var texels = _texels[z]; var colors = _colors[z];
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        for (int x = 0, p = y * Width; x < Width; x++, p++) {
          byte r = texels[2 * p], g = texels[2 * p + 1];
          if (r == g) continue;
          texels[2 * p] = g;
          // r != g, so the texel was non-zero; it stays so only with a non-zero new level.
          if (g == 0) NonZeroTexels--;
          _levelUploads[z].Include(y);
          if (g == 0 && ClearColor(colors, p)) _colorUploads[z].Include(y);
        }
      }
    }

    private void Apply(int z, bool interpolate) {
      var rows = _written[z]; _written[z] = Rows.None;
      var texels = _texels[z] ??= new byte[LevelBytesPerTexel * _cells];
      var colors = _colors[z] ??= new ushort[ColorHalvesPerTexel * _cells];
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        for (int x = 0, p = y * Width; x < Width; x++, p++) {
          byte top = 0; float red = 0, green = 0, blue = 0, sum = 0;
          for (int k = 0; k < _overlays; k++) {
            var layer = _levels[k][z];
            if (layer == null) continue;
            byte level = layer[p];
            if (level == 0) continue;
            if (level > top) top = level;
            float weight = level / 255f;
            red += weight * _red[k]; green += weight * _green[k]; blue += weight * _blue[k]; sum += weight;
          }
          byte r = texels[2 * p], g = texels[2 * p + 1];
          byte nr = interpolate ? (top != g ? g : r) : top, ng = top;
          if (nr != r || ng != g) {
            bool before = r != 0 || g != 0, after = nr != 0 || ng != 0;
            if (before != after) NonZeroTexels += after ? 1 : -1;
            texels[2 * p] = nr; texels[2 * p + 1] = ng;
            _levelUploads[z].Include(y);
          }
          if (nr != ng) _unsettled[z].Include(y);
          if (top > 0) {
            if (SetColor(colors, p, FluidHalf.FromFloat(red), FluidHalf.FromFloat(green), FluidHalf.FromFloat(blue), FluidHalf.FromFloat(sum))) _colorUploads[z].Include(y);
          } else if (ng == 0 && nr == 0 && ClearColor(colors, p)) _colorUploads[z].Include(y);
        }
      }
    }

    private static bool SetColor(ushort[] colors, int p, ushort red, ushort green, ushort blue, ushort sum) {
      int i = ColorHalvesPerTexel * p;
      if (colors[i] == red && colors[i + 1] == green && colors[i + 2] == blue && colors[i + 3] == sum) return false;
      colors[i] = red; colors[i + 1] = green; colors[i + 2] = blue; colors[i + 3] = sum;
      return true;
    }

    private static bool ClearColor(ushort[] colors, int p) => colors != null && SetColor(colors, p, 0, 0, 0, 0);

    /// <summary>The level layer z (R old, G new per texel), or null while nothing was ever drawn on it.</summary>
    public byte[] LevelLayer(int z) => _texels[z];
    /// <summary>The colour layer z (four half floats per texel), or null while nothing was ever drawn on it.</summary>
    public ushort[] ColorLayer(int z) => _colors[z];

    /// <summary>Takes the rows of layer z whose level texels changed since the last call; false when none did.</summary>
    public bool TakeLevelUpload(int z, out int lo, out int hi) => Take(_levelUploads, z, out lo, out hi);
    /// <summary>Takes the rows of layer z whose colour texels changed since the last call; false when none did.</summary>
    public bool TakeColorUpload(int z, out int lo, out int hi) => Take(_colorUploads, z, out lo, out hi);

    private static bool Take(Rows[] uploads, int z, out int lo, out int hi) {
      var rows = uploads[z];
      uploads[z] = Rows.None;
      lo = rows.Lo; hi = rows.Hi;
      return !rows.Empty;
    }

    /// <summary>The level texel of a cell: (old, new).</summary>
    public (byte Old, byte New) Texel(int x, int y, int z) {
      var texels = _texels[z];
      int p = x + y * Width;
      return texels == null ? ((byte)0, (byte)0) : (texels[2 * p], texels[2 * p + 1]);
    }

    /// <summary>The colour texel of a cell, decoded: sum(level * colour) and sum(level).</summary>
    public (float Red, float Green, float Blue, float LevelSum) ColorTexel(int x, int y, int z) {
      var colors = _colors[z];
      int i = ColorHalvesPerTexel * (x + y * Width);
      return colors == null ? (0f, 0f, 0f, 0f)
        : (FluidHalf.ToFloat(colors[i]), FluidHalf.ToFloat(colors[i + 1]), FluidHalf.ToFloat(colors[i + 2]), FluidHalf.ToFloat(colors[i + 3]));
    }

    private struct Rows {
      public static readonly Rows None = new Rows { Lo = int.MaxValue, Hi = int.MinValue };
      public int Lo, Hi;
      public bool Empty => Lo > Hi;
      public void Include(int y) { if (y < Lo) Lo = y; if (y > Hi) Hi = y; }
    }
  }

  /// <summary>IEEE 754 binary16 conversion with round-to-nearest-even (netstandard2.1 has no System.Half).</summary>
  public static class FluidHalf {
    public static ushort FromFloat(float value) {
      uint bits = (uint)BitConverter.SingleToInt32Bits(value);
      uint sign = (bits >> 16) & 0x8000u;
      int exponent = (int)((bits >> 23) & 0xFF);
      uint mantissa = bits & 0x7FFFFFu;
      if (exponent == 0xFF) return (ushort)(sign | 0x7C00u | (mantissa != 0 ? 0x200u : 0u));
      if (exponent > 112) {
        // Normal in half precision (or overflowing to infinity through the rounding carry).
        if (exponent > 142) return (ushort)(sign | 0x7C00u);
        uint half = ((uint)(exponent - 112) << 10) | (mantissa >> 13);
        uint rest = mantissa & 0x1FFFu;
        if (rest > 0x1000u || (rest == 0x1000u && (half & 1u) != 0)) half++;
        return (ushort)(sign | half);
      }
      // Subnormal in half precision: the value in units of 2^-24, rounded to nearest even.
      int shift = 126 - exponent;
      if (shift > 24) return (ushort)sign;
      uint full = mantissa | 0x800000u;
      uint whole = full >> shift, remainder = full & ((1u << shift) - 1u), halfway = 1u << (shift - 1);
      if (remainder > halfway || (remainder == halfway && (whole & 1u) != 0)) whole++;
      return (ushort)(sign | whole);
    }

    public static float ToFloat(ushort half) {
      uint sign = (uint)(half & 0x8000) << 16;
      int exponent = (half >> 10) & 0x1F;
      uint mantissa = (uint)(half & 0x3FF);
      if (exponent == 0) {
        float subnormal = mantissa * 5.9604644775390625E-8f;
        return sign != 0 ? -subnormal : subnormal;
      }
      if (exponent == 0x1F) return BitConverter.Int32BitsToSingle((int)(sign | 0x7F800000u | (mantissa << 13)));
      return BitConverter.Int32BitsToSingle((int)(sign | ((uint)(exponent + 112) << 23) | (mantissa << 13)));
    }
  }
}
