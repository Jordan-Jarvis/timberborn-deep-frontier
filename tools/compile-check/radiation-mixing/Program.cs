using System.Reflection;

// Runs the actual compiled mod's pure mixing methods, without Unity or a settlement.
// Pass an explicit DeepFrontier.dll and the official publicized Managed directory.
// No copied implementation or test stubs.
if (args.Length != 2) throw new ArgumentException("Expected DeepFrontier.dll and official publicized Managed directory");
var assembly = Assembly.LoadFrom(Path.GetFullPath(args[0]));
var mixing = assembly.GetType("DeepFrontier.Scripts.Radiation.RadiationMixing", throwOnError:true)!;
var replay = mixing.GetMethod("ReplayChange", BindingFlags.Public | BindingFlags.Static)!;
var require = mixing.GetMethod("RequireShares", BindingFlags.Public | BindingFlags.Static)!;
var kernelExcess = mixing.GetMethod("KernelExcess", BindingFlags.Public | BindingFlags.Static)!;
int cases = 0, failures = 0;
void Check(bool condition, string message) {
  cases++;
  if (!condition) { failures++; if (failures <= 8) Console.WriteLine("FAIL " + message); }
}
void Removal(float clean, float bad, float radioactive, float taken, string name) {
  float initialShare = radioactive / (clean + bad);
  require.Invoke(null, new object[] { bad / (clean + bad), initialShare, name + " initial" });
  object[] values = { clean, bad, radioactive, -taken, 0f, 0f };
  float removed = (float)replay.Invoke(null, values)!;
  float left = (float)values[0], badLeft = (float)values[1], rLeft = (float)values[2];
  float share = left + badLeft > 0 ? rLeft / (left + badLeft) : 0;
  bool valid = true;
  try { require.Invoke(null, new object[] { left + badLeft > 0 ? badLeft / (left + badLeft) : 0, share, name }); }
  catch (TargetInvocationException e) when (e.InnerException is InvalidOperationException) { valid = false; }
  Check(valid, $"{name}: share {initialShare:R} became {share:R} (clean {left:R}, radioactive {rLeft:R})");
  double expected = clean > 0 ? (double)radioactive * Math.Max(0, clean - taken) / clean : 0;
  Check(Math.Abs(rLeft - expected) <= Math.Abs(expected) * 2e-7 + 1e-35,
    $"{name}: retained {rLeft:R}, proportional result {expected:R}");
  Check(removed >= 0 && rLeft >= 0 && Math.Abs((double)removed + rLeft - radioactive) <= Math.Abs(radioactive) * 1e-7,
    $"{name}: removal did not conserve radioactive volume");
}

// Accepted floating-point shares near 100%, then a pump nearly empties the column.
Removal(.031250011175870895f, 0, .03125024959445f, .031249849125742912f, "near-empty pump regression");
Removal(.24999971687793732f, 0, .2500011920928955f, .24999898672103882f, "second near-empty regression");
Removal(10, 2, 4, 3, "mixed water partial removal");
Removal(10, 2, 4, 12, "complete clean-water removal");
Removal(10, 0, 0, 7, "fresh-water removal");
Removal(10, 0, 10, 7, "pure radioactive removal");

var random = new Random(491);
for (int i = 0; i < 10000; i++) {
  float clean = (float)Math.Exp(random.NextDouble() * 16 - 12);
  float radioactive = clean * (float)random.NextDouble();
  float taken = clean * (float)(.99 + random.NextDouble() * .01);
  Removal(clean, 0, radioactive, taken, "pump sample " + i);
}
object[] addition = { 2f, 1f, 1f, 4f, 0f, 1f };
Check((float)replay.Invoke(null, addition)! == 0 && (float)addition[0] == 6 && (float)addition[1] == 1 && (float)addition[2] == 5,
  "radioactive addition changed");
// The kernel's soil-transfer rule must not retain a surplus in a nearly all-bad
// column. A later badwater-only removal magnifies that surplus relative to total
// water even though the radioactive amount is unchanged.
void KernelThenBadRemoval(float kernelBad, float kernelRadioactive, float depth, float taken, string name) {
  object[] kernelValues = { kernelBad, kernelRadioactive, 0f };
  float kernelRetained = (float)kernelExcess.Invoke(null, kernelValues)!;
  Check(kernelRetained <= 1f - kernelBad, name + ": kernel left more radioactive water than its clean-water capacity");
  Check(Math.Abs((double)kernelRetained + (float)kernelValues[2] - kernelRadioactive) < 1e-11,
    name + ": kernel soil transfer lost radioactive volume");
  object[] badRemoval = { depth*(1f-kernelBad), depth*kernelBad, depth*kernelRetained, -taken, 1f, 0f };
  replay.Invoke(null, badRemoval);
  bool validBadRemoval = true;
  try {
    float total = (float)badRemoval[0] + (float)badRemoval[1];
    require.Invoke(null, new object[] { (float)badRemoval[1]/total, (float)badRemoval[2]/total, "badwater removal after kernel" });
  } catch (TargetInvocationException e) when (e.InnerException is InvalidOperationException) { validBadRemoval = false; }
  Check(validBadRemoval, name + ": badwater removal amplified the kernel's retained surplus beyond the share tolerance");
}
KernelThenBadRemoval(.9998f, .000205f, 1f, .9f, "small kernel surplus");
// Build 277's exact failing cell 6412: one badwater removal, no clean-water change.
float traceClean = 3.97814256E-05f, traceBad = .206209153f, traceRadioactive = 4.14364476E-05f;
float traceDepth = traceClean + traceBad;
KernelThenBadRemoval(traceBad / traceDepth, traceRadioactive / traceDepth,
  traceDepth, .149856851f, "live crash cell 6412");
NativeSourceRegression.Run(assembly, Path.GetFullPath(args[1]), Check);
Console.WriteLine($"{cases - failures}/{cases} checks passed; {failures} failures.");
return failures == 0 ? 0 : 1;
