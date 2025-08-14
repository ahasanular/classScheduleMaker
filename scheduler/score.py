from typing import List
from scheduler.models import Assignment
from collections import defaultdict, Counter


class ScoreEngine:
    def __init__(self, constraints, slots, tracker):
        self.constraints = {
            cs.key : cs for cs in constraints
        }
        self.time_slots = slots
        self.tracker = tracker

    def score_assignment(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        scores = {}
        if assignment.teacher.initial == 'MR' and assignment.teacher.load >= 3 and assignment.course.code == 'CSE-345':
            pass
        for key, value in self.constraints.items():
            score_func = getattr(self, f'_score_{key}', None)
            if not score_func:
                continue

            scores[key] = score_func(assignment, current_assignments)

        # total_score = sum(self.constraints[key].score_weight * scores[key] for key in scores)
        total_score = sum(scores[key] for key in scores)
        assignment.score = total_score
        return total_score

    def _score_minimize_teacher_slot_gap(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        # 1. Preferred time slot
        teacher_id = assignment.teacher.id
        grouped_by_day = defaultdict(list)

        # Collect all slot numbers by day for the teacher
        for a in current_assignments:
            if a.teacher.id == teacher_id:
                for ts in a.slot_group:
                    grouped_by_day[ts.day].append(ts.slot_number)
        for ts in assignment.slot_group:
            grouped_by_day[ts.day].append(ts.slot_number)

        total_gap = 0
        count = 0
        total_max_possible_gap = 0

        # Group all time slots by day
        all_slots_by_day = defaultdict(list)
        for ts in self.time_slots:
            all_slots_by_day[ts.day].append(ts.slot_number)

        for day, slots in grouped_by_day.items():
            slots.sort()
            if len(slots) > 1:
                # Real gaps
                gaps = [slots[i + 1] - slots[i] - 1 for i in range(len(slots) - 1)]
                total_gap += sum(gaps)
                count += len(gaps)

                # Calculate max possible gap dynamically for that day
                max_slot = max(all_slots_by_day[day])
                min_slot = min(all_slots_by_day[day])
                total_max_possible_gap += max(max_slot - min_slot - 1, 1)

        if count == 0 or total_max_possible_gap == 0:
            return 1.0  # No gaps, or can't compute

        avg_gap_ratio = total_gap / total_max_possible_gap
        return max(0.0, 1.0 - avg_gap_ratio)

    def _score_minimize_section_slot_gap(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        section = assignment.section
        department = assignment.course.department
        grouped_by_day = defaultdict(list)

        if len(current_assignments) > 3:
            pass

        # Collect all existing slot numbers for this course and semester
        for a in current_assignments:
            if a.section == section:
                for ts in a.slot_group:
                    grouped_by_day[ts.day].append(ts.slot_number)
        for ts in assignment.slot_group:
            grouped_by_day[ts.day].append(ts.slot_number)

        total_gap = 0
        count = 0
        total_max_possible_gap = 0  # Dynamic gap per day

        # Gather all possible slot numbers by day for the semester
        all_slots_by_day = defaultdict(list)
        for ts in self.time_slots:
            all_slots_by_day[ts.day].append(ts.slot_number)

        # Calculate gaps and dynamic max possible gaps for each day
        for day, slots in grouped_by_day.items():
            slots = sorted(slots)
            if len(slots) > 1:
                gaps = [slots[i + 1] - slots[i] - 1 for i in range(len(slots) - 1)]
                total_gap += sum(gaps)
                count += len(gaps)

                # Dynamic calculation of the max gap for this day
                max_slot = max(all_slots_by_day[day])
                min_slot = min(all_slots_by_day[day])
                total_max_possible_gap += max(max_slot - min_slot - 1, 1)

        if count == 0 or total_max_possible_gap == 0:
            return 1.0  # No gaps, or can't compute

        # Normalizing score
        avg_gap_ratio = total_gap / total_max_possible_gap
        return max(0.0, 1.0 - avg_gap_ratio)

    def _score_load_balancing_between_teacher(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        # Calculate the current load for each teacher
        teacher_loads = {t.id: t.load for t in current_assignments}

        # Add the current assignment to the teacher's load
        if assignment.teacher.id in teacher_loads:
            teacher_loads[assignment.teacher.id] += 1  # Adjust based on assignment

        if len(teacher_loads) == 1:
            return 1.0  # Perfect load balancing since there is only one teacher

        # Calculate the average load across all teachers
        avg_load = sum(teacher_loads.values()) / len(teacher_loads) if len(teacher_loads) > 0 else 1.0

        # Calculate imbalance (how far each teacher's load is from the average)
        imbalance = sum(abs(load - avg_load) for load in teacher_loads.values()) / len(teacher_loads)

        # Score: Higher score for teachers closer to an average load
        return max(0.0, 1.0 - (imbalance / avg_load))  # Normalize between 0 and 1

    def _score_day_balancing_slots_allocation(self, assignment: Assignment, current_assignments: List[Assignment]) -> float:
        slot_count_by_day = defaultdict(int)
        total_available = 0

        # Count the total available slots for the course on each day
        for slot in self.time_slots:
            if slot.day not in self.tracker.day_used_by_course_section[assignment.course.id][assignment.section.id]:
                slot_count_by_day[slot.day] += 1
                total_available += 1

        section = assignment.section

        # Count actual slots per day for this section
        day_count = Counter()
        for a in current_assignments:
            if a.section == section:
                for ts in a.slot_group:
                    day_count[ts.day] += 1

        # Add new assignment to the actual day count
        for ts in assignment.slot_group:
            day_count[ts.day] += 1

        # Normalize by ideal day allocation based on available slots
        total_assigned = sum(day_count.values())
        if total_assigned == 0 or total_available == 0:
            return 1.0  # No slots to balance, or no available slots

        # Ideal allocation of slots per day
        ideal = {day: slot_count_by_day[day] / total_available for day in slot_count_by_day}
        actual = {day: day_count[day] / total_assigned for day in slot_count_by_day}

        # Calculate squared error for day distribution
        error = sum((actual.get(day, 0.0) - ideal[day]) ** 2 for day in ideal)

        # Normalize error to keep the score between 0 and 1
        return max(0.0, 1.0 - min(error, 1.0))
