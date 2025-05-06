from django.db import models
from config.mixin import ModelMixin

DAYS = [
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
]


class Department(ModelMixin):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Room(ModelMixin):
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=40)  # optional
    is_lab = models.BooleanField(default=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class TimeSlot(ModelMixin):
    day = models.CharField(max_length=10, choices=DAYS)
    slot_number = models.PositiveIntegerField()  # like 1 to N
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ('day', 'slot_number')
        ordering = ['day', 'slot_number']

    def __str__(self):
        return f"{self.day} - Slot {self.slot_number}"


class Teacher(ModelMixin):
    name = models.CharField(max_length=100)
    initial = models.CharField(max_length=10, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    max_classes_per_week = models.PositiveIntegerField(default=10)
    preferred_time_slots = models.ManyToManyField(TimeSlot, blank=True, related_name='preferred_teachers')
    preferred_courses = models.ManyToManyField('Course', blank=True, related_name='preferred_teachers')
    is_assigned = models.BooleanField(default=False)
    minimum_classes_per_day = models.PositiveIntegerField(default=2)

    def __str__(self):
        return self.name


class Course(ModelMixin):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    credit = models.FloatField(default=3.0)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField()
    sessions_per_week = models.PositiveIntegerField(default=2)
    duration_per_session = models.PositiveIntegerField(default=1)  # in slots
    is_lab = models.BooleanField(default=False)
    is_assigned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (Sem {self.semester})"


class Assignment(ModelMixin):
    """
    This model holds the final generated routine assignments.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    time_slot = models.ManyToManyField(TimeSlot, related_name='assignments')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    score = models.FloatField(default=0)

    def __str__(self):
        return f"{self.course.name} at {[slot for slot in self.time_slot.all()]} by {self.teacher.name}"

class ConstrainType(ModelMixin):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
    class Meta:
        unique_together = ('name',)


class Constrain(models.Model):
    CONSTRAIN_SEVERITY_CHOICES = (
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low')
    )
    SEVERITY_SCORE = {
        'High': 3.0,
        'Medium': 1.5,
        'Low': 1.0,
    }
    type = models.ForeignKey(ConstrainType, on_delete=models.CASCADE)
    condition = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    severity = models.CharField(default='High', max_length=8, choices=CONSTRAIN_SEVERITY_CHOICES)
    score_weight = models.FloatField(default=100.0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.type.name

    def save(self, *args, **kwargs):
        self.score = self.SEVERITY_SCORE[self.severity]
        super().save(*args, **kwargs)

    @property
    def key(self):
        return '_'.join(self.condition.lower().split())
