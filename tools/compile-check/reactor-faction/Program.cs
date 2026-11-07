using System.Collections;
using System.Collections.Immutable;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;

if(args.Length!=2)throw new ArgumentException("Expected compiled mod DLL and publicized Managed directory");
var managed=Path.GetFullPath(args[1]);
AssemblyLoadContext.Default.Resolving+=(_,n)=>Assembly.LoadFrom(Path.Combine(managed,n.Name+".dll"));
var mod=Assembly.LoadFrom(Path.GetFullPath(args[0]));
Type Native(string assembly,string type)=>Assembly.LoadFrom(Path.Combine(managed,assembly+".dll")).GetType(type,true)!;
Type Mod(string type)=>mod.GetType("DeepFrontier.Scripts.SuperBots."+type,true)!;
void Set(object target,string name,object value)=>target.GetType().GetProperty(name,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance)!.SetValue(target,value);
var factionType=Native("Timberborn.FactionSystem","Timberborn.FactionSystem.FactionSpec");
var serviceType=Native("Timberborn.GameFactionSystem","Timberborn.GameFactionSystem.FactionService");
var needsType=Native("Timberborn.GameFactionSystem","Timberborn.GameFactionSystem.FactionNeedService");
var needType=Native("Timberborn.NeedSpecs","Timberborn.NeedSpecs.NeedSpec");
var spec=Activator.CreateInstance(Mod("FrontierReactorBotSettingsSpec"))!;
Set(spec,"ReactorNeedIds",ImmutableArray.Create("ReactorCharge","ReactorBotCoolant","ReactorBotPlating"));
Set(spec,"ReplacedNeedIds",ImmutableArray.Create("Energy"));
Set(spec,"RetrofitNeedIds",ImmutableArray.Create("ReactorRetrofitFrame","ReactorRetrofitCell"));
var leakSpec=Activator.CreateInstance(Mod("FrontierReactorBotLeakSpec"))!;
Set(leakSpec,"CoolantNeedId","ReactorBotCoolant");
var needs=RuntimeHelpers.GetUninitializedObject(needsType);
var list=(IList)Activator.CreateInstance(typeof(List<>).MakeGenericType(needType))!;
needsType.GetField("_needs",BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public)!.SetValue(needs,list);
int checks=0;
void PostLoad(object target,string? expected=null) {
  checks++;
  try {target.GetType().GetMethod("PostLoad")!.Invoke(target,null);}
  catch(TargetInvocationException e) when(expected!=null&&e.InnerException is InvalidOperationException x&&x.Message.Contains(expected)) {return;}
  if(expected!=null)throw new Exception("Iron Teeth validation did not reject "+expected);
}
foreach(var id in new[]{"Folktails","Whitepaws","Emberpelts","IronTeeth"}) {
  var faction=Activator.CreateInstance(factionType)!;Set(faction,"Id",id);
  var factions=RuntimeHelpers.GetUninitializedObject(serviceType);Set(factions,"Current",faction);
  var settings=Activator.CreateInstance(Mod("ReactorBotSettings"),new object?[]{null,needs,null,factions})!;Set(settings,"Spec",spec);
  var leaks=Activator.CreateInstance(Mod("ReactorBotLeakSettings"),new object?[]{null,needs,settings})!;Set(leaks,"Spec",leakSpec);
  PostLoad(settings,id=="IronTeeth"?"ReactorCharge is not a Bot need":null);
  PostLoad(leaks,id=="IronTeeth"?"must be a critical Bot need":null);
  if(id=="IronTeeth") {
    foreach(var needId in new[]{"ReactorCharge","ReactorBotCoolant","ReactorBotPlating","Energy","ReactorRetrofitFrame","ReactorRetrofitCell"}) {
      var need=Activator.CreateInstance(needType)!;Set(need,"Id",needId);Set(need,"CharacterType","Bot");list.Add(need);
    }
    PostLoad(settings);
  }
}
Console.WriteLine($"PASS {checks} compiled Reactor Bot faction-validation checks: non-Iron-Teeth skipped, Iron Teeth remains strict");
