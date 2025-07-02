from django.urls import path
from university.views import routine_test_view, teacher_routine_view, public_routine_view, generate_routine_pdf, GenerateNewRoutineSet

urlpatterns = [
    path('<int:shift_id>/', public_routine_view, name='routine'),
    path('export/<int:shift_id>/', generate_routine_pdf, name='export_routine_pdf'),
    path('scheduler/routine/', routine_test_view, name='routine'),
    path('routine/teacher/<initial>/', teacher_routine_view, name='teacher_routine'),
    path('generate/<int:shift_id>/', GenerateNewRoutineSet.as_view(), name='generate_routine_view'),
]
