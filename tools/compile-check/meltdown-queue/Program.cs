// Runs the production Request/Tick method bodies verbatim. The doubles model
// native synchronous EntityComponent deletion and deferred Unity destruction;
// they do not simulate blast geometry, fluid transport or Unity rendering.
using DeepFrontier.Scripts.Meltdown;

int checks = 0;
void Check(bool condition, string message) {
  checks++;
  if (!condition) throw new Exception(message);
}
foreach (bool reverse in new[] {false, true}) {
  var first = new ReactorCore();
  var second = new ReactorCore();
  var service = new MeltdownService();
  service.OnExecute = core => {
    Check(!core.Entity.Deleted, "Attempted meltdown of a reactor removed by the earlier blast");
    // Either back-to-back reactor destroys both, without destroying their
    // Unity objects until the end of the frame.
    first.Entity.Deleted = second.Entity.Deleted = true;
  };
  service.Request(reverse ? second : first);
  service.Request(reverse ? first : second);
  service.Tick();
  Check(service.Executed.Count == 1, "Overlapping pair must not execute the destroyed second reactor");
  Check(first && second, "Reproduction requires both Unity references still valid");
  service.Tick();
  Check(service.Executed.Count == 1, "Finished batch must not repeat");
}
{
  var service = new MeltdownService();
  var first = new ReactorCore();
  var second = new ReactorCore();
  service.OnExecute = core => core.Entity.Deleted = true;
  service.Request(first); service.Request(first); service.Request(second);
  service.Tick();
  Check(service.Executed.SequenceEqual(new[] {first, second}), "Separated reactors must both execute, exactly once");
}
{
  var service = new MeltdownService();
  var removed = new ReactorCore();
  var destroyed = new ReactorCore {UnityAlive = false};
  service.Request(removed); service.Request(destroyed);
  removed.Entity.Deleted = true;
  service.Tick();
  Check(service.Executed.Count == 0, "Deletion before the batch must cancel queued work");
}
{
  var service = new MeltdownService();
  var first = new ReactorCore();
  var next = new ReactorCore();
  service.OnExecute = core => {if (core == first) service.Request(next);};
  service.Request(first); service.Tick();
  Check(service.Executed.SequenceEqual(new[] {first}), "New requests retain next-tick semantics");
  service.Tick();
  Check(service.Executed.SequenceEqual(new[] {first, next}), "New requests must not be lost");
}
Console.WriteLine($"PASS {checks} meltdown queue checks (production method bodies; deferred-destruction doubles)");

namespace DeepFrontier.Scripts.Meltdown {
  internal sealed class EntityComponent { public bool Deleted; }
  internal sealed class ReactorCore {
    public readonly EntityComponent Entity = new();
    public bool UnityAlive = true;
    public T GetComponent<T>() => (T)(object)Entity;
    public static implicit operator bool(ReactorCore core) => core != null && core.UnityAlive;
  }
  internal sealed partial class MeltdownService {
    private readonly List<ReactorCore> _pending = new();
    public readonly List<ReactorCore> Executed = new();
    public Action<ReactorCore> OnExecute = _ => {};
    private void Execute(ReactorCore core) { Executed.Add(core); OnExecute(core); }
  }
}
