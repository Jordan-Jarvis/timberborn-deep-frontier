using System;
using Timberborn.BaseComponentSystem;
using Timberborn.Characters;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.NotificationSystem;
using Timberborn.Persistence;
using Timberborn.WorkSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Persistent specialist qualification of one adult beaver (decorates the
  // native AdultSpec). The skill exists only on this beaver: when it dies
  // (old age, accident, radiation...) the skill is gone and its specialist
  // workplace loses a crew member until someone else is trained.
  internal sealed class SpecialistTrait : BaseComponent, IAwakableComponent, IInitializableEntity,
      IPersistentEntity, IDeletableEntity {
    private static readonly ComponentKey Key=new("DeepFrontier.Specialist");
    private static readonly PropertyKey<string> DisciplineKey=new("Discipline");
    private static readonly PropertyKey<float> TrainingHoursKey=new("TrainingHours");

    private readonly WorkforceSettings _settings;
    private readonly SpecialistRoster _roster;
    private readonly NotificationBus _notifications;
    private readonly ILoc _loc;
    private Character _character;

    // null: not a specialist.
    public string Discipline { get; private set; }
    public bool IsSpecialist=>Discipline!=null;
    // Hours worked in a running training course; picks who graduates next.
    public float TrainingHours { get; private set; }
    public Worker Worker { get; private set; }
    public Citizen Citizen { get; private set; }
    public bool Alive=>_character.Alive;
    public string FirstName=>_character.FirstName;

    public SpecialistTrait(WorkforceSettings settings, SpecialistRoster roster, NotificationBus notifications, ILoc loc) {
      _settings=settings;_roster=roster;_notifications=notifications;_loc=loc;
    }

    public void Awake() {
      _character=GetComponent<Character>();
      Worker=GetComponent<Worker>();
      Citizen=GetComponent<Citizen>();
      if(!Worker||!Citizen)throw new InvalidOperationException($"{Name}: a specialist must be a working citizen");
      _character.Died+=OnDied;
    }

    public void Save(IEntitySaver saver) {
      if(!IsSpecialist&&TrainingHours==0f)return;
      var data=saver.GetComponent(Key);
      if(IsSpecialist)data.Set(DisciplineKey,Discipline);
      data.Set(TrainingHoursKey,TrainingHours);
    }

    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return; // never trained
      if(data.Has(DisciplineKey))Discipline=data.Get(DisciplineKey);
      TrainingHours=data.Get(TrainingHoursKey);
    }

    public void InitializeEntity() {
      if(!IsSpecialist)return;
      _settings.Discipline(Discipline); // unknown saved discipline fails explicitly
      if(_character.Alive)_roster.Add(this);
    }

    public void DeleteEntity() {_roster.Remove(this);}

    public void AddTrainingHours(float hours) {
      if(IsSpecialist)throw new InvalidOperationException($"{FirstName} is already a specialist");
      TrainingHours+=hours;
    }

    public void Graduate(string discipline) {
      if(IsSpecialist)throw new InvalidOperationException($"{FirstName} is already a {Discipline} specialist");
      var spec=_settings.Discipline(discipline);
      Discipline=discipline;
      TrainingHours=0f;
      _roster.Add(this);
      _notifications.Post(_loc.T("DeepFrontier.Workforce.Notification.Graduated",FirstName,_loc.T(spec.DisplayNameLocKey)),this);
    }

    private void OnDied(object sender, EventArgs e) {
      if(!IsSpecialist)return;
      _roster.Remove(this);
      var spec=_settings.Discipline(Discipline);
      var remaining=_roster.Count(Discipline);
      _notifications.Post(_loc.T("DeepFrontier.Workforce.Notification.SkillLost",FirstName,_loc.T(spec.DisplayNameLocKey),
        $"{_loc.T(spec.PluralDisplayNameLocKey)}: {remaining}"),this);
    }
  }
}
