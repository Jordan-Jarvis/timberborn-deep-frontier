using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectModelSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.BuildingTools;
using Timberborn.Coordinates;
using Timberborn.CoreUI;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.GoodsUI;
using Timberborn.Localization;
using Timberborn.Rendering;
using Timberborn.SelectionSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.ToolSystemUI;
using UnityEngine;
using UnityEngine.UIElements;
using Object = UnityEngine.Object;

namespace DeepFrontier.Scripts.SteelStructures {
  // Steel decks on legs (docs/platforms-design.md, slice 2 "assisted placement").
  //
  // A tool template (SteelLegDeck<n>x<n>H<k>, tools/structural_building_content.mjs)
  // is only ever a preview: native BlockObjectTool asks BlockObjectPlacerService
  // for the template's placer, and SteelDeckPlacer (claimed through the native
  // IBlockObjectPlacer extension point) builds native entities instead of it:
  // one stack of SteelColumnH* per deck foundation, then the real SteelDeck.
  // After that click everything is a native entity with native support,
  // deletion, construction order and load validation (the deck's corner
  // foundations stand on the column caps, the column foundations on the bed).
  //
  // The tool's own blocks are the deck's at layer DeckZ (corner foundations
  // relaxed to Any), plus one foot block at z = 0 under the footprint centre:
  // MatterBelow GroundOrStackable, Occupations None. Native picking puts that
  // centre cell on the terrain or stackable top under the cursor
  // (BlockObjectPreviewPicker.CenteredPreviewCoordinates), so the foot is
  // natively valid wherever the tool can be shown, and native
  // BlockObject.IsAlmostValid (one valid solid-matter block) keeps an
  // unbuildable preview visible with this file's placement message instead of
  // hiding it. The foot occupies nothing and never becomes an entity.
  //
  // Leg lengths come from the native BlockValidator: for each deck foundation
  // the planner tries L = 0 (the deck foundation's own MatterBelow, native
  // MatterBelowValidator) and then L = 1..MaxDepth with a column stack of
  // exactly the blocks that will be built (BlockValidator.BlocksValid on the
  // stacked column blocks; a joint between two stacked columns needs no check
  // because the lower column's cap is a stackable block), and keeps the
  // shortest valid one. Any bed the native rules accept counts: terrain (also
  // under water), platforms, stackable roofs and roof hardpoints.
  internal record SteelDeckToolSpec : ComponentSpec {
    // Template name of the deck that gets built (a one-layer BlockObject whose
    // solid-matter blocks are its leg foundations).
    [Serialize] public string DeckTemplate { get; init; }
    // Local z of the deck layer in the tool: its height above the pointed surface.
    [Serialize] public int DeckZ { get; init; }
    // Column templates by height: Columns[k-1] is k layers high.
    [Serialize] public ImmutableArray<string> Columns { get; init; }
    // Nodes under the tool's finished model, one per column template, cloned to
    // draw the columns of the current placement.
    [Serialize] public ImmutableArray<string> ColumnNodes { get; init; }
    // Longest leg in layers below the deck.
    [Serialize] public int MaxDepth { get; init; }
  }

  internal static class SteelLegLoc {
    // English source text: tools/structural_building_content.mjs (STEEL_LEG_ROWS).
    public const string Blocked="DeepFrontier.SteelLegs.Blocked";
    public const string TooDeep="DeepFrontier.SteelLegs.TooDeep";
    public const string Columns="DeepFrontier.SteelLegs.Columns";
    public const string NoColumns="DeepFrontier.SteelLegs.NoColumns";
    public const string PointAt="DeepFrontier.SteelLegs.PointAt";
  }

  internal enum LegFailure { None, Blocked, TooDeep }

