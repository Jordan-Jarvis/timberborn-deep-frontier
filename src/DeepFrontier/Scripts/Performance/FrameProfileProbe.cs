using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.Metrics;
using Timberborn.SingletonSystem;
using Timberborn.TimeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Performance {
  // Explicit test launch only (tools/start_frame_profile.ps1): -deepFrontierFrameProfile "<output
  // path without extension>" with -deepFrontierLoadAcceptance -deepFrontierLoadSave and the native
  // -metrics switch. The native benchmark cannot be used with mods (ModManagerScenePanel ignores
  // every mod when -benchmarkLength is given, Timberborn 1.1.2.8), so this probe does the same with
  // mods loaded: once the save runs, it sets WarmUpSpeed, waits WarmUpSeconds, resets the native
  // metrics, records every frame's unscaled time for SampleSeconds, then writes
  //   <path>.csv          the native IMetricsService report: each tickable singleton and tickable
  //                       component type's share of the measured tick time (native "Tick" context)
  //   <path>-frames.csv   one row per frame (ms)
  // and logs the frame statistics and process memory. Normal play binds nothing.
  [Context("Game")]
  public sealed class FrameProfileProbeConfigurator : Configurator {
    protected override void Configure() {
      if (FrameProfileProbe.OutputPath() != null) Bind<FrameProfileProbe>().AsSingleton();
    }
  }

  internal sealed class FrameProfileProbe : IUpdatableSingleton {
    private const string Flag = "-deepFrontierFrameProfile";
    private const string Tag = "[DeepFrontier FrameProfile]";
    private const int StartFrame = 120;          // after AcceptanceStartupPanels and MemoryLoadProbe start
    private const float WarmUpSpeed = 3f;
    private const float WarmUpSeconds = 20f;
    private const float SampleSeconds = 60f;
    private const long MB = 1024 * 1024;

    private readonly IMetricsService _metrics;
    private readonly SpeedManager _speed;
    private readonly List<float> _frames = new List<float>();
    private readonly string _path = OutputPath();
    private int _frame;
    private float _warmUpLeft = WarmUpSeconds, _sampleLeft = SampleSeconds;
    private bool _finished;

    public FrameProfileProbe(IMetricsService metrics, SpeedManager speed) { _metrics = metrics; _speed = speed; }

    internal static string OutputPath() {
      var args = Environment.GetCommandLineArgs();
      int index = Array.IndexOf(args, Flag);
      if (index < 0) return null;
      if (!args.Contains("-deepFrontierLoadAcceptance")) throw new InvalidOperationException($"{Flag} requires -deepFrontierLoadAcceptance");
      if (index == args.Length - 1) throw new InvalidOperationException($"{Flag} must be followed by an output path");
      return Path.GetFullPath(args[index + 1].Trim('"'));
    }

    public void UpdateSingleton() {
      if (_finished || ++_frame < StartFrame) return;
      if (!_metrics.MetricsEnabled) {
        _finished = true;
        Debug.LogError($"{Tag} FAILED the native -metrics switch is missing");
        return;
      }
      float dt = Time.unscaledDeltaTime;
      if (_warmUpLeft > 0f) {
        if (_speed.CurrentSpeed != WarmUpSpeed) _speed.ChangeSpeed(WarmUpSpeed);
        _warmUpLeft -= dt;
        if (_warmUpLeft <= 0f) {
          _metrics.ResetMetrics();
          Debug.Log($"{Tag} sampling {SampleSeconds} s at speed {WarmUpSpeed}; private {ProcessMemory.PrivateBytes() / MB} MB");
        }
        return;
      }
      _frames.Add(dt * 1000f);
      _sampleLeft -= dt;
      if (_sampleLeft > 0f) return;
      _finished = true;
      _speed.ChangeSpeed(0f);
      _metrics.WriteCollectedDataToFile(_path);
      File.WriteAllLines(_path + "-frames.csv",
        new[] { "frameMs" }.Concat(_frames.Select(ms => ms.ToString("0.###", CultureInfo.InvariantCulture))));
      var sorted = _frames.OrderBy(ms => ms).ToList();
      float Percentile(float p) => sorted[Math.Min(sorted.Count - 1, (int)(p * sorted.Count))];
      float total = _frames.Sum();
      Debug.Log(string.Format(CultureInfo.InvariantCulture,
        "{0} COMPLETE frames={1} avgFps={2:0.0} medianMs={3:0.0} p95Ms={4:0.0} p99Ms={5:0.0} maxMs={6:0.0} over50ms={7} over100ms={8} private {9} MB; report {10}.csv",
        Tag, _frames.Count, _frames.Count / (total / 1000f), Percentile(.5f), Percentile(.95f), Percentile(.99f), sorted[sorted.Count - 1],
        _frames.Count(ms => ms > 50f), _frames.Count(ms => ms > 100f), ProcessMemory.PrivateBytes() / MB, _path));
    }
  }
}
