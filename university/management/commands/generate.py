import time
from django.core.management.base import BaseCommand
from university.models import Course, Teacher, Room, TimeSlot, Constrain  # Django models
from university.models import Assignment as DjangoAssignment
from scheduler.scheduleGenerator import ScheduleGenerator
from scheduler.models import Course as DCourse, Teacher as DTeacher, Room as DRoom, TimeSlot as DTimeSlot, Constrains as DConstrains, Assignment as DAssignment

from typing import List, Dict


class Command(BaseCommand):
    help = 'Generates the optimal class schedule and stores it in the database'

    @staticmethod
    def clear_previous_assignments():
        """Reset assignment and assignment-related flags in all relevant models."""
        DjangoAssignment.objects.all().delete()
        Course.objects.all().update(is_assigned=False)
        Teacher.objects.all().update(is_assigned=False)

    def handle(self, *args, **options):
        self.clear_previous_assignments()

        config, courses, teachers, rooms, time_slots = self.initialize_data()

        scheduler = ScheduleGenerator(config, courses, teachers, rooms, time_slots)
        assignments, unassigned = scheduler.generate()

        self.save_routine(assignments)

    def save_routine(self, assignments: List[DAssignment]):
        for assignment in assignments:
            course = Course.objects.get(id=assignment.course.id)
            teacher = Teacher.objects.get(id=assignment.teacher.id)
            room = Room.objects.get(id=assignment.room.id)
            ass = DjangoAssignment.objects.create(
                course=course,
                teacher=teacher,
                room=room,
                score=assignment.score,
            )
            ass.time_slot.set([s.id for s in assignment.slot_group])

            course.is_assigned = True
            course.save()

            teacher.is_assigned = True
            teacher.save()

        self.stdout.write(self.style.SUCCESS('Schedule generated and saved successfully.'))

    @staticmethod
    def initialize_data(*args, **kwargs):
        # convert config models to constrains
        config: Dict[str, DConstrains] = {
            cs.key: DConstrains(
                id=cs.id,
                type=cs.type.name,
                condition=cs.condition,
                severity=cs.severity,
                score_weight=cs.score_weight,
            )
            for cs in Constrain.objects.filter(is_active=True)
        }

        # Convert Django TimeSlot to dataclass
        time_slots: List[DTimeSlot] = [
            DTimeSlot(id=ts.id, day=ts.day, slot_number=ts.slot_number, start_time=ts.start_time, end_time=ts.end_time)
            for ts in TimeSlot.objects.filter(is_active=True).order_by('id')
        ]

        # Convert Django Room to dataclass
        rooms: List[DRoom] = [
            DRoom(
                id=r.id,
                name=r.name,
                department=r.department,
                is_lab=r.is_lab
            ) for r in Room.objects.filter(is_active=True).select_related('department').all()
        ]

        # Convert Django Teacher to dataclass
        teachers: List[DTeacher] = []
        for t in Teacher.objects.filter(is_active=True).prefetch_related('preferred_courses', 'preferred_time_slots'):
            teachers.append(DTeacher(
                id=t.id,
                name=t.name,
                initial=t.initial,
                department=t.department,
                max_classes_per_week=t.max_classes_per_week,
                preferred_courses=[c.id for c in t.preferred_courses.filter(is_active=True)],
                preferred_time_slots=[ts for ts in t.preferred_time_slots.all()],
                minimum_classes_per_day=t.minimum_classes_per_day
            ))

        # Convert Django Course to dataclass
        courses: List[DCourse] = [
            DCourse(
                id=c.id,
                code=c.code,
                name=c.name,
                department=c.department,
                semester=c.semester,
                credit=c.credit,
                sessions_per_week=c.sessions_per_week,
                duration_per_session=c.duration_per_session,
                is_lab=c.is_lab,
                preferred_teachers=[
                    DTeacher(
                        id=t.id,
                        name=t.name,
                        initial=t.initial,
                        department=t.department,
                        max_classes_per_week=t.max_classes_per_week,
                        preferred_courses=[c.id for c in t.preferred_courses.all()],
                        preferred_time_slots=[ts for ts in t.preferred_time_slots.all()],
                        minimum_classes_per_day=t.minimum_classes_per_day
                    )
                    for t in c.preferred_teachers.filter(is_active=True)
                ],
            ) for c in Course.objects.filter(is_active=True).select_related('department').all()
        ]

        return config, courses, teachers, rooms, time_slots
