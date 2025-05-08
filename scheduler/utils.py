from collections import defaultdict, Counter
from typing import List
from .models import Assignment
import numpy as np


class ConstraintCheckerEngine:
    def __init__(self, config):
        self.config = config

    def is_valid_assignment(self, assignment: Assignment, current_assignments: List[Assignment]) -> bool:
        course = assignment.course
        teacher = assignment.teacher
        slot_group = assignment.slot_group
        room = assignment.room
        # day_assignments = [a for a in current_assignments if a.slot.day == slot.day]

        # 1. One teacher per course [ Already checked in teacher ]
        if self.config.get('one_teacher_per_course') and any(a.course == course and a.teacher != teacher for a in current_assignments):
            return False

        # 2. cross department teacher class
        if self.config.get('cross_department_teacher') and course.department != teacher.department:
            return False

        # 3 No overlapping
        for a in current_assignments:
            same_time = a.slot_group[0].day == slot_group[0].day and any(num in [s.slot_number for s in a.slot_group] for num in [s.slot_number for s in slot_group])

            param_match = (a.teacher == teacher or a.room == room or a.course.semester == course.semester)

            if same_time and param_match:
                return False

        # 4 Ensure constructiveness of multiple duration classes
        if course.duration_per_session > 1:
            for j in range(1, len(slot_group)):
                prev_slot = slot_group[j - 1]
                current_slot = slot_group[j]

                # Check if slot numbers are consecutive
                if current_slot.slot_number != prev_slot.slot_number + 1:
                    return False

                # Check if the end time of the previous slot matches the start time of the current slot
                if prev_slot.end_time != current_slot.start_time:
                    return False

        # 5 No course repeats on same day
        if not self.config.get('no_course_repeat_same_day'):
            for a in current_assignments:
                if a.course == course and any(day in [s.day for s in a.slot_group] for day in [s.day for s in slot_group]):
                    return False

        # 6. Teacher class count does not exceed weekly max
        if self.config.get('enforce_teacher_max_weekly_load'):
            if teacher.load + 1 > teacher.max_classes_per_week:
                return False
        return True


