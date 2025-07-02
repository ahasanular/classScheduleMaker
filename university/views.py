from collections import defaultdict
from weasyprint import HTML
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db.models import Count
from university.models import Assignment, TimeSlot, Teacher, Course, Shift, Section


def routine_test_view(request):
    assignments = Assignment.objects.select_related('course', 'teacher', 'room')
    time_slots = TimeSlot.objects.order_by('slot_number')
    semesters = sorted(set(a.course.semester for a in assignments))
    days = ['Thursday', 'Friday', 'Saturday']

    routine_data = {}

    for sem in semesters:
        sem_assignments = assignments.filter(course__semester=sem)
        row = {}
        for slot in time_slots:
            a = sem_assignments.filter(time_slot=slot).first()
            if a:
                row[slot] = f"({a.course.code}) {a.course.name} ({a.teacher.name})<br><small>{a.room.name}</small>"
            else:
                row[slot] = ""
        routine_data[sem] = row

    # Unassigned courses logic
    all_courses = Course.objects.filter(is_active=True)

    assigned_counts_qs = (
        Assignment.objects.values('course')
        .annotate(count=Count('id'))
    )

    assigned_counts = {entry['course']: entry['count'] for entry in assigned_counts_qs}

    unassigned = {}
    for course in all_courses:
        assigned = assigned_counts.get(course.id, 0)
        if assigned < course.sessions_per_week:
            unassigned[course.id] = {
                'code': course.code,
                'name': course.name,
                'session_needed_per_week': course.sessions_per_week,
                'assigned_per_week': assigned,
            }

    context = {
        'routine_data': routine_data,
        'time_slots': time_slots,
        'days': days,
        'unassigned': unassigned,
    }
    return render(request, 'routine.html', context)