  // One deck foundation: the deck cell it carries, and either its column stack
  // (Length layers, 0 = the deck stands directly on a bed) or why none fits.
  // Probed is how many cells below the deck were examined.
  internal readonly struct SteelLeg {
    public Vector3Int DeckCell { get; }
    public int Length { get; }
    public LegFailure Failure { get; }
    public int Probed { get; }
    public SteelLeg(Vector3Int deckCell,int length,LegFailure failure,int probed) {
      DeckCell=deckCell;Length=length;Failure=failure;Probed=probed;
    }
    // Foundation cell of the bottom column (the bed is the cell below it).
    public Vector3Int Bottom=>DeckCell-new Vector3Int(0,0,Length);
  }

  internal sealed class SteelLegPlan {
    public SteelLegPlan(SteelDeckModel model,Placement deck,SteelLeg[] legs) {
      Model=model;DeckPlacement=deck;Legs=legs;
      Failure=legs.Any(l=>l.Failure==LegFailure.Blocked)?LegFailure.Blocked
        :legs.Any(l=>l.Failure==LegFailure.TooDeep)?LegFailure.TooDeep:LegFailure.None;
    }
    public SteelDeckModel Model { get; }
    public Placement DeckPlacement { get; }
    public SteelLeg[] Legs { get; }
    public LegFailure Failure { get; }
    public bool Valid=>Failure==LegFailure.None;
    public int Frame { get; set; }

    // Every column to build, bottom-up per leg: template index (height - 1)
    // and foundation cell.
    public IEnumerable<(int column,Vector3Int cell)> Columns() {
      if(!Valid)throw new InvalidOperationException("An unsupported steel deck plan has no columns.");
      foreach(var leg in Legs) {
        var z=leg.Bottom.z;
        foreach(var height in Model.Segments(leg.Length)) {
          yield return (height-1,new Vector3Int(leg.DeckCell.x,leg.DeckCell.y,z));
          z+=height;
        }
      }
    }

    public bool SameLayout(SteelLegPlan other)=>other!=null&&other.Model==Model&&
      other.DeckPlacement.Equals(DeckPlacement)&&other.Legs.SequenceEqual(Legs);
  }

  // The checked templates behind one tool spec.
  internal sealed class SteelDeckModel {
    public SteelDeckModel(SteelDeckToolSpec spec,TemplateSpec deck,Blocks deckBlocks,TemplateSpec[] columns,BlockObjectSpec[] legSpecs) {
      Spec=spec;Deck=deck;DeckBlocks=deckBlocks;Columns=columns;_legSpecs=legSpecs;
    }
    private readonly BlockObjectSpec[] _legSpecs;
    public SteelDeckToolSpec Spec { get; }
    public TemplateSpec Deck { get; }
    public Blocks DeckBlocks { get; }
    public TemplateSpec[] Columns { get; }
    public BlockObjectSpec LegSpec(int length)=>_legSpecs[length];

    // Column heights of a leg L layers long, bottom-up: full-height columns,
    // with the remainder as the bottom column. Every split into the same
    // number of columns costs the same (each column's cost is linear in its
    // height plus one fixed part).
    public IEnumerable<int> Segments(int length) {
      int tallest=Columns.Length,remainder=length%tallest;
      if(remainder>0)yield return remainder;
      for(int i=0;i<length/tallest;i++)yield return tallest;
    }
  }

  internal sealed class SteelLegPlanner : IPostLoadableSingleton {
    private readonly TemplateService _templates;
    private readonly TemplateNameMapper _names;
    private readonly BlockValidator _blockValidator;
    private readonly MatterBelowValidator _matterBelow;
    private readonly IBlockService _blocks;
    private readonly ITerrainService _terrain;
    private readonly Dictionary<SteelDeckToolSpec,SteelDeckModel> _models=new();
    private readonly Dictionary<SteelDeckToolSpec,SteelLegPlan> _shown=new();
    private SteelLegPlan _cached;
    private SteelDeckToolSpec _cachedSpec;
    private Placement _cachedPlacement;

