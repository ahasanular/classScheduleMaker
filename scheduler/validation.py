from typing import List
from scheduler.models import Assignment


class ConstraintCheckerEngine:
    def __init__(self, constraints):
        self.config = {cs.key : cs for cs in constraints}

    def is_valid_assignment(self, assignment: Assignment, current_assignments: List[Assignment]) -> bool:
        course = assignment.course
        teacher = assignment.teacher
        section = assignment.section
        shift = assignment.shift
        slot_group = assignment.slot_group
        room = assignment.room

        # No overlapping
        for a in current_assignments:
            same_time = a.slot_group[0].day == slot_group[0].day and any(
                num in [s.slot_number for s in a.slot_group] for num in [s.slot_number for s in slot_group]
            )

            param_match = (a.teacher == teacher or a.room == room or a.section == section)

            if same_time and param_match:
                return False

        teacher = self.validate_teacher(assignment, current_assignments)
        slot = self.validate_slot(assignment, current_assignments)
        room = self.validate_room(assignment, current_assignments)

        return teacher and slot and room

    def validate_teacher(self, assignment: Assignment, current_assignments: List[Assignment]) -> bool:
        course = assignment.course
        teacher = assignment.teacher
        section = assignment.section
        shift = assignment.shift

        # 1. One teacher per course [ Already checked in teacher ]
        if self.config.get('one_teacher_per_course') and any(
                a.course == course and a.section == section and shift == a.shift and a.teacher != teacher for a in current_assignments
        ):
            return False

        # 2. cross department teacher class
        if self.config.get('cross_department_teacher') and course.department != teacher.department:
            return False

        # 6. Teacher class count does not exceed weekly max
        if self.config.get('enforce_teacher_max_weekly_load'):
            if teacher.load + 1 > teacher.max_classes_per_week:
                return False

        return True


    def validate_slot(self, assignment: Assignment, current_assignments: List[Assignment]) -> bool:
        course = assignment.course
        teacher = assignment.teacher
        section = assignment.section
        shift = assignment.shift
        slot_group = assignment.slot_group
        room = assignment.room

        if course.duration_per_session != len(slot_group):
            return False

        # 1 Ensure constructiveness of multiple duration classes
        if course.duration_per_session > 1:
            for j in range(1, len(slot_group)):
                prev_slot = slot_group[j - 1]
                current_slot = slot_group[j]

                # Check if slot numbers are consecutive
                if current_slot.slot_number != prev_slot.slot_number + 1:
                    return False

                # Check if the end time of the previous slot matches the start time of the current slot
                if prev_slot.end_time != current_slot.start_time:
                    if not assignment.shift.name == 'Morning':
                        return False

        # No course repeats on same day
        if not self.config.get('no_course_repeat_same_day'):
            for a in current_assignments:
                if a.course.id == course.id and a.section.id == section.id and any(
                        day in [s.day for s in a.slot_group] for day in [s.day for s in slot_group]
                ):
                    return False
        return True


    def validate_room(self, assignment: Assignment, current_assignments: List[Assignment]) -> bool:
        course = assignment.course
        teacher = assignment.teacher
        section = assignment.section
        shift = assignment.shift
        slot_group = assignment.slot_group
        room = assignment.room

        if course.is_lab != room.is_lab:
            return False
        return True