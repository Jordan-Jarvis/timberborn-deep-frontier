using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using FluidsApi.Transport.Prototype;

namespace FluidsApi.Native.Prototype {
  /// <summary>Version-specific reflected access to Timberborn 1.1.2.8 water buffers.</summary>
  /// <remarks>No game types appear in the public contract. Call only at a native-safe simulation stage.</remarks>
  public sealed class NativeWaterArrayAdapter {
    private const BindingFlags Members = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
    private readonly Array _water, _flows, _directed;
    private readonly byte[] _counts;
    private readonly int _width, _height, _stride, _verticalStride;
    private readonly object _depthSetter, _overflowCalculator;
    private readonly MethodInfo _setDepth, _overflowSpace;
    private readonly FieldInfo _floor, _ceiling, _depth, _overflow, _contamination;
    private readonly FieldInfo[] _directions;
    private readonly FieldInfo _origin, _target, _rate;
    public double LastUnfulfilledFlowDemand { get; private set; }
    public double LastRepresentationDifference { get; private set; }

    public NativeWaterArrayAdapter(Array waterColumns, byte[] columnCounts, Array baseFlows, Array directedFlows,
        int width, int height, int stride, int verticalStride, object depthSetter, object overflowCalculator) {
      if (waterColumns == null || columnCounts == null || baseFlows == null || directedFlows == null || depthSetter == null || overflowCalculator == null)
        throw new ArgumentNullException("native buffers");
      if (width <= 0 || height <= 0 || stride != width + 2 || verticalStride != stride * (height + 2) ||
          columnCounts.Length != verticalStride || baseFlows.Length != verticalStride || directedFlows.Length != verticalStride || waterColumns.Length % verticalStride != 0)
        throw new ArgumentException("Native padded buffer dimensions do not match");
      var column = waterColumns.GetType().GetElementType();
      var flow = baseFlows.GetType().GetElementType();
      if (column.FullName != "Timberborn.WaterSystem.WaterColumn" || flow.FullName != "Timberborn.WaterSystem.WaterFlow")
        throw new ArgumentException("Expected Timberborn 1.1.2.8 water buffers");
      _water = waterColumns; _counts = columnCounts; _flows = baseFlows; _directed = directedFlows;
      _width = width; _height = height; _stride = stride; _verticalStride = verticalStride;
      _depthSetter = depthSetter; _overflowCalculator = overflowCalculator;
      _floor = Field(column, "Floor", typeof(byte)); _ceiling = Field(column, "Ceiling", typeof(byte));
      _depth = Field(column, "WaterDepth", typeof(float)); _overflow = Field(column, "Overflow", typeof(float));
      _contamination = Field(column, "Contamination", typeof(float));
      _directions = new[] { Field(flow, "Bottom", typeof(float)), Field(flow, "Left", typeof(float)), Field(flow, "Top", typeof(float)), Field(flow, "Right", typeof(float)) };
      var directed = column.Assembly.GetType("Timberborn.WaterSystem.DirectedFlow", true);
      _origin = Field(directed, "OriginIndex3D", typeof(int)); _target = Field(directed, "TargetIndex3D", typeof(int)); _rate = Field(directed, "Flow", typeof(float));
      _setDepth = depthSetter.GetType().GetMethod("SetWaterDepth", Members, null, new[] { typeof(float), column.MakeByRefType() }, null)
        ?? throw new MissingMethodException("Expected native WaterDepthSetter.SetWaterDepth(float, ref WaterColumn)");
      _overflowSpace = overflowCalculator.GetType().GetMethod("GetOverflowSpace", Members, null, new[] { typeof(float), typeof(byte) }, null)
        ?? throw new MissingMethodException("Expected native WaterOverflowCalculator.GetOverflowSpace(float, byte)");
    }

    private static FieldInfo Field(Type type, string name, Type expected) {
      var field = type.GetField(name, Members);
      if (field == null || field.FieldType != expected) throw new MissingFieldException(type.FullName, name + " : " + expected.Name);
      return field;
    }
    public FluidColumnGeometry[] CaptureGeometry() {
      var result = new List<FluidColumnGeometry>();
      for (int y = 1; y <= _height; y++) for (int x = 1; x <= _width; x++) {
        int cell = y * _stride + x;
        if (_counts[cell] * _verticalStride > _water.Length) throw new InvalidOperationException("Native column count exceeds the supplied arrays");
        for (int ordinal = 0; ordinal < _counts[cell]; ordinal++) {
          int index = cell + ordinal * _verticalStride;
          object water = _water.GetValue(index);
          int floor = (byte)_floor.GetValue(water), ceiling = (byte)_ceiling.GetValue(water);
          if (ceiling == floor) continue;
          double pressureSpace = (float)_overflowSpace.Invoke(_overflowCalculator, new object[] { 0f, (byte)ceiling });
          result.Add(new FluidColumnGeometry(index, cell, floor, ceiling, ceiling - floor + pressureSpace));
        }
      }
      return result.ToArray();
    }
    public double PhysicalVolume(int nativeIndex) {
      object column = _water.GetValue(nativeIndex);
      return (double)(float)_depth.GetValue(column) + (float)_overflow.GetValue(column);
    }
    public double BadwaterShare(int nativeIndex) => (float)_contamination.GetValue(_water.GetValue(nativeIndex));