    public SteelLegPlanner(TemplateService templates,TemplateNameMapper names,BlockValidator blockValidator,
        MatterBelowValidator matterBelow,IBlockService blocks,ITerrainService terrain) {
      _templates=templates;_names=names;_blockValidator=blockValidator;_matterBelow=matterBelow;_blocks=blocks;_terrain=terrain;
    }

    // Every tool template is checked when the game loads, so a broken contract
    // fails at load and not at the first preview.
    public void PostLoad() {
      foreach(var spec in _templates.GetAll<SteelDeckToolSpec>())Model(spec);
    }

    public SteelDeckModel Model(SteelDeckToolSpec spec) {
      if(_models.TryGetValue(spec,out var model))return model;
      model=Build(spec);
      _models.Add(spec,model);
      return model;
    }

    // Plan of a tool preview, computed once per frame and placement (the
    // validator, the leg models and the tool panel all ask in the same frame).
    public SteelLegPlan Plan(BlockObject tool) {
      var spec=tool.GetComponent<SteelDeckToolSpec>();
      var placement=tool.Placement;
      if(_cached!=null&&_cached.Frame==Time.frameCount&&_cachedSpec==spec&&_cachedPlacement.Equals(placement))return _cached;
      _cached=Plan(spec,placement);
      _cached.Frame=Time.frameCount;
      _cachedSpec=spec;_cachedPlacement=placement;
      return _cached;
    }

    // Uncached: the placer plans again against the world without previews.
    public SteelLegPlan Plan(SteelDeckToolSpec spec,Placement tool) {
      var model=Model(spec);
      var deck=new Placement(tool.Coordinates+new Vector3Int(0,0,spec.DeckZ),tool.Orientation,tool.FlipMode);
      var legs=new List<SteelLeg>();
      foreach(var block in PositionedBlocks.From(model.DeckBlocks,deck).GetAllBlocks())
        if(block.MatterBelow.IsSolidMatter())legs.Add(Probe(model,block));
      return new SteelLegPlan(model,deck,legs.ToArray());
    }

    private SteelLeg Probe(SteelDeckModel model,Block foundation) {
      var top=foundation.Coordinates;
      if(_matterBelow.Validate(in foundation))return new SteelLeg(top,0,LegFailure.None,0);
      for(int length=1;length<=model.Spec.MaxDepth;length++) {
        var cell=top-new Vector3Int(0,0,length);
        // Cheap stop: a cell no column block can occupy (off the map, inside
        // terrain, or holding a non-overridable object's Corners) makes every
        // longer leg invalid as well; native BlocksValid rejects each of them
        // for that same cell.
        if(!_blocks.Contains(cell)||_terrain.Underground(cell)||_blocks.AnyNonOverridableObjectsAt(cell,BlockOccupations.Corners))
          return new SteelLeg(top,length,LegFailure.Blocked,length);
        if(_blockValidator.BlocksValid(model.LegSpec(length),new Placement(cell)))
          return new SteelLeg(top,length,LegFailure.None,length);
      }
      return new SteelLeg(top,model.Spec.MaxDepth,LegFailure.TooDeep,model.Spec.MaxDepth);
    }

    // The tool panel shows the plan of the preview drawn last.
    public void RecordShown(SteelDeckToolSpec spec,SteelLegPlan plan)=>_shown[spec]=plan;
    public SteelLegPlan Shown(SteelDeckToolSpec spec)=>_shown.TryGetValue(spec,out var plan)?plan:null;

    private TemplateSpec Template(string name) {
      if(!_names.TryGetTemplate(name,out var template))
        throw new InvalidOperationException($"Steel deck tool names a missing template {name}.");
      return template;
    }

    private SteelDeckModel Build(SteelDeckToolSpec spec) {
      string Fail(string what)=>$"Steel deck tool {spec.DeckTemplate} H{spec.DeckZ}: {what}";
      if(spec.Columns.IsDefaultOrEmpty||spec.ColumnNodes.IsDefault||spec.ColumnNodes.Length!=spec.Columns.Length)
        throw new InvalidOperationException(Fail("needs one model node per column template"));
      if(spec.MaxDepth<1)throw new InvalidOperationException(Fail("MaxDepth must be at least 1"));
      var tool=spec.GetSpec<BlockObjectSpec>();
      var deck=Template(spec.DeckTemplate);
      var deckSpec=deck.GetSpec<BlockObjectSpec>();
      if(deckSpec.Size.z!=1||deckSpec.BaseZ!=0||tool.BaseZ!=0||spec.DeckZ<1||
         tool.Size!=new Vector3Int(deckSpec.Size.x,deckSpec.Size.y,spec.DeckZ+1))
        throw new InvalidOperationException(Fail($"tool size {tool.Size} does not hold the one-layer deck {deckSpec.Size} at layer {spec.DeckZ}"));
      if(!deck.HasSpec<BuildingSpec>()||deck.HasSpec<SteelDeckToolSpec>())
        throw new InvalidOperationException(Fail("the deck must be an ordinary building"));
      int foundations=0;
      for(int y=0;y<deckSpec.Size.y;y++)for(int x=0;x<deckSpec.Size.x;x++) {
        var d=deckSpec.BlockSpecFromCoordinates(new Vector3Int(x,y,0));
        var t=tool.BlockSpecFromCoordinates(new Vector3Int(x,y,spec.DeckZ));
        var solid=d.MatterBelow.IsSolidMatter();
        if(solid)foundations++;
        if(t!=(solid?d with {MatterBelow=MatterBelow.Any}:d))
          throw new InvalidOperationException(Fail($"deck layer block {x},{y} differs from the deck (only foundations become Any)"));
      }
      if(foundations==0)throw new InvalidOperationException(Fail("the deck has no foundation blocks"));
      var foot=new Vector3Int(tool.Size.x/2,tool.Size.y/2,0);
      if(tool.Size.x%2==0||tool.Size.y%2==0)throw new InvalidOperationException(Fail("the footprint needs a centre cell for the foot"));
      for(int z=0;z<spec.DeckZ;z++)for(int y=0;y<tool.Size.y;y++)for(int x=0;x<tool.Size.x;x++) {
        var b=tool.BlockSpecFromCoordinates(new Vector3Int(x,y,z));
        var expected=new BlockSpec {MatterBelow=new Vector3Int(x,y,z)==foot?MatterBelow.GroundOrStackable:MatterBelow.Any,
          Occupations=BlockOccupations.None,Stackable=BlockStackable.None,OccupyAllBelow=false,Underground=false};
        if(b!=expected)throw new InvalidOperationException(Fail($"block {x},{y},{z} under the deck must be empty (the foot at {foot} is GroundOrStackable)"));
      }
      var columns=spec.Columns.Select(Template).ToArray();
      for(int k=1;k<=columns.Length;k++) {
        var c=columns[k-1].GetSpec<BlockObjectSpec>();
        if(c.Size!=new Vector3Int(1,1,k)||c.BaseZ!=0||!columns[k-1].HasSpec<BuildingSpec>())
          throw new InvalidOperationException(Fail($"column {spec.Columns[k-1]} must be a 1x1x{k} building"));
        for(int z=0;z<k;z++) {
          var b=c.BlockSpecFromCoordinates(new Vector3Int(0,0,z));
          if(b.MatterBelow!=(z==0?MatterBelow.GroundOrStackable:MatterBelow.Any)||b.OccupyAllBelow||b.Underground||
             (z==k-1)!=b.Stackable.IsStackable())
            throw new InvalidOperationException(Fail($"column {spec.Columns[k-1]} block {z} breaks the stackable column contract"));
        }
      }
      var model=new SteelDeckModel(spec,deck,Blocks.From(deckSpec),columns,new BlockObjectSpec[spec.MaxDepth+1]);
      var legSpecs=new BlockObjectSpec[spec.MaxDepth+1];
      for(int length=1;length<=spec.MaxDepth;length++) {
        var blocks=new List<BlockSpec>();
        foreach(var height in model.Segments(length)) {
          var c=columns[height-1].GetSpec<BlockObjectSpec>();
          for(int z=0;z<height;z++) {
            var b=c.BlockSpecFromCoordinates(new Vector3Int(0,0,z));
            // The lowest column stands on the bed (native MatterBelow); an upper
            // column's foundation stands on the cap below it.
            blocks.Add(z==0&&blocks.Count>0?b with {MatterBelow=MatterBelow.Any}:b);
          }
        }
        legSpecs[length]=columns[0].GetSpec<BlockObjectSpec>() with {Size=new Vector3Int(1,1,length),Blocks=blocks.ToImmutableArray()};
      }
      return new SteelDeckModel(spec,deck,model.DeckBlocks,columns,legSpecs);
    }
  }

  // Hard rule for tool previews. Only previews: the tool is never an entity,
  // and the deck and columns it places are ordinary buildings that native
  // support rules keep.
  internal sealed class SteelDeckLegValidator : IBlockObjectValidator {
    private readonly SteelLegPlanner _planner;
    private readonly ILoc _loc;
    public SteelDeckLegValidator(SteelLegPlanner planner,ILoc loc) {_planner=planner;_loc=loc;}
    public bool IsValid(BlockObject blockObject,out string errorMessage) {
      errorMessage=null;
      if(!blockObject.IsPreview||!blockObject.HasComponent<SteelDeckToolSpec>())return true;
      var plan=_planner.Plan(blockObject);
      switch(plan.Failure) {
        case LegFailure.None:return true;
        case LegFailure.Blocked:errorMessage=_loc.T(SteelLegLoc.Blocked);return false;
        case LegFailure.TooDeep:errorMessage=_loc.T(SteelLegLoc.TooDeep,plan.Model.Spec.MaxDepth);return false;
        default:throw new ArgumentOutOfRangeException(nameof(plan.Failure),plan.Failure,null);
      }
    }
  }

  // Draws the planned columns under a tool preview with clones of the column
  // models themselves (ColumnNodes), so the preview shows what gets built. A
  // leg without support shows plain one-layer segments down to where its probe
  // stopped. Native PreviewPlacer calls UpdateModel every frame; clones are
  // moved only when the plan's layout changes.
  internal sealed class SteelDeckLegs : BaseComponent, IAwakableComponent, IPostPlacementChangeListener, IModelUpdater {
    private readonly SteelLegPlanner _planner;
    private BlockObject _block;
    private SteelDeckToolSpec _spec;
    private EntityMaterials _materials;
    private HighlightableObject _highlight;
    private GameObject[] _templates;
    private List<GameObject>[] _pools;
    private int[] _used;
    private SteelLegPlan _drawn;

    public SteelDeckLegs(SteelLegPlanner planner) {_planner=planner;}

    public void Awake() {
      _block=GetComponent<BlockObject>();_spec=GetComponent<SteelDeckToolSpec>();
      _materials=GetComponent<EntityMaterials>();_highlight=GetComponent<HighlightableObject>();
      if(_materials==null||_highlight==null)
        throw new InvalidOperationException("Steel deck legs require native EntityMaterials and HighlightableObject");
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      if(finished==null)throw new InvalidOperationException("Steel deck legs require a finished model");
      var transforms=finished.GetComponentsInChildren<Transform>(true);
      _templates=_spec.ColumnNodes.Select(name=> {
        var matches=transforms.Where(t=>t.name==name).ToArray();
        if(matches.Length!=1)throw new InvalidOperationException("Steel deck column node must exist exactly once: "+name);
        matches[0].gameObject.SetActive(false);
        return matches[0].gameObject;
      }).ToArray();
      _pools=_templates.Select(_=>new List<GameObject>()).ToArray();
      _used=new int[_templates.Length];
    }