def public_routine_view(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    assignments = Assignment.objects.filter(shift=shift).select_related('course', 'teacher', 'room')\
        .prefetch_related('time_slot')

    # Order time slots consistently
    time_slots = TimeSlot.objects.filter(shift=shift).order_by('day', 'slot_number')
    days = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday']

    # Build time slots grouped by day
    slots_by_day = defaultdict(list)
    for day in days:
        for slot in time_slots:
            if slot.day == day:
                slots_by_day[slot.day].append(slot)

    # Get unique semesters sections
    sections = sorted(set(a.section for a in assignments), key=lambda s: s.semester)
    all_courses = Course.objects.filter(is_active=True)

    # Initialize routine data
    routine_data = {f"{sec.semester}-{sec.name}": {day: [] for day in slots_by_day.keys()} for sec in sections}

    for sec in sections:
        sem_assignments = [a for a in assignments if a.section.id == sec.id]

        for day in slots_by_day.keys():
            slots = slots_by_day[day]
            # slot_ids = [s.id for s in slots]

            # Track which slots are already used (to avoid duplicates)
            used_slots = set()
            row = []

            i = 0
            while i < len(slots):
                slot = slots[i]

                # Check if any assignment starts at this slot
                matched_assignment = None
                for a in sem_assignments:
                    a_slot_ids = [s.id for s in a.time_slot.all() if s.day == day]
                    if slot.id in a_slot_ids and slot.id not in used_slots:
                        matched_assignment = a
                        break

                if matched_assignment:
                    a_slot_ids = [s.id for s in matched_assignment.time_slot.all() if s.day == day]
                    a_slot_objs = [s for s in matched_assignment.time_slot.all() if s.day == day]
                    a_slot_objs.sort(key=lambda x: x.slot_number)

                    # Count how many slots this assignment spans
                    colspan = len(a_slot_objs)

                    # Mark these slots as used
                    for s in a_slot_objs:
                        used_slots.add(s.id)

                    cell_text = f"({matched_assignment.course.code}) {matched_assignment.course.name} ({matched_assignment.teacher.name})<br><small>{matched_assignment.room.name}</small>"
                    row.append({'colspan': colspan, 'text': cell_text})
                    i += colspan
                else:
                    row.append({'colspan': 1, 'text': ""})
                    i += 1

            routine_data[f"{sec.semester}-{sec.name}"][day] = row

    # Count how many times each course is already assigned in this section
    unassigned = defaultdict(list)
    unassigned_count = 0
    for course in all_courses:
        for sec in Section.objects.filter(shift=shift, semester=course.semester):
            as_count = Assignment.objects.filter(course=course, section=sec).count()
            if as_count < course.sessions_per_week:
                unassigned[f"{sec.semester}-{sec.name}"].append(
                    {
                        'semester': sec.semester,
                        'section': sec.name,
                        'course_id': course.id,
                        'code': course.code,
                        'name': course.name,
                        'session_needed_per_week': course.sessions_per_week,
                        'assigned_per_week': as_count,
                    }
                )
                unassigned_count += 1
    unassigned = dict(sorted(unassigned.items()))

    context = {
        'routine_data': routine_data,
        'slots_by_day': slots_by_day,
        'days': slots_by_day.keys(),
        'unassigned': unassigned,
        'unassigned_count': unassigned_count,
        'shift_id': shift_id,
        'shift': shift,
    }
    return render(request, 'public_routine.html', context)

def teacher_routine_view(request, *args, **kwargs):
    teacher = get_object_or_404(Teacher, initial=kwargs['initial'])
    shifts = Shift.objects.all() # or order by id if needed
    days = ['Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday']

    all_routines = {}

    for shift in shifts:
        assignments = Assignment.objects.filter(shift=shift, teacher=teacher).select_related(
            'course', 'room', 'section').prefetch_related('time_slot')

        # time_slots = [ass.time_slot.all() for ass in assignments]

        time_slots = TimeSlot.objects.filter(shift=shift, assignments__in=assignments).distinct().order_by('day', 'slot_number')

        slots_by_day = defaultdict(list)
        for day in days:
            for slot in time_slots:
                if slot.day == day:
                    slots_by_day[day].append(slot)

        sections = sorted(set(a.section for a in assignments), key=lambda s: (s.semester, s.name))
        routine_data = {f"{sec.semester}-{sec.name}": {day: [] for day in slots_by_day.keys()} for sec in sections}

        for sec in sections:
            sec_assignments = [a for a in assignments if a.section.id == sec.id]

            for day in slots_by_day.keys():
                slots = slots_by_day[day]
                used_slots = set()
                row = []

                i = 0
                while i < len(slots):
                    slot = slots[i]
                    matched_assignment = None
                    for a in sec_assignments:
                        a_slot_ids = [s.id for s in a.time_slot.all() if s.day == day]
                        if slot.id in a_slot_ids and slot.id not in used_slots:
                            matched_assignment = a
                            break

                    if matched_assignment:
                        a_slot_objs = [s for s in matched_assignment.time_slot.all() if s.day == day]
                        a_slot_objs.sort(key=lambda x: x.slot_number)
                        colspan = len(a_slot_objs)
                        for s in a_slot_objs:
                            used_slots.add(s.id)

                        cell_text = f"({matched_assignment.course.code}) {matched_assignment.course.name}<br><small>{matched_assignment.room.name}</small>"
                        row.append({'colspan': colspan, 'text': cell_text})
                        i += colspan
                    else:
                        row.append({'colspan': 1, 'text': ""})
                        i += 1

                routine_data[f"{sec.semester}-{sec.name}"][day] = row

        all_routines[shift.name] = {
            'routine_data': routine_data,
            'slots_by_day': slots_by_day,
            'days': slots_by_day.keys(),
        }

    context = {
        'teacher': teacher,
        'all_routines': all_routines,
    }
    return render(request, 'teacher_routine.html', context)

def generate_routine_pdf(request, shift_id):
    DAYS = ['Thursday', 'Friday', 'Saturday']

    shift = get_object_or_404(Shift, id=shift_id)

    # Preload data
    timeslots = TimeSlot.objects.all().order_by('slot_number')
    assignments = Assignment.objects.filter(shift=shift).prefetch_related(
        'time_slot', 'course', 'teacher', 'room'
    )

    # Group by day
    day_map = defaultdict(list)
    for assignment in assignments:
        for ts in assignment.time_slot.all():
            day_map[ts.day].append({
                'assignment': assignment,
                'time_slots': list(assignment.time_slot.all()),
                'min_slot': min([s.slot_number for s in assignment.time_slot.all()])
            })

    # Get sorted days
    # days_sorted = sorted(day_map.items(), key=lambda x: x[0])  # Optional: custom weekday sort

    sorted_keys = [key for key in DAYS if key in day_map]
    days_sorted = {key: day_map[key] for key in DAYS}


    html_string = render_to_string('pdf/routine_pdf.html', {
        'days_data': days_sorted.items(),
        'all_slots': timeslots,
        'semesters': sorted({a.course.semester for a in assignments}),
    })

    html = HTML(string=html_string)
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="cse_evening_routine.pdf"'
    return response


from django.views import View
from django.http import HttpResponseRedirect
from django.core.management import call_command
from io import StringIO


class GenerateNewRoutineSet(View):
    """
    Django class-based view that runs a management command and redirects back to the referring URL.
    """

    def get(self, request, *args, **kwargs):
        command_name = 'generate'  # Replace with your management command name

        shift_id = kwargs.get('shift_id')
        shift = get_object_or_404(Shift, pk=shift_id)

        out = StringIO()
        err = StringIO()
        try:
            call_command(command_name, shift=shift.name, stdout=out, stderr=err)
        except Exception as ex:
            print(ex)
            pass

        # Get 'Referer' HTTP header to redirect back
        referer_url = request.META.get('HTTP_REFERER', '/')
        return HttpResponseRedirect(referer_url)