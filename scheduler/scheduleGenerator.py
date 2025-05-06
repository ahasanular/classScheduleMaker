from .utils import ConstraintCheckerEngine, Tracker, ScoreEngine
from collections import defaultdict
from typing import List
from .models import Assignment, Course, Teacher, TimeSlot, Room
from university.models import Assignment as DjAssignment, Teacher as DTeacher, Room as DRoom, Course as DCourse
import random


class ScheduleGenerator:
    def __init__(self, config, courses, teachers, rooms, time_slots):
        self.config = config
        self.time_slots = time_slots
        self.teachers = teachers
        self.rooms = rooms
        random.shuffle(courses)
        courses.sort(key=self.get_course_priority, reverse=True)
        self.courses = courses

        self.tracker = Tracker()

        self.constraints = ConstraintCheckerEngine(config)
        self.scorer = ScoreEngine(config, time_slots, self.tracker)

        self.assignments : List[Assignment] = []

    def get_day_slots(self, time_slots: List[TimeSlot]):
        all_slots_by_day = defaultdict(list)
        for slot in time_slots:
            all_slots_by_day[slot.day].append(slot)

        for slots in all_slots_by_day.values():
            slots.sort(key=lambda s: s.slot_number)
        return all_slots_by_day

    @staticmethod
    def get_course_priority(course: Course):
        base = 0
        if course.is_lab:
            base += 5
        base += course.duration_per_session
        base += course.sessions_per_week
        base += 5 - min(5, len(course.preferred_teachers))
        return base

    def generate(self):
        unassigned_courses = []
        for idx, course in enumerate(self.courses):
            if idx == 8:
                pass
            if not self.try_assign_course(course):
                unassigned_courses.append(course)
        return self.assignments, unassigned_courses

    def try_assign_course(self, course: Course):
        schedule = []
        for class_count in range(course.sessions_per_week):
            combinations = []
            teachers = self.get_available_teachers(course)
            for teacher in teachers:
                slot_groups = self.get_available_slots(course, teacher)

                for slot_group in slot_groups:
                    if isinstance(slot_group[0], list):
                        pass
                    rooms = self.get_available_rooms(course, slot_group, teacher)

                    for room in rooms:
                        combinations.append(self.make_combination(course, teacher, slot_group, room))

            valid_combinations = []
            for combination in combinations:
                if self.constraints.is_valid_assignment(combination, self.assignments):
                    combination.score = self.scorer.score_assignment(combination, self.assignments)
                    valid_combinations.append(combination)

            if valid_combinations:
                schedule.append(self.make_assignment(valid_combinations)) # finalize the top scored one

        if len(schedule) != course.sessions_per_week:
            return False
        return True

    def get_available_teachers(self, course: Course):
        # See course already taken by a teacher
        if course.id in self.tracker.teacher_occupied_courses:
            x = [teacher for teacher in self.teachers if teacher.id in self.tracker.teacher_occupied_courses[course.id]]
            return x

        preferred = course.preferred_teachers
        ts = [t for t in self.teachers if t.department == course.department]

        found_teachers = preferred + [item for item in ts if item not in preferred]
        random.shuffle(found_teachers)
        return found_teachers

    def get_available_slots(self, course: Course, teacher: Teacher):

        all_slots_by_day = self.get_day_slots(self.time_slots)

        day_slots_map = defaultdict(list)
        for day, day_sl in all_slots_by_day.items():
            # check course for same day
            if course.id in self.tracker.day_used_by_course and day in self.tracker.day_used_by_course[course.id]:
                continue
            day_slots_map[day].extend(day_sl)

        # Filter by consecutiveness
        days = list(day_slots_map.keys())

        random.shuffle(days)

        found_slots = []
        for day in days:
            for i, slot in enumerate(day_slots_map[day]):
                if i + course.duration_per_session > len(day_slots_map[day]):
                    continue

                slot_group = day_slots_map[day][i:i + course.duration_per_session]

                found_slots.append(slot_group)

        return found_slots

    def get_available_rooms(self, course: Course, slot_group: List[TimeSlot], teacher: Teacher):
        random.shuffle(self.rooms)
        rooms = [r for r in self.rooms if r.is_lab == course.is_lab]
        if course.is_lab:
            rooms = [r for r in rooms if r.department == course.department]

        # Filter by used slots for each room
        found_rooms = []
        for room in rooms:
            if (
                room.id in self.tracker.used_slots_by_room and
                all(s.id in self.tracker.used_slots_by_room[room.id] for s in slot_group)
            ):
                continue
            found_rooms.append(room)
        return found_rooms

    @staticmethod
    def make_combination(course, teacher, slot_group, room):
        return Assignment(course=course, teacher=teacher, slot_group=slot_group, room=room)

    def make_assignment(self, combinations: List[Assignment]):

        top_score_assignment = max(combinations, key=lambda x: x.score)

        self.assignments.append(top_score_assignment)

        # update the trackers default dict as well.
        self.tracker.add_assignment(top_score_assignment)

        return top_score_assignment
