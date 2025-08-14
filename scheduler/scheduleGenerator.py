from scheduler.tracker import Tracker
from scheduler.validation import ConstraintCheckerEngine
from scheduler.score import ScoreEngine
from collections import defaultdict
from typing import List, Dict
from scheduler.models import Assignment, Course, Teacher, TimeSlot, Room, Shift, Section, Constrains
from university.models import Assignment as DjangoAssignment, Teacher as DTeacher, Room as DRoom, Course as DCourse, Shift as DShift, Section as DSection
import random


class ScheduleGenerator:
    def __init__(self, constrains, courses, teachers, rooms, time_slots, shift, sections):
        self.soft_constrains = [cs for cs in constrains if cs.type == 'Soft']
        self.hard_constrains = [cs for cs in constrains if cs.type == 'Hard']
        self.time_slots = time_slots
        self.teachers = teachers
        self.rooms = rooms
        self.shift = shift
        self.sections = sections

        random.shuffle(courses)
        courses.sort(key=self.get_course_priority, reverse=True)

        self.courses = courses

        self.tracker = Tracker()

        self.constraints = ConstraintCheckerEngine(self.hard_constrains)
        self.scorer = ScoreEngine(self.soft_constrains, time_slots, self.tracker)

        self.assignments : List[Assignment] = []

    def get_filtered_timeslots(self, time_slots: List[TimeSlot], section: Section, teacher: Teacher) -> defaultdict[str, List[TimeSlot]]:
        all_slots_by_day = defaultdict(list)
        for slot in time_slots:
            # if slot.id not in self.tracker.slot_used_by_section.get(section.id, set()) and slot.id not in self.tracker.slot_used_by_teacher.get(teacher.id, set()):
            all_slots_by_day[slot.day].append(slot)

        for slots in all_slots_by_day.values():
            slots.sort(key=lambda s: s.slot_number)
        return all_slots_by_day

    @staticmethod
    def get_course_priority(course: Course):
        base = 0
        # if course.is_lab:
        #     base += 5
        base += course.duration_per_session
        # base += course.sessions_per_week
        base += 5 - min(5, len(course.preferred_teachers))
        return base

    def generate(self):
        unassigned_courses = defaultdict(list)
        for idx, course in enumerate(self.courses):
            for section in self.get_sections_for_course(course):
                if not self.try_assign_course(course, section):
                    unassigned_courses[section].append(course)

        backtracking_failed_courses = self.try_backtracking(unassigned_courses)

        return self.assignments, backtracking_failed_courses

    def try_backtracking(self, unassigned_courses: Dict[Section, List[Course]]) -> Dict[Section, List[Course]]:
        """
        Its try to backtrack to the assigned schedule for that section and find the blocking courses and try to
        Re-arrange the course to see if that can assign the unassigned course.
        params:
        unassigned_courses: Dict[Section, List[Course]] Initially Failed courses by section.
        returns: Dict[Section, List[Course]] Failed courses by section even after backtracking.
        """

        failed_courses = dict()
        for section, courses in unassigned_courses.items():
            for course in courses:
                pass
                # if not self.solve_issue(course, section):
                #     failed_courses[section].append(course)
        return failed_courses

    def try_assign_course(self, course: Course, section: Section):
        schedule = []
        for class_count in range(course.sessions_per_week):
            combinations = []
            teachers = self.get_available_teachers(course, section)
            for teacher in teachers:
                slot_groups = self.get_available_slots(course, teacher, section)

                for slot_group in slot_groups:
                    rooms = self.get_available_rooms(course, slot_group, teacher)

                    for room in rooms:
                        combinations.append(self.make_combination(course, teacher, slot_group, room, self.shift, section))

            valid_combinations = []
            for combination in combinations:
                if self.constraints.is_valid_assignment(combination, self.assignments):
                    combination.score = self.scorer.score_assignment(combination, self.assignments)
                    valid_combinations.append(combination)

            if valid_combinations:
                schedule.append(self.make_assignment(valid_combinations)) # finalize the top scored one

        if len(schedule) != course.sessions_per_week:
            print(f'Invalid combination: {course.code} - {course.name}')
            # raise Exception(f'Invalid combination: {course.code} - {course.name}')
            return False
        return True

    def get_sections_for_course(self, course: Course):
        return [
            sec for sec in self.sections
            if course.semester == sec.semester and
               sec.shift == self.shift
        ]

    def get_available_teachers(self, course: Course, section: Section):
        preferred = course.preferred_teachers
        ts = [t for t in self.teachers if t.department == course.department]
        random.shuffle(ts)
        random.shuffle(preferred)
        found_teachers = [t for t in ts if t.id in preferred] + [item for item in ts if item not in preferred]

        # if a teacher was already taken this course, then check no other teacher
        filtered_teachers = [
            teacher for teacher in found_teachers
            if teacher.id in self.tracker.teacher_occupied_courses[course.id]
               and section.id in self.tracker.teacher_occupied_courses[course.id][teacher.id]
        ]
        if filtered_teachers:
            found_teachers = filtered_teachers

        found_teachers.sort(key=lambda t: t.load)

        # for tc in found_teachers:
        #     if tc.preferred_time_slots and any([pts.id not in self.tracker.slot_used_by_teacher[tc.id] for pts in tc.preferred_time_slots]):
        #         found_teachers.sort(key=lambda t: len(t.preferred_time_slots) - len(self.tracker.slot_used_by_teacher[t.id]), reverse=True)
        #         break

        return found_teachers

    def get_available_slots(self, course: Course, teacher: Teacher, section: Section):
        all_slots_by_day = self.get_filtered_timeslots([ts for ts in self.time_slots if ts.id not in self.tracker.slot_used_by_section[section.id] and ts.id not in self.tracker.slot_used_by_teacher[teacher.id]], section, teacher)

        to_del = []
        for day, day_sl in all_slots_by_day.items():
            # check course for the same day
            if day in self.tracker.day_used_by_course_section[course.id] and day in self.tracker.day_used_by_course_section[course.id][section.id]:
                to_del.append(day)
            # day_slots_map[day].extend(day_sl)

        for day in to_del:
            all_slots_by_day.pop(day)

        day_slots_map = all_slots_by_day

        # Filter by consecutiveness
        days = list(day_slots_map.keys())

        random.shuffle(days)

        found_slots = []
        for day in days:
            for i, slot in enumerate(day_slots_map[day]):
                if i + course.duration_per_session > len(day_slots_map[day]):
                    continue
                slot_group = day_slots_map[day][i:i + course.duration_per_session]
                for s in slot_group:
                    if s.id in self.tracker.slot_used_by_teacher[teacher.id]:
                        continue
                if all([s.id not in self.tracker.slot_used_by_teacher[teacher.id] for s in slot_group]):
                    found_slots.append(slot_group)

        return found_slots

    def get_available_rooms(self, course: Course, slot_group: List[TimeSlot], teacher: Teacher):
        random.shuffle(self.rooms)
        rooms = [r for r in self.rooms if r.is_lab == course.is_lab]
        if course.is_lab:
            rooms = [r for r in rooms if r.department == course.department]

        found_rooms = []

        for room in rooms:
            if (
                room.id in self.tracker.used_slots_by_room and
                any(slot.id in self.tracker.used_slots_by_room[room.id] for slot in slot_group)
            ):
                continue
            found_rooms.append(room)

        # found_rooms = [
        #     room for room in rooms
        #     if room.id in self.tracker.used_slots_by_room and
        #        not any(slot.id in self.tracker.used_slots_by_room[room.id] for slot in slot_group)
        # ]

        # # Filter by used slots for each room
        # found_rooms = []
        # for room in rooms:
        #     if (
        #         room.id in self.tracker.used_slots_by_room and
        #         all(s.id in self.tracker.used_slots_by_room[room.id] for s in slot_group)
        #     ):
        #         continue
        #     found_rooms.append(room)
        return found_rooms

    @staticmethod
    def make_combination(course, teacher, slot_group, room, shift, section):
        return Assignment(course=course, teacher=teacher, slot_group=slot_group, room=room, shift=shift, section=section)

    def make_assignment(self, combinations: List[Assignment]):

        top_score_assignment = max(combinations, key=lambda x: x.score)

        self.assignments.append(top_score_assignment)

        # update the tracker default dict as well.
        self.tracker.add_assignment(top_score_assignment)

        # TESTING>>>>
        # self.save_routine([top_score_assignment])

        return top_score_assignment

    def save_routine(self, assignments: List[Assignment]):
        """
        Only for testing purpose, Don't call in main or development branch. Only call locally
        """
        for assignment in assignments:
            course = DCourse.objects.get(id=assignment.course.id)
            teacher = DTeacher.objects.get(id=assignment.teacher.id)
            room = DRoom.objects.get(id=assignment.room.id)
            shift = DShift.objects.get(id=assignment.shift.id)
            section = DSection.objects.get(id=assignment.section.id)
            ass = DjangoAssignment.objects.create(
                course=course,
                teacher=teacher,
                room=room,
                score=assignment.score,
                shift=shift,
                section=section,
            )
            ass.time_slot.set([s.id for s in assignment.slot_group])

            course.is_assigned = True
            course.save()

            teacher.is_assigned = True
            teacher.save()