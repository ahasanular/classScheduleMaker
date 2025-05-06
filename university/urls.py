from django.urls import path
from university.views import routine_test_view, teacher_routine_view, public_routine_view, generate_routine_pdf

urlpatterns = [
    path('', public_routine_view, name='routine'),
    path('export/', generate_routine_pdf, name='export_routine_pdf'),
    path('scheduler/routine/', routine_test_view, name='routine'),
    path('routine/teacher/<initial>/', teacher_routine_view, name='teacher_routine'),
]
