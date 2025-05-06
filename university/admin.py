from django.contrib import admin
from django.db.models import Count
from .models import Teacher, Course, Room, TimeSlot, Assignment, Department, Constrain, ConstrainType


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    # filter_horizontal = ('preferred_time_slots', 'preferred_courses')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'max_classes_per_week', 'is_assigned', 'get_total_loads', 'is_active')
    list_filter = ('is_assigned', 'department', 'is_active')
    filter_horizontal = ('preferred_time_slots', 'preferred_courses')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_loads=Count('assignment'))

    def get_total_loads(self, obj):
        return obj.total_loads

    get_total_loads.admin_order_field = 'total_loads'
    get_total_loads.short_description = 'Total Loads'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'semester', 'credit', 'sessions_per_week', 'duration_per_session', 'is_lab', 'is_assigned',
        'is_active', 'get_total_assignment'
    )
    list_filter = ('semester', 'is_lab', 'credit', 'is_assigned', 'department', 'is_active')
    search_fields = ('name', 'id', 'code')

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
    list_display = ('day', 'slot_number', 'is_active', 'get_total_assignment')
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
    list_filter = ('teacher', 'room', 'time_slot', 'course__semester', 'is_active')


@admin.register(ConstrainType)
class ConstrainTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Constrain)
class ConstrainAdmin(admin.ModelAdmin):
    list_display = ['type', 'condition', 'severity', 'is_active']
    list_filter = ('type', 'severity')
