from collections import defaultdict
from weasyprint import HTML
from django.http import Http404
from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse
from university.models import Assignment, TimeSlot, Teacher


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

    context = {
        'routine_data': routine_data,
        'time_slots': time_slots,
        'days': days,
    }
    return render(request, 'routine.html', context)

def public_routine_view(request):
    assignments = Assignment.objects.select_related('course', 'teacher', 'room')\
        .prefetch_related('time_slot')

    # Order time slots consistently
    time_slots = TimeSlot.objects.order_by('day', 'slot_number')
    days = ['Thursday', 'Friday', 'Saturday']

    # Build time slots grouped by day
    slots_by_day = {day: [] for day in days}
    for slot in time_slots:
        if slot.day in days:
            slots_by_day[slot.day].append(slot)

    # Get unique semesters
    semesters = sorted(set(a.course.semester for a in assignments))

    # Initialize routine data
    routine_data = {sem: {day: [] for day in days} for sem in semesters}

    for sem in semesters:
        sem_assignments = [a for a in assignments if a.course.semester == sem]

        for day in days:
            slots = slots_by_day[day]
            slot_ids = [s.id for s in slots]

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

            routine_data[sem][day] = row

    context = {
        'routine_data': routine_data,
        'slots_by_day': slots_by_day,
        'days': days,
    }
    return render(request, 'public_routine.html', context)

def teacher_routine_view(request, *args, **kwargs):
    teacher = Teacher.objects.get(initial=kwargs['initial'])
    if not teacher:
        raise Http404
    assignments = Assignment.objects.filter(teacher=teacher).select_related('course', 'teacher', 'room')
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
                row[slot] = f"{a.course.name} ({a.teacher.name})<br><small>{a.room.name}</small>"
            else:
                row[slot] = ""
        routine_data[sem] = row

    context = {
        'routine_data': routine_data,
        'time_slots': time_slots,
        'days': days,
    }
    return render(request, 'teacher_routine.html', context)

def generate_routine_pdf(request):
    DAYS = ['Thursday', 'Friday', 'Saturday']

    # Preload data
    timeslots = TimeSlot.objects.all().order_by('slot_number')
    assignments = Assignment.objects.filter().prefetch_related(
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

        out = StringIO()
        err = StringIO()
        try:
            call_command(command_name, stdout=out, stderr=err)
        except Exception:
            # Even if error, we will redirect back as per user request
            pass

        # Get 'Referer' HTTP header to redirect back
        referer_url = request.META.get('HTTP_REFERER', '/')
        return HttpResponseRedirect(referer_url)