using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.Characters;
using Timberborn.Effects;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.NeedSystem;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.TickSystem;
using Timberborn.WorkSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Persistent specialist qualifications of one adult beaver (decorates the
  // native AdultSpec). A beaver can hold every discipline. The skills exist
  // only on this beaver: when it dies (old age, accident, radiation...) they
  // are gone and its specialist workplace loses a crew member until someone
  // else is trained. Study hours toward each discipline it does not hold yet
  // come from free-time visits to a Technical School (SpecialistSchool).
  internal sealed class SpecialistTrait : BaseComponent, IAwakableComponent, IInitializableEntity,
      IPersistentEntity, IDeletableEntity {
    private static readonly ComponentKey Key=new("DeepFrontier.Specialist");
    private static readonly ListKey<string> DisciplinesKey=new("Disciplines");
    private static readonly ListKey<string> StudyDisciplinesKey=new("StudyDisciplines");
    private static readonly ListKey<float> StudyHoursKey=new("StudyHours");
    // Saves before multi-discipline training (one discipline; worker-hours of the old workplace course).
    private static readonly PropertyKey<string> LegacyDisciplineKey=new("Discipline");

    private readonly WorkforceSettings _settings;
    private readonly SpecialistRoster _roster;
    private readonly NotificationBus _notifications;
    private readonly ILoc _loc;
    private readonly List<string> _disciplines=new List<string>();
    private readonly Dictionary<string, float> _studyHours=new Dictionary<string, float>();
    private Character _character;

    public IReadOnlyList<string> Disciplines=>_disciplines;
    public bool IsSpecialist=>_disciplines.Count>0;
    public IReadOnlyDictionary<string, float> StudyHours=>_studyHours;
    public Worker Worker { get; private set; }
    public Citizen Citizen { get; private set; }
    public NeedManager NeedManager { get; private set; }
    public bool Alive=>_character.Alive;
    public string FirstName=>_character.FirstName;

    // The study need of a discipline (written by tools/workforce_risk_content.mjs).
    public static string StudyNeedId(string discipline)=>"Study"+discipline;

    public SpecialistTrait(WorkforceSettings settings, SpecialistRoster roster, NotificationBus notifications, ILoc loc) {
      _settings=settings;_roster=roster;_notifications=notifications;_loc=loc;
    }

    public void Awake() {
      _character=GetComponent<Character>();
      Worker=GetComponent<Worker>();
      Citizen=GetComponent<Citizen>();
      NeedManager=GetComponent<NeedManager>();
      if(!Worker||!Citizen||!NeedManager)throw new InvalidOperationException($"{Name}: a specialist must be a working citizen with needs");
      _character.Died+=OnDied;
    }

    public bool Has(string discipline)=>_disciplines.Contains(discipline);

    public float StudyHoursIn(string discipline)=>_studyHours.TryGetValue(discipline,out var hours)?hours:0f;

    public void Save(IEntitySaver saver) {
      if(!IsSpecialist&&_studyHours.Count==0)return;
      var data=saver.GetComponent(Key);
      data.Set(DisciplinesKey,_disciplines);
      var studying=_studyHours.Keys.ToList();
      data.Set(StudyDisciplinesKey,studying);
      data.Set(StudyHoursKey,studying.Select(d=>_studyHours[d]).ToList());
    }

    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return; // never studied
      if(data.Has(DisciplinesKey))_disciplines.AddRange(data.Get(DisciplinesKey));
      else if(data.Has(LegacyDisciplineKey))_disciplines.Add(data.Get(LegacyDisciplineKey));
      if(!data.Has(StudyDisciplinesKey))return; // legacy course hours do not carry over
      var studying=data.Get(StudyDisciplinesKey);
      var hours=data.Get(StudyHoursKey);
      if(studying.Count!=hours.Count)throw new InvalidOperationException($"{Name}: saved study hours do not match their disciplines");
      for(var i=0;i<studying.Count;i++)_studyHours.Add(studying[i],hours[i]);
    }

    public void InitializeEntity() {
      foreach(var discipline in _disciplines.Concat(_studyHours.Keys))
        _settings.Discipline(discipline); // unknown saved discipline fails explicitly
      if(_disciplines.Count!=_disciplines.Distinct().Count())throw new InvalidOperationException($"{Name}: a saved discipline is listed twice");
      if(IsSpecialist&&_character.Alive)_roster.Add(this);
    }

    public void DeleteEntity() {_roster.Remove(this);}

    // Returns true when the hours complete the discipline (the beaver graduates).
    public bool AddStudyHours(string discipline, float hours, float required) {
      if(Has(discipline))throw new InvalidOperationException($"{FirstName} is already a {discipline} specialist");
      var total=StudyHoursIn(discipline)+hours;
      if(total<required) {_studyHours[discipline]=total;return false;}
      Graduate(discipline);
      return true;
    }

    public void Graduate(string discipline) {
      if(Has(discipline))throw new InvalidOperationException($"{FirstName} is already a {discipline} specialist");
      var spec=_settings.Discipline(discipline);
      _disciplines.Add(discipline);
      _studyHours.Remove(discipline);
      _roster.Add(this);
      KeepStudyNeedsFull();
      _notifications.Post(_loc.T("DeepFrontier.Workforce.Notification.Graduated",FirstName,_loc.T(spec.DisplayNameLocKey)),this);
    }

    // A held discipline's study need stays full: the beaver never visits a
    // school teaching it, and the need's wellbeing counts as long as it lives.
    public void KeepStudyNeedsFull() {
      foreach(var discipline in _disciplines) {
        var need=StudyNeedId(discipline);
        if(!NeedManager.HasNeed(need))continue; // a faction without the study needs
        var missing=NeedManager.NeedPointsToMax(need);
        if(missing>0f)NeedManager.ApplyEffect(new InstantEffect(need,missing,1));
      }
    }

    private void OnDied(object sender, EventArgs e) {
      if(!IsSpecialist)return;
      _roster.Remove(this);
      foreach(var discipline in _disciplines) {
        var spec=_settings.Discipline(discipline);
        var remaining=_roster.Count(discipline);
        _notifications.Post(_loc.T("DeepFrontier.Workforce.Notification.SkillLost",FirstName,_loc.T(spec.DisplayNameLocKey),
          $"{_loc.T(spec.PluralDisplayNameLocKey)}: {remaining}"),this);
      }
    }
  }

  // Keeps every specialist's held-discipline study needs full each tick
  // (native needs decay; schools must never draw a beaver that already knows).
  internal sealed class SpecialistStudyNeeds : ITickableSingleton {
    private readonly SpecialistRoster _roster;
    public SpecialistStudyNeeds(SpecialistRoster roster) {_roster=roster;}
    public void Tick() {
      foreach(var trait in _roster.All)if(trait.Alive)trait.KeepStudyNeedsFull();
    }
  }
}
