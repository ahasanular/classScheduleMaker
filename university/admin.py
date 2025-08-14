from django.contrib import admin
from django.db.models import Count, Q, Value, CharField, F
from django.db.models.functions import Concat
from .models import Teacher, Course, Room, TimeSlot, Assignment, Department, Constrain, ConstrainType, Shift, Section


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    # filter_horizontal = ('preferred_time_slots', 'preferred_courses')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'max_classes_per_week', 'is_assigned', 'get_distribution', 'is_active')
    list_filter = ('is_assigned', 'department', 'is_active')
    filter_horizontal = ('preferred_time_slots', 'preferred_courses')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            morning=Count('assignment', filter=Q(assignment__shift_id=1)),
            evening=Count('assignment', filter=Q(assignment__shift_id=2))
        ).annotate(
            distribution=Concat(
                'morning', Value(' + '),
                'evening', Value(' = '),
                F('morning') + F('evening'),  # Sum the counts
                output_field=CharField()
            )
        ).annotate(total_loads=Count('assignment'))

    def get_distribution(self, obj):
        return obj.distribution

    get_distribution.admin_order_field = 'total_loads'
    get_distribution.short_description = 'Total Loads'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'semester', 'credit', 'sessions_per_week', 'duration_per_session', 'is_lab', 'is_assigned',
        'is_active', 'get_total_assignment'
    )
    list_filter = ('semester', 'is_lab', 'credit', 'is_assigned', 'department', 'is_active')
    search_fields = ('name', 'id', 'code')
    filter_horizontal = ('shifts',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_assigned=Count('assignment'))

    def get_total_assignment(self, obj):
        return obj.total_assigned

    get_total_assignment.admin_order_field = 'total_assigned'
    get_total_assignment.short_description = 'Total Assigned'


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'is_lab', 'department', 'is_active', 'get_total_assignment')
    list_filter = ('is_lab', 'department', 'is_active')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_assigned=Count('assignment'))

    def get_total_assignment(self, obj):
        return obj.total_assigned

    get_total_assignment.admin_order_field = 'total_assigned'
    get_total_assignment.short_description = 'Total Assigned'


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('day', 'slot_number', 'is_active', 'shift', 'get_total_assignment')
    list_filter = ('day', 'shift', 'is_active')
    ordering = ('day', 'slot_number', 'is_active')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_assigned=Count('assignments'))

    def get_total_assignment(self, obj):
        return obj.total_assigned

    get_total_assignment.admin_order_field = 'total_assigned'
    get_total_assignment.short_description = 'Total Assigned'

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('course', 'teacher', 'room', 'score', 'is_active')
    list_filter = ('shift', 'teacher', 'room', 'time_slot__day', 'course__semester', 'is_active')

    filter_horizontal = ('time_slot',)


@admin.register(ConstrainType)
class ConstrainTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Constrain)
class ConstrainAdmin(admin.ModelAdmin):
    list_display = ['type', 'condition', 'severity', 'is_active']
    list_filter = ('type', 'severity')

    actions = ['mark_as_active', 'mark_as_inactive']

    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users were marked as active.")

    def mark_as_inactive(self, request, queryset):
        """Mark selected users as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users were marked as inactive.")

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'semester', 'shift', 'department', 'is_active')
    list_filter = ('semester', 'shift', 'department', 'is_active')