class ScoreEngine:
    def __init__(self, config, slots, tracker):
        self.constraints = config
        self.time_slots = slots
        self.tracker = tracker

    def score_assignment(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        scores = {}
        for key, value in self.constraints.items():
            score_func = getattr(self, f'_score_{key}', None)
            if not score_func:
                continue

            scores[key] = score_func(assignment, current_assignments)

        total_score = sum(self.constraints[key].score_weight * scores[key] for key in scores)
        assignment.score = total_score
        return total_score

    def _score_respect_teacher_preferred_slots(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        # 1. Preferred time slot
        if assignment.teacher.preferred_time_slots:
            matched = 1
            for slot in assignment.slot_group:
                if slot.id in [s.id for s in assignment.teacher.preferred_time_slots]:
                    matched += 1
            return matched / len(assignment.slot_group) if assignment.slot_group else 0.0
        else:
            return 0.0

    def _score_respect_teacher_preferred_courses(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        return 1.0 if assignment.course.id in assignment.teacher.preferred_courses else 0.0

    def _score_prioritize_teachers_with_fewer_assignments(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        teacher = assignment.teacher
        if teacher.max_classes_per_week == 0:
            return 0.0
        return 1.0 - min(teacher.load / teacher.max_classes_per_week, 1.0)

    def _score_prioritize_rooms_with_fewer_assignments(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        room = assignment.room
        if not len(self.tracker.used_slots_by_room[room.id]):
            return 1.0
        return 1.0 - min(len(self.tracker.used_slots_by_room[room.id]) / len(self.time_slots), 1.0)

    def _score_minimize_teacher_slot_gap(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        teacher_id = assignment.teacher.id
        slots = [ts.slot_number for a in current_assignments if a.teacher.id == teacher_id for ts in a.slot_group]
        slots += [ts.slot_number for ts in assignment.slot_group]
        grouped_by_day = defaultdict(list)

        for a in current_assignments:
            if a.teacher.id == teacher_id:
                for ts in a.slot_group:
                    grouped_by_day[ts.day].append(ts.slot_number)
        for ts in assignment.slot_group:
            grouped_by_day[ts.day].append(ts.slot_number)

        total_gap = 0
        count = 0
        for day, slots in grouped_by_day.items():
            slots = sorted(slots)
            if len(slots) > 1:
                gaps = [slots[i + 1] - slots[i] - 1 for i in range(len(slots) - 1)]
                total_gap += sum(gaps)
                count += len(gaps)

        if count == 0:
            return 1.0  # no gaps to penalize
        avg_gap = total_gap / count
        max_possible_gap = 5  # assume worst reasonable gap (e.g., 5-slot gap)
        return max(0.0, 1.0 - avg_gap / max_possible_gap)

    def _score_minimize_semester_slot_gap(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        semester = assignment.course.semester
        department = assignment.course.department
        grouped_by_day = defaultdict(list)

        for a in current_assignments:
            if a.course.semester == semester and a.course.department == department:
                for ts in a.slot_group:
                    grouped_by_day[ts.day].append(ts.slot_number)
        for ts in assignment.slot_group:
            grouped_by_day[ts.day].append(ts.slot_number)

        total_gap = 0
        count = 0
        for day, slots in grouped_by_day.items():
            slots = sorted(slots)
            if len(slots) > 1:
                gaps = [slots[i + 1] - slots[i] - 1 for i in range(len(slots) - 1)]
                total_gap += sum(gaps)
                count += len(gaps)

        if count == 0:
            return 1.0  # no gaps to penalize
        avg_gap = total_gap / count
        max_possible_gap = 5  # same assumption
        return max(0.0, 1.0 - avg_gap / max_possible_gap)

    def _score_day_balancing_slots_allocation(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        slot_count_by_day = defaultdict(int)
        total_available = 0
        for slot in self.time_slots:
            if slot.id not in self.tracker.slot_used_by_semester[assignment.course.semester]:
                slot_count_by_day[slot.day] += 1
                total_available += 1

        dept_id = assignment.course.department.id
        semester = assignment.course.semester

        # Count actual slots per day
        day_count = Counter()
        for a in current_assignments:
            if a.course.department.id == dept_id and a.course.semester == semester:
                for ts in a.slot_group:
                    day_count[ts.day] += 1
        # Add new assignment
        for ts in assignment.slot_group:
            day_count[ts.day] += 1

        # Calculate ideal ratio
        ideal = {day: slot_count_by_day[day] / total_available for day in slot_count_by_day}
        total_assigned = sum(day_count.values())
        if total_assigned == 0:
            return 1.0
        actual = {day: day_count[day] / total_assigned for day in slot_count_by_day}

        # Score similarity using squared error
        error = sum((actual.get(day, 0.0) - ideal[day]) ** 2 for day in ideal)
        return 1.0 - min(error * 2, 1.0)  # Normalize into [0, 1] range


    def _score_prioritize_early_slots(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        day_slots_dict = defaultdict(list)
        for slot in self.time_slots:
            day_slots_dict[slot.day].append(slot.slot_number)

        # Optional: convert defaultdict to regular dict
        for day, slots in day_slots_dict.items():
            slots.sort(key=lambda slot: slot)

        score = 0
        for slot in assignment.slot_group:
            day = slot.day
            number = slot.slot_number
            if day in day_slots_dict and number in day_slots_dict[day]:
                idx = day_slots_dict[day].index(number)
                score += max(0, 1.0 - 0.1 * idx)
        return score

        avg_slot_number = np.mean([ts.slot_number for ts in assignment.slot_group])
        max_slot_number = max(ts.slot_number for ts in assignment.slot_group)
        if max_slot_number == 0:
            return 0.0
        # Early slots get lower score (better), late slots higher score (worse)
        return avg_slot_number / max_slot_number


class Tracker:
    def __init__(self):
        # Tracker
        self.slot_used_by_semester = defaultdict(set)
        self.slot_used_by_course = defaultdict(set)
        self.slot_used_by_teacher = defaultdict(set)
        self.used_slots_by_room = defaultdict(set)
        self.teacher_occupied_courses = defaultdict(set)
        self.day_used_by_course = defaultdict(set)
        self.used_days_by_semester = defaultdict(lambda: defaultdict(int))

    def add_assignment(self, assignment: Assignment):
        course = assignment.course
        teacher = assignment.teacher
        slot_group = assignment.slot_group
        room = assignment.room
        day = slot_group[0].day

        for slot in slot_group:
            self.slot_used_by_semester[course.semester].add(slot.id)
            self.slot_used_by_course[course.id].add(slot.day)
            self.slot_used_by_teacher[teacher.id].add(slot.id)
            self.used_slots_by_room[room.id].add(slot.id)
            self.teacher_occupied_courses[course.id].add(teacher.id)
            self.day_used_by_course[course.id].add(day)
            self.used_days_by_semester[course.semester][slot.day] += 1
        assignment.teacher.load += 1

    def remove_assignment(self, assignment: Assignment):
        course = assignment.course
        teacher = assignment.teacher
        slot_group = assignment.slot_group
        room = assignment.room
        day = slot_group[0].day

        for slot in slot_group:
            self.slot_used_by_semester[course.semester].remove(slot.id)
            self.slot_used_by_course[course.id].remove(slot.day)
            self.slot_used_by_teacher[teacher.id].remove(slot.id)
            self.used_slots_by_room[room.id].remove(slot.id)
            self.teacher_occupied_courses[course.id].remove(teacher.id)
            self.day_used_by_course[course.id].remove(day)
            self.used_days_by_semester[course.semester][slot.day] -= 1
        assignment.teacher.load -= 1

