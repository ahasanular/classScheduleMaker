from collections import defaultdict
from scheduler.models import Assignment

class Tracker:
    def __init__(self):
        # Tracker
        self.slot_used_by_section = defaultdict(set)
        self.slot_used_by_teacher = defaultdict(set)
        self.used_slots_by_room = defaultdict(set)
        self.teacher_occupied_courses = defaultdict(lambda : defaultdict(set))
        self.day_used_by_course_section = defaultdict(lambda : defaultdict(set))

    def add_assignment(self, assignment: Assignment):
        course = assignment.course
        teacher = assignment.teacher
        slot_group = assignment.slot_group
        room = assignment.room
        day = slot_group[0].day

        for slot in slot_group:
            self.slot_used_by_section[assignment.section.id].add(slot.id)

            self.slot_used_by_teacher[teacher.id].add(slot.id)
            self.used_slots_by_room[room.id].add(slot.id)
            self.teacher_occupied_courses[course.id][teacher.id].add(assignment.section.id)
            self.day_used_by_course_section[course.id][assignment.section.id].add(day)
        assignment.teacher.load += 1

    def remove_assignment(self, assignment: Assignment):
        course = assignment.course
        teacher = assignment.teacher
        slot_group = assignment.slot_group
        room = assignment.room
        day = slot_group[0].day

        for slot in slot_group:
            self.slot_used_by_section[assignment.section.id].remove(slot.id)

            self.slot_used_by_teacher[teacher.id].remove(slot.id)
            self.used_slots_by_room[room.id].remove(slot.id)
            self.teacher_occupied_courses[course.id][teacher.id].remove(assignment.section.id)
            self.day_used_by_course_section[course.id][assignment.section.id].remove(day)
        assignment.teacher.load -= 1