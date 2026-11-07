using System.Collections;
using System.Reflection;
using System.Runtime.Loader;

// Executes the compiled mod policy and the installed native goods registry.
// Does not instantiate a Unity Inventory or claim save/reload acceptance.
if(args.Length!=2) throw new ArgumentException("Expected mod DLL and game Managed directory");
string managed=Path.GetFullPath(args[1]);
AssemblyLoadContext.Default.Resolving += (_,name) => Assembly.LoadFrom(Path.Combine(managed,name.Name+".dll"));
var mod=Assembly.LoadFrom(Path.GetFullPath(args[0]));
var native=Assembly.LoadFrom(Path.Combine(managed,"Timberborn.Goods.dll"));
var good=native.GetType("Timberborn.Goods.StorableGood",true)!;
var amount=native.GetType("Timberborn.Goods.StorableGoodAmount",true)!;
var registry=native.GetType("Timberborn.Goods.StorableGoodRegistry",true)!;
var policy=mod.GetType("DeepFrontier.Scripts.Radiation.ShieldedRadioactiveStorage",true)!;
var configure=policy.GetMethod("Configure",BindingFlags.Static|BindingFlags.NonPublic)!;
var listType=typeof(List<>).MakeGenericType(amount);
IList List(params (string id,int capacity)[] entries) {
  var list=(IList)Activator.CreateInstance(listType)!;
  foreach(var e in entries) {
    var g=good.GetMethod("CreateGiveableAndTakeable")!.Invoke(null,new object[]{e.id});
    list.Add(Activator.CreateInstance(amount,g,e.capacity));
  }
  return list;
}
int checks=0;
void Check(bool ok,string message) { checks++;if(!ok)throw new Exception(message); }
object Registry(IList list) {
  var r=Activator.CreateInstance(registry)!;
  registry.GetMethod("Add",BindingFlags.Public|BindingFlags.Instance)!.Invoke(r,new object[]{list});
  return r;
}
bool Has(object r,string property,string id) {
  var set=registry.GetProperty(property)!.GetValue(r)!;
  return (bool)set.GetType().GetMethod("Contains")!.Invoke(set,new object[]{id})!;
}
int Capacity(object r,string id) => (int)registry.GetMethod("GetAmount")!.Invoke(r,new object[]{id})!;
var tank=List(("Water",300),("RadioactiveSludge",300),("ContaminatedWater",300));
configure.Invoke(null,new object[]{tank,false,300});
var t=Registry(tank);
Check(!Has(t,"InputGoods","RadioactiveSludge"),"unshielded storage accepts radioactive water");
Check(Has(t,"OutputGoods","RadioactiveSludge"),"old radioactive stock cannot leave");
Check(Capacity(t,"RadioactiveSludge")==0,"incoming radioactive capacity remains");
Check((bool)registry.GetMethod("Contains")!.Invoke(t,new object[]{"RadioactiveSludge"})!,"old stock no longer recognized");
Check(Has(t,"InputGoods","Water")&&Capacity(t,"Water")==300,"ordinary water altered");
Check(Has(t,"InputGoods","ContaminatedWater"),"accidentally contaminated water cleanup broken");
var vault=List(("RadioactiveWaste",1600));
configure.Invoke(null,new object[]{vault,true,1600});
var v=Registry(vault);
Check(Has(v,"InputGoods","RadioactiveSludge")&&Has(v,"OutputGoods","RadioactiveSludge"),"shielded liquid transfer missing");
Check(Capacity(v,"RadioactiveSludge")==1600&&Capacity(v,"RadioactiveWaste")==1600,"vault capacity contract changed");
var warehouse=List(("Log",200));
configure.Invoke(null,new object[]{warehouse,false,200});
Check(warehouse.Count==1,"unrelated storage gained radioactive entry");
var shieldedTank=List(("RadioactiveSludge",300));
configure.Invoke(null,new object[]{shieldedTank,true,300});
Check(shieldedTank.Count==1&&Has(Registry(shieldedTank),"InputGoods","RadioactiveSludge"),"existing shielded liquid entry duplicated");
try {configure.Invoke(null,new object[]{List(("RadioactiveSludge",300),("RadioactiveSludge",300)),false,300});throw new Exception("duplicate accepted");}
catch(TargetInvocationException e) when(e.InnerException is InvalidOperationException){checks++;}
try {configure.Invoke(null,new object[]{List(),true,0});throw new Exception("invalid capacity accepted");}
catch(TargetInvocationException e) when(e.InnerException is ArgumentOutOfRangeException){checks++;}
Console.WriteLine($"Shielded storage: {checks} compiled-policy/native-registry checks passed.");
