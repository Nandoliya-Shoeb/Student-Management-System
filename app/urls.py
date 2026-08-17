from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('', views.dashboard, name='dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),

    # Students (admin)
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/<int:pk>/reset-password/', views.student_reset_password, name='student_reset_password'),
    path('students/csv-import/', views.student_csv_import, name='student_csv_import'),

    # Attendance (admin)
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/save/', views.attendance_save, name='attendance_save'),
    path('attendance/bulk-action/', views.attendance_bulk_action, name='attendance_bulk_action'),
    path('attendance/pdf/', views.attendance_pdf_export, name='attendance_pdf_export'),
    path('attendance/excel/', views.attendance_excel_export, name='attendance_excel_export'),

    # Fees
    path('fees/', views.fee_list, name='fee_list'),
    path('fees/create/', views.fee_create, name='fee_create'),
    path('fees/<int:pk>/edit/', views.fee_edit, name='fee_edit'),
    path('fees/<int:pk>/delete/', views.fee_delete, name='fee_delete'),
    path('fees/<int:pk>/mark-paid/', views.fee_mark_paid, name='fee_mark_paid'),
    path('fees/<int:pk>/receipt/', views.fee_pdf_receipt, name='fee_pdf_receipt'),

    # Quiz management
    path('quiz/', views.quiz_list, name='quiz_list'),
    path('quiz/create/', views.quiz_create, name='quiz_create'),
    path('quiz/<int:pk>/edit/', views.quiz_edit, name='quiz_edit'),
    path('quiz/<int:pk>/delete/', views.quiz_delete, name='quiz_delete'),
    path('quiz/<int:pk>/questions/', views.quiz_questions, name='quiz_questions'),
    path('quiz/<int:pk>/take/', views.quiz_take, name='quiz_take'),

    # Questions
    path('question/<int:quiz_pk>/create/', views.question_create, name='question_create'),
    path('question/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('question/<int:pk>/delete/', views.question_delete, name='question_delete'),

    # Quiz results
    path('quiz-result/<int:pk>/', views.quiz_result, name='quiz_result'),
    path('quiz-result/<int:pk>/pdf/', views.quiz_result_pdf, name='quiz_result_pdf'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),
]