    public void OnPostPlacementChanged()=>Refresh();
    public void UpdateModel()=>Refresh();

    private void Refresh() {
      if(!_block.IsPreview||!_block.Positioned)return;
      var plan=_planner.Plan(_block);
      _planner.RecordShown(_spec,plan);
      if(plan.SameLayout(_drawn))return;
      _drawn=plan;
      Array.Clear(_used,0,_used.Length);
      bool created=false;
      if(plan.Valid) {
        foreach(var (column,cell) in plan.Columns())Show(column,cell,ref created);
      } else {
        foreach(var leg in plan.Legs) {
          if(leg.Failure==LegFailure.None) {
            var z=leg.Bottom.z;
            foreach(var height in plan.Model.Segments(leg.Length)) {
              Show(height-1,new Vector3Int(leg.DeckCell.x,leg.DeckCell.y,z),ref created);
              z+=height;
            }
          } else {
            // Cells probed and found free; the blocking cell itself stays empty.
            int free=leg.Failure==LegFailure.Blocked?leg.Probed-1:leg.Probed;
            for(int k=1;k<=free;k++)Show(0,leg.DeckCell-new Vector3Int(0,0,k),ref created);
          }
        }
      }
      for(int i=0;i<_pools.Length;i++)
        for(int j=_used[i];j<_pools[i].Count;j++)_pools[i][j].SetActive(false);
      if(created)_highlight.RefreshHighlight();
    }

    private void Show(int column,Vector3Int cell,ref bool created) {
      var pool=_pools[column];
      if(_used[column]==pool.Count) {
        var template=_templates[column];
        var clone=Object.Instantiate(template,template.transform.parent);
        clone.name=template.name+"#"+pool.Count;
        _materials.AddMaterials(clone);
        pool.Add(clone);created=true;
      }
      var instance=pool[_used[column]++];
      // Column models span their cell from its corner. The tool may be rotated
      // and flipped (native flips scale the entity by -1 in X), so the clone
      // keeps the parent's axes and is centred on its cell: a square model
      // covers the same cell in every rotation and flip.
      var t=instance.transform;
      t.localRotation=Quaternion.identity;t.localScale=Vector3.one;
      t.position=CoordinateSystem.GridToWorldCentered(cell);
      t.localPosition+=new Vector3(-.5f,0f,-.5f);
      instance.SetActive(true);
    }
  }

  // Native IBlockObjectPlacer for the tool templates (BuildingPlacer gives
  // them up through SteelDeckPlacerClaim). Each entity is created by the
  // native BuildingPlacer exactly as its own tool would (unfinished, or
  // finished for the native PlaceFinished key and spec), and the tool panel
  // is the native building panel plus a live section with the columns of the
  // spot under the cursor. BuildingPlacer is fetched from the container when
  // first used: it is a member of the same IBlockObjectPlacer multibinding as
  // this placer, so a constructor dependency would be circular.
  internal sealed class SteelDeckPlacer : IBlockObjectPlacer {
    private const string CostSection="Game/ToolPanel/DescriptionPanelCostSection";
    private readonly SteelLegPlanner _planner;
    private readonly IContainer _container;
    private readonly VisualElementLoader _visualElementLoader;
    private readonly GoodItemFactory _goodItemFactory;
    private readonly ILoc _loc;
    private BuildingPlacer _buildingPlacer;

    public SteelDeckPlacer(SteelLegPlanner planner,IContainer container,VisualElementLoader visualElementLoader,
        GoodItemFactory goodItemFactory,ILoc loc) {
      _planner=planner;_container=container;_visualElementLoader=visualElementLoader;_goodItemFactory=goodItemFactory;_loc=loc;
    }

    private BuildingPlacer Buildings=>_buildingPlacer??=_container.GetInstances<IBlockObjectPlacer>().OfType<BuildingPlacer>().Single();

    public bool CanHandle(BlockObjectSpec template)=>template.HasSpec<SteelDeckToolSpec>();

    public void Place(EntitySetup.Builder entitySetupBuilder,Placement placement) {
      var spec=entitySetupBuilder.Template.GetSpec<SteelDeckToolSpec>();
      var plan=_planner.Plan(spec,placement);
      if(!plan.Valid)
        throw new InvalidOperationException($"Steel deck legs changed between validation and placement at {placement.Coordinates} ({plan.Failure}).");
      // Bottom-up: every column and the deck stand on something that already
      // exists (native BlockObject.AddToService refuses an invalid object; an
      // unfinished column cap is a stackable block).
      foreach(var (column,cell) in plan.Columns())
        Buildings.Place(new EntitySetup.Builder(plan.Model.Columns[column].Blueprint),new Placement(cell));
      Buildings.Place(new EntitySetup.Builder(plan.Model.Deck.Blueprint),plan.DeckPlacement);
    }

    public void Describe(BlockObjectTool tool,ToolDescription.Builder builder,Preview preview) {
      Buildings.Describe(tool,builder,preview);
      var spec=tool.Template.GetSpec<SteelDeckToolSpec>();
      var root=new VisualElement();
      var label=new Label();
      label.style.whiteSpace=WhiteSpace.Normal;
      var section=_visualElementLoader.LoadVisualElement(CostSection);
      var materials=section.Q<VisualElement>("Materials")
        ??throw new InvalidOperationException($"{CostSection} has no Materials element");
      root.Add(label);root.Add(section);
      SteelLegPlan drawn=null;bool started=false;
      builder.AddUpdatableSection(root,()=> {
        var plan=_planner.Shown(spec);
        if(plan!=null&&plan.Frame<Time.frameCount-1)plan=null;
        if(started&&(plan==null?drawn==null:plan.SameLayout(drawn)))return;
        started=true;drawn=plan;
        materials.Clear();
        if(plan==null||!plan.Valid) {
          label.text=_loc.T(SteelLegLoc.PointAt,spec.MaxDepth);
          section.style.display=DisplayStyle.None;
          return;
        }
        var columns=plan.Columns().ToArray();
        if(columns.Length==0) {
          label.text=_loc.T(SteelLegLoc.NoColumns);
          section.style.display=DisplayStyle.None;
          return;
        }
        label.text=_loc.T(SteelLegLoc.Columns,columns.Length,plan.Legs.Sum(l=>l.Length));
        var totals=new List<(string id,int amount)>();
        foreach(var (column,_) in columns)
          foreach(var good in plan.Model.Columns[column].GetSpec<BuildingSpec>().BuildingCost) {
            var i=totals.FindIndex(t=>t.id==good.Id);
            if(i<0)totals.Add((good.Id,good.Amount));else totals[i]=(good.Id,totals[i].amount+good.Amount);
          }
        foreach(var (id,amount) in totals)materials.Add(_goodItemFactory.Create(new GoodAmountSpec {Id=id,Amount=amount},true));
        section.style.display=DisplayStyle.Flex;
      });
    }
  }

  [Context("Game")]
  public sealed class SteelLegDeckConfigurator : Configurator {
    protected override void Configure() {
      Bind<SteelLegPlanner>().AsSingleton();
      Bind<SteelDeckLegs>().AsTransient();
      Bind<SteelDeckLegValidator>().AsSingleton();
      MultiBind<IBlockObjectValidator>().ToExisting<SteelDeckLegValidator>();
      MultiBind<IBlockObjectPlacer>().To<SteelDeckPlacer>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<SteelDeckToolSpec,SteelDeckLegs>();
      // As AdaptiveSupports and native WaterInputPipe: the clones' materials.
      b.AddDecorator<SteelDeckLegs,EntityMaterials>();
      return b.Build();
    }
  }
}