    /// <summary>
    /// Applies donor capacity at the flow producer, before the native depth task consumes
    /// its rates. Stable edge order assigns only available physical volume. Float rates
    /// round toward zero when necessary so they cannot overdraw a double-precision donor.
    /// </summary>
    public FluidTransfer[] BudgetFlowRequests(FluidColumnGeometry[] layout, FluidVolumes[] mixtures, double deltaTime) {
      if (layout.Length != mixtures.Length || deltaTime <= 0 || double.IsNaN(deltaTime) || double.IsInfinity(deltaTime)) throw new ArgumentException("Invalid transfer snapshot or timestep");
      var slots = new Dictionary<int, int>();
      for (int i = 0; i < layout.Length; i++) slots.Add(layout[i].NativeIndex, i);
      var requests = new List<Request>();
      int[] offsets = { -_stride, -1, _stride, 1 };
      for (int i = 0; i < layout.Length; i++) {
        int index = layout[i].NativeIndex;
        if (index < _verticalStride) for (int direction = 0; direction < 4; direction++) {
          var field = _directions[direction];
          float rate = (float)field.GetValue(_flows.GetValue(index));
          if (rate == 0) continue;
          int sourceIndex = index;
          requests.Add(new Request(i, Resolve(index + offsets[direction], slots), rate, accepted => {
            object flows = _flows.GetValue(sourceIndex); field.SetValue(flows, accepted); _flows.SetValue(flows, sourceIndex);
          }));
        }
        var list = (IList)_directed.GetValue(layout[i].CellIndex);
        for (int n = 0; n < list.Count; n++) {
          object entry = list[n];
          if ((int)_origin.GetValue(entry) != index) continue;
          int item = n, destination = (int)_target.GetValue(entry);
          float rate = (float)_rate.GetValue(entry);
          requests.Add(new Request(i, Resolve(destination, slots), rate, accepted => {
            // DirectedFlow is immutable; use its verified native constructor.
            var constructor = entry.GetType().GetConstructor(new[] { typeof(float), typeof(int), typeof(int) })
              ?? throw new MissingMethodException("DirectedFlow(float, int, int)");
            list[item] = constructor.Invoke(new object[] { accepted, destination, index });
          }));
        }
      }
      foreach (var request in requests) FluidVolumes.RequireQuantity(request.Rate, "native requested flow rate");
      var spent = new double[mixtures.Length];
      var result = new FluidTransfer[requests.Count];
      var acceptedRates = new float[requests.Count];
      double unmet = 0;
      for (int i = 0; i < requests.Count; i++) {
        var request = requests[i];
        double demanded = (double)request.Rate * deltaTime;
        FluidVolumes.RequireQuantity(demanded, "native flow demand");
        float rate = request.Rate;
        double remaining = mixtures[request.Source].TotalVolume - spent[request.Source];
        if (demanded > remaining) {
          rate = (float)(remaining / deltaTime);
          if ((double)rate * deltaTime > remaining) rate = BitConverter.Int32BitsToSingle(BitConverter.SingleToInt32Bits(rate) - 1);
        }
        double accepted = (double)rate * deltaTime;
        spent[request.Source] += accepted;
        unmet += demanded - accepted;
        acceptedRates[i] = rate;
        result[i] = new FluidTransfer(request.Source, request.Destination, accepted);
      }
      // Validate the whole producer batch before publishing any changed rate.
      for (int i = 0; i < requests.Count; i++) requests[i].Write(acceptedRates[i]);
      LastUnfulfilledFlowDemand = unmet;
      return result;
    }
    private int Resolve(int index, Dictionary<int, int> slots) {
      int cell = index % _verticalStride, x = cell % _stride, y = cell / _stride;
      if (index < 0 || x == 0 || x == _stride - 1 || y == 0 || y == _height + 1) return -1;
      if (!slots.TryGetValue(index, out int slot)) throw new InvalidOperationException("Native flow targets a missing interior column " + index);
      return slot;
    }
    public void Publish(int nativeIndex, FluidVolumes mixture, int badwaterComponent, bool writeVolume) {
      object column = _water.GetValue(nativeIndex);
      if (writeVolume) {
        float difference = (float)(mixture.TotalVolume - PhysicalVolume(nativeIndex));
        object[] arguments = { difference, column };
        _setDepth.Invoke(_depthSetter, arguments);
        column = arguments[1];
      }
      _contamination.SetValue(column, (float)mixture.GetShare(badwaterComponent));
      _water.SetValue(column, nativeIndex);
      LastRepresentationDifference = PhysicalVolume(nativeIndex) - mixture.TotalVolume;
    }
    private sealed class Request {
      internal readonly int Source, Destination;
      internal readonly float Rate;
      internal readonly Action<float> Write;
      internal Request(int source, int destination, float rate, Action<float> write) { Source = source; Destination = destination; Rate = rate; Write = write; }
    }
  }
}
