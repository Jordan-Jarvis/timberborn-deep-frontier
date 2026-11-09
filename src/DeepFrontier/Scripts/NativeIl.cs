using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

namespace DeepFrontier.Scripts {
  // IL facts a Harmony target is verified against at mod start: its body
  // size (Mono inlines methods whose IL is at most MonoInlineLimit bytes into
  // their callers, which would bypass a patch), the methods it calls and the
  // string literals it loads. Public for the optional assemblies
  // (DeepFrontier.SluiceIsBack), which verify another mod's members the same
  // way. Callers throw their own "native API changed" message.
  public static class NativeIl {
    // Mono INLINE_LENGTH_LIMIT.
    public const int MonoInlineLimit = 20;

    public static int Size(MethodBase method) => method.GetMethodBody()?.GetILAsByteArray()?.Length ?? 0;

    public static bool Inlinable(MethodBase method) => Size(method) <= MonoInlineLimit;

    // Methods named by call/callvirt/newobj operands. Only the method token
    // tables (MethodDef 0x06, MemberRef 0x0A, MethodSpec 0x2B) are resolved.
    public static List<MethodBase> Callees(MethodBase caller) {
      var il = caller.GetMethodBody()?.GetILAsByteArray()
        ?? throw new InvalidOperationException($"{caller.DeclaringType?.Name}.{caller.Name} has no IL body");
      var called = new List<MethodBase>();
      for (int i = 0; i + 4 < il.Length; i++) {
        if (il[i] != 0x28 && il[i] != 0x6F && il[i] != 0x73) continue;
        int token = BitConverter.ToInt32(il, i + 1);
        int table = token >> 24;
        if (table != 0x06 && table != 0x0A && table != 0x2B) continue;
        MethodBase method;
        try {
          method = caller.Module.ResolveMethod(token, caller.DeclaringType?.GetGenericArguments(),
            caller.IsGenericMethod ? caller.GetGenericArguments() : null);
        } catch (ArgumentException) { continue; }
        called.Add(method);
      }
      return called;
    }

    public static bool Calls(MethodBase caller, MethodBase callee) =>
      callee != null && Callees(caller).Any(method => method.Module == callee.Module && method.MetadataToken == callee.MetadataToken);

    // SHA-256 (lower-case hex) of the method's IL bytes: the same digest as
    // System.Reflection.Metadata MethodBodyBlock.GetILBytes on the shipped DLL.
    public static string Sha256(MethodBase method) {
      var il = method.GetMethodBody()?.GetILAsByteArray()
        ?? throw new InvalidOperationException($"{method.DeclaringType?.Name}.{method.Name} has no IL body");
      using var sha = System.Security.Cryptography.SHA256.Create();
      return string.Concat(sha.ComputeHash(il).Select(b => b.ToString("x2")));
    }

    // A prefix that replaces a native method's body (returns false) is a copy
    // of that body plus one change; it stays valid only while the native
    // body is the one it was written from. Throws if the IL differs.
    public static void RequireBody(string feature, MethodBase method, string sha256) {
      if (method == null) throw new InvalidOperationException($"{feature}: native method missing");
      string actual = Sha256(method);
      if (actual != sha256)
        throw new InvalidOperationException($"{feature}: native {method.DeclaringType?.FullName}.{method.Name} differs from Timberborn 1.1.2.8 (IL {actual}); the replacement must be re-derived from the new body");
    }

    // String literals loaded by ldstr (0x72, user-string token table 0x70).
    public static bool LoadsString(MethodBase caller, string literal) {
      var il = caller.GetMethodBody()?.GetILAsByteArray()
        ?? throw new InvalidOperationException($"{caller.DeclaringType?.Name}.{caller.Name} has no IL body");
      for (int i = 0; i + 4 < il.Length; i++) {
        if (il[i] != 0x72) continue;
        int token = BitConverter.ToInt32(il, i + 1);
        if (token >> 24 != 0x70) continue;
        string value;
        try { value = caller.Module.ResolveString(token); } catch (ArgumentException) { continue; }
        if (value == literal) return true;
      }
      return false;
    }
  }
}
