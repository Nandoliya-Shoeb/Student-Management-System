from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Avg, Sum, Max, Case, When, Value, IntegerField, F, ExpressionWrapper, DecimalField
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, JsonResponse, Http404
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password
from datetime import datetime, timedelta
import csv
import io
from decimal import Decimal
import json

from .models import Student, Attendance, Fee, Quiz, Question, QuizResult, StudentAnswer, Progress
from .forms import (
    LoginForm, StudentForm, AttendanceForm, BulkAttendanceForm,
    FeeForm, QuizForm, QuestionForm, CSVImportForm, StudentUserForm
)
from .utils import (
    generate_pdf_receipt, generate_pdf_attendance, generate_excel_report,
    generate_pdf_result, calculate_attendance_percentage,
    calculate_student_performance, get_formatted_time
)


from django.utils import translation
from django.conf import settings


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def change_language(request):
    """
    Bulletproof language switcher view that properly redirects between English and Gujarati
    and removes/adds the language URL prefix accurately.
    """
    lang = request.POST.get('language') or request.GET.get('language', 'en')
    if lang not in ('en', 'gu'):
        lang = 'en'

    translation.activate(lang)

    # Get raw next path
    next_url = request.POST.get('next') or request.GET.get('next') or '/'

    # Strip any existing /gu/ or /en/ prefix
    path = next_url
    if path.startswith('/gu/'):
        path = path[3:]
    elif path == '/gu':
        path = '/'
    elif path.startswith('/en/'):
        path = path[3:]
    elif path == '/en':
        path = '/'

    if not path.startswith('/'):
        path = '/' + path

    # If switching to Gujarati, prepend /gu
    if lang == 'gu':
        target_url = f'/gu{path}' if path != '/' else '/gu/'
    else:
        target_url = path

    response = redirect(target_url)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
    if hasattr(request, 'session'):
        request.session['_language'] = lang
    return response


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_student_for_user(user):
    """Return the Student linked to this user, or None if not a student."""
    try:
        return user.student
    except (Student.DoesNotExist, AttributeError):
        return None


def is_student_user(user):
    return get_student_for_user(user) is not None


# ---------------------------------------------------------------------------
# Authentication views
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        student = get_student_for_user(request.user)
        if student:
            return redirect('student_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is None and username.lower() != 'admin':
                user = authenticate(request, username=username.upper(), password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, _('Your account is inactive. Contact admin.'))
                    return render(request, 'login.html', {'form': form})
                login(request, user)
                request.session.set_expiry(10 * 60 * 60)
                messages.success(request, _('Login successful!'))
                student = get_student_for_user(user)
                if student:
                    # --- AUTO ATTENDANCE POPUP LOGIC ---
                    now_local = timezone.localtime(timezone.now())
                    today = now_local.date()
                    current_time = now_local.time()
                    from datetime import time as dtime
                    window_start = dtime(9, 0)   # 09:00 AM
                    window_end = dtime(18, 0)     # 06:00 PM
                    in_window = window_start <= current_time <= window_end
                    already_marked = Attendance.objects.filter(student=student, date=today).exists()
                    if in_window and not already_marked:
                        request.session['show_attendance_popup'] = True
                        request.session['attendance_login_time'] = current_time.strftime('%H:%M:%S')
                    else:
                        request.session.pop('show_attendance_popup', None)
                    # -----------------------------------
                    return redirect('student_dashboard')
                return redirect('dashboard')
            else:
                messages.error(request, _('Invalid credentials. Please try again.'))
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, _('Logged out successfully.'))
    return redirect('login')


# ---------------------------------------------------------------------------
# Student Mark Attendance via Popup (AJAX)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
@require_http_methods(["POST"])
def student_mark_attendance(request):
    """Called via AJAX when student clicks 'Mark Present' in popup."""
    student = get_student_for_user(request.user)
    if not student:
        return JsonResponse({'success': False, 'error': 'Not a student'}, status=403)

    now_local = timezone.localtime(timezone.now())
    today = now_local.date()
    current_time = now_local.time()

    # Check window 9AM - 6PM
    from datetime import time as dtime
    window_start = dtime(9, 0)
    window_end = dtime(18, 0)
    if not (window_start <= current_time <= window_end):
        return JsonResponse({'success': False, 'error': 'Outside attendance window (9AM - 6PM)'})

    # Only create if not already marked
    record, created = Attendance.objects.get_or_create(
        student=student,
        date=today,
        defaults={
            'status': 'present',
            'login_time': current_time,
            'auto_marked': True,
            'remarks': 'Auto-marked via student login popup',
        }
    )

    # Clear session flag
    request.session.pop('show_attendance_popup', None)
    request.session.pop('attendance_login_time', None)

    return JsonResponse({
        'success': True,
        'created': created,
        'status': record.status,
        'login_time': current_time.strftime('%I:%M %p'),
        'message': 'Attendance marked as Present!' if created else 'Already marked: ' + record.status.capitalize(),
    })




# Helper function to auto-mark absent after 6 PM on-the-fly (no paid scheduled task needed)
def auto_mark_absent_on_the_fly():
    now_local = timezone.localtime(timezone.now())
    today = now_local.date()
    current_time = now_local.time()
    from datetime import time as dtime
    if current_time >= dtime(18, 0):  # After 6:00 PM
        active_students = Student.objects.filter(status='active')
        for student in active_students:
            Attendance.objects.get_or_create(
                student=student,
                date=today,
                defaults={
                    'status': 'absent',
                    'auto_marked': True,
                    'remarks': 'Auto-marked absent (No login between 09:00 AM - 06:00 PM)'
                }
            )


# ---------------------------------------------------------------------------
# Admin dashboard (staff/superuser only)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def dashboard(request):
    # If logged-in user is a student, redirect to student dashboard
    if is_student_user(request.user):
        return redirect('student_dashboard')

    auto_mark_absent_on_the_fly()

    total_students = Student.objects.count()
    active_students = Student.objects.filter(status='active').count()
    pending_fees = Fee.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
    collected_fees = Fee.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0

    today = timezone.localdate()
    today_attendance = Attendance.objects.filter(date=today).aggregate(
        present=Count(Case(When(status='present', then=1))),
        absent=Count(Case(When(status='absent', then=1))),
        leave=Count(Case(When(status='leave', then=1)))
    )

    quiz_results = QuizResult.objects.all()
    avg_score = quiz_results.aggregate(avg=Avg('percentage'))['avg'] or 0

    total_quizzes = Quiz.objects.filter(is_active=True).count()
    total_tests_taken = quiz_results.count()

    class_counts = {
        '5': Student.objects.filter(class_field='5', status='active').count(),
        '6': Student.objects.filter(class_field='6', status='active').count(),
        '7': Student.objects.filter(class_field='7', status='active').count(),
        '8': Student.objects.filter(class_field='8', status='active').count(),
    }

    context = {
        'total_students': total_students,
        'active_students': active_students,
        'pending_fees': pending_fees,
        'collected_fees': collected_fees,
        'class_counts': class_counts,
        'total_quizzes': total_quizzes,
        'total_tests_taken': total_tests_taken,
        'avg_score': round(avg_score, 2),
        'recent_results': QuizResult.objects.select_related('student', 'quiz').order_by('-taken_date')[:6],
        'recent_students': Student.objects.order_by('-created_at')[:5],
        'is_admin_view': True,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------------------------------------------------------
# Student dashboard (student users only)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def student_dashboard(request):
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, _('Access denied.'))
        return redirect('dashboard')

    auto_mark_absent_on_the_fly()

    # Real data only — all filtered by authenticated student
    attendance_pct = calculate_attendance_percentage(student)
    attendance_today = Attendance.objects.filter(student=student, date=timezone.localdate()).first()

    quiz_results = QuizResult.objects.filter(student=student).select_related('quiz').order_by('-taken_date')
    total_tests = quiz_results.count()
    avg_score = quiz_results.aggregate(avg=Avg('percentage'))['avg'] or 0
    best_score = quiz_results.aggregate(best=Max('percentage'))['best'] or 0

    fees = Fee.objects.filter(student=student)
    paid_fees = fees.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    pending_fees = fees.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    available_quizzes = Quiz.objects.filter(is_active=True).order_by('-created_at')[:5]

    # Monthly attendance breakdown (last 30 days)
    thirty_days_ago = timezone.localdate() - timedelta(days=30)
    recent_attendance = Attendance.objects.filter(
        student=student, date__gte=thirty_days_ago
    ).order_by('-date')[:10]

    # Pop popup flag from session (show once)
    show_popup = request.session.pop('show_attendance_popup', False)
    attendance_login_time = request.session.pop('attendance_login_time', None)

    context = {
        'student': student,
        'attendance_pct': attendance_pct,
        'attendance_today': attendance_today,
        'total_tests': total_tests,
        'avg_score': round(float(avg_score), 2),
        'best_score': round(float(best_score), 2),
        'paid_fees': paid_fees,
        'pending_fees': pending_fees,
        'recent_results': quiz_results[:5],
        'available_quizzes': available_quizzes,
        'recent_attendance': recent_attendance,
        'is_student_view': True,
        'show_attendance_popup': show_popup,
        'attendance_login_time': attendance_login_time,
    }
    return render(request, 'student_dashboard.html', context)


# ---------------------------------------------------------------------------
# Student management (admin only)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def student_list(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    students = Student.objects.select_related('user').all()

    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | Q(student_id__icontains=search_query)
        )

    class_filter = request.GET.get('class', '')
    if class_filter:
        students = students.filter(class_field=class_filter)

    status_filter = request.GET.get('status', '')
    if status_filter:
        students = students.filter(status=status_filter)

    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    students_page = paginator.get_page(page_number)

    context = {
        'students': students_page,
        'search_query': search_query,
        'class_filter': class_filter,
        'status_filter': status_filter,
    }
    return render(request, 'students/list.html', context)


@login_required(login_url='login')
def student_detail(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    student = get_object_or_404(Student, pk=pk)

    attendance_records = Attendance.objects.filter(student=student).order_by('-date')
    attendance_pct = calculate_attendance_percentage(student)

    fees = Fee.objects.filter(student=student)
    paid_fees = fees.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    pending_fees = fees.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    quiz_results = QuizResult.objects.filter(student=student).select_related('quiz').order_by('-taken_date')[:5]

    try:
        progress = student.progress
    except Progress.DoesNotExist:
        progress = Progress.objects.create(student=student)

    context = {
        'student': student,
        'attendance_records': attendance_records[:10],
        'attendance_percentage': attendance_pct,
        'paid_fees': paid_fees,
        'pending_fees': pending_fees,
        'quiz_results': quiz_results,
        'progress': progress,
    }
    return render(request, 'students/detail.html', context)


@login_required(login_url='login')
def student_create(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        user_form = StudentUserForm(request.POST)
        if form.is_valid() and user_form.is_valid():
            with transaction.atomic():
                # Create Django User for student
                student_id = form.cleaned_data['student_id']
                # Default password to GR.NO if not explicitly provided
                password = user_form.cleaned_data.get('password') or student_id

                # Use student_id as Django username
                if User.objects.filter(username=student_id).exists():
                    messages.error(request, _('A user with this GR.NO already exists.'))
                    return render(request, 'students/form.html', {
                        'form': form, 'user_form': user_form, 'title': _('Add Student')
                    })

                django_user = User.objects.create_user(
                    username=student_id,
                    password=password,
                    first_name=form.cleaned_data['name'],
                    email=form.cleaned_data.get('email') or '',
                )

                student = form.save(commit=False)
                student.user = django_user
                student.save()
                Progress.objects.create(student=student)

            messages.success(request, _('Student added successfully.'))
            return redirect('student_detail', pk=student.pk)
    else:
        form = StudentForm()
        user_form = StudentUserForm()

    return render(request, 'students/form.html', {
        'form': form,
        'user_form': user_form,
        'title': _('Add Student'),
    })


@login_required(login_url='login')
def student_edit(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            with transaction.atomic():
                student = form.save()
                # Sync name/email to linked User
                if student.user:
                    student.user.first_name = student.name
                    student.user.email = student.email or ''
                    student.user.save()
            messages.success(request, _('Student updated successfully.'))
            return redirect('student_detail', pk=student.pk)
    else:
        form = StudentForm(instance=student)

    return render(request, 'students/form.html', {
        'form': form,
        'title': _('Edit Student'),
        'student': student,
    })


@login_required(login_url='login')
def student_reset_password(request, pk):
    """Allow admin to reset a student's login password."""
    if is_student_user(request.user):
        return redirect('student_dashboard')

    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '').strip()
        # If left blank, default to GR.NO
        if not new_password:
            new_password = student.student_id

        with transaction.atomic():
            if student.user:
                student.user.set_password(new_password)
                student.user.save()
            else:
                # Create user if it doesn't exist
                django_user = User.objects.create_user(
                    username=student.student_id,
                    password=new_password,
                    first_name=student.name,
                    email=student.email or '',
                )
                student.user = django_user
                student.save(update_fields=['user'])

        messages.success(request, f'✅ {student.name} નો પાસવર્ડ સેટ થઈ ગયો: {new_password}')
        return redirect('student_detail', pk=pk)

    return render(request, 'students/reset_password.html', {'student': student})


@login_required(login_url='login')
def student_delete(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        with transaction.atomic():
            if student.user:
                student.user.delete()  # Cascade-deletes student via SET_NULL will set null
            student.delete()
        messages.success(request, _('Student deleted successfully.'))
        return redirect('student_list')

    return render(request, 'students/confirm_delete.html', {'student': student})


@login_required(login_url='login')
def student_bulk_delete(request):
    """Delete multiple selected students in one go."""
    if is_student_user(request.user):
        return redirect('student_dashboard')

    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        if not student_ids:
            messages.warning(request, _('કૃપા કરીને ડિલીટ કરવા માટે ઓછામાં ઓછો એક વિદ્યાર્થી પસંદ કરો.'))
            return redirect('student_list')

        with transaction.atomic():
            students = Student.objects.filter(pk__in=student_ids)
            count = students.count()
            user_ids = [s.user_id for s in students if s.user_id]
            if user_ids:
                User.objects.filter(id__in=user_ids).delete()
            students.delete()

        messages.success(request, f'✅ {count} {_("વિદ્યાર્થીઓ સફળતાપૂર્વક ડિલીટ થઈ ગયા.")}')

    return redirect('student_list')


@login_required(login_url='login')
def student_csv_import(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['csv_file']
            default_class = form.cleaned_data.get('default_class', '8')
            try:
                rows_data = []

                # Handle Excel (.xlsx, .xls) files directly
                if uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
                    import openpyxl
                    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                    sheet = wb.active
                    all_rows = list(sheet.iter_rows(values_only=True))
                    if all_rows:
                        headers = [str(h).strip() if h is not None else '' for h in all_rows[0]]
                        for r in all_rows[1:]:
                            if not any(cell is not None and str(cell).strip() != '' for cell in r):
                                continue
                            row_dict = {}
                            for col_idx, h in enumerate(headers):
                                if h and col_idx < len(r):
                                    row_dict[h] = r[col_idx]
                            rows_data.append(row_dict)
                else:
                    # Handle CSV and TXT files
                    raw_bytes = uploaded_file.read()
                    try:
                        raw_content = raw_bytes.decode('utf-8-sig')
                    except UnicodeDecodeError:
                        try:
                            raw_content = raw_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            raw_content = raw_bytes.decode('latin-1')

                    sample = raw_content[:2048]
                    delimiter = '\t' if '\t' in sample and sample.count('\t') > sample.count(',') else ','
                    reader = csv.DictReader(io.StringIO(raw_content), delimiter=delimiter)
                    for r in reader:
                        if any(val is not None and str(val).strip() != '' for val in r.values()):
                            rows_data.append(r)

                created_count = 0
                updated_count = 0
                errors = []

                def parse_flex_date(date_val):
                    if not date_val:
                        return timezone.localdate()
                    from datetime import date as dt_date
                    if isinstance(date_val, datetime):
                        return date_val.date()
                    if isinstance(date_val, dt_date):
                        return date_val

                    val = str(date_val).strip()
                    formats = [
                        '%m/%d/%Y', '%d/%m/%Y', '%d-%m-%Y', '%m-%d-%Y',
                        '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
                        '%d.%m.%Y', '%m.%d.%Y',
                        '%d/%m/%y', '%m/%d/%y', '%d-%m-%y', '%m-%d-%y',
                        '%d %b %Y', '%d %B %Y',
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(val, fmt).date()
                        except ValueError:
                            continue
                    return timezone.localdate()

                for row_idx, raw_row in enumerate(rows_data, start=2):
                    try:
                        # Clean and normalize column names (lowercase, no spaces, no dots, no underscores)
                        row = {}
                        for k, v in raw_row.items():
                            if k:
                                norm_k = str(k).strip().lower().replace('.', '').replace(' ', '').replace('_', '').replace('-', '')
                                row[norm_k] = v if v is not None else ''

                        # Extract fields flexibly
                        sr_no = row.get('srno') or row.get('sr') or row.get('serialno') or row.get('sno') or ''
                        gr_no = row.get('grno') or row.get('gr') or row.get('grnumber') or row.get('studentid') or row.get('id') or row.get('rollno') or ''
                        name = row.get('studentname') or row.get('name') or row.get('student') or row.get('fullname') or ''
                        dob_val = row.get('dob') or row.get('birthdate') or row.get('dateofbirth') or row.get('joiningdate') or ''
                        address = row.get('address') or row.get('add') or row.get('city') or ''
                        mobile = row.get('mobailno') or row.get('mobileno') or row.get('mobail') or row.get('mobile') or row.get('phone') or row.get('phoneno') or row.get('contact') or row.get('parentmobile') or ''
                        parent_name = row.get('parentname') or row.get('fathername') or row.get('guardianname') or ''
                        email = row.get('email') or row.get('emailid') or ''
                        class_val = row.get('class') or row.get('classfield') or row.get('grade') or row.get('standard') or row.get('std') or row.get('dhoran') or default_class

                        # Convert to strings
                        name = str(name).strip()
                        gr_no = str(gr_no).strip()
                        sr_no = str(sr_no).strip()
                        address = str(address).strip()
                        parent_name = str(parent_name).strip()
                        email = str(email).strip()

                        # Format mobile number cleanly (remove decimal like 8154068812.0)
                        if mobile != '':
                            if isinstance(mobile, float) and mobile.is_integer():
                                mobile = str(int(mobile))
                            else:
                                mobile = str(mobile).split('.')[0].strip()
                        else:
                            mobile = ''

                        # Ensure valid class choice (5, 6, 7, 8)
                        class_val = str(class_val).strip()
                        if class_val not in ['5', '6', '7', '8']:
                            digits = [c for c in class_val if c in '5678']
                            class_val = digits[0] if digits else default_class

                        if not name:
                            if not gr_no and not sr_no and not mobile:
                                continue
                            errors.append(f"Row {row_idx}: {_('Student name is required')}")
                            continue

                        # Format Student ID / GR Number (Only clean number, no STD prefix)
                        if gr_no:
                            if gr_no.endswith('.0'):
                                gr_no = gr_no[:-2]
                            stu_id = gr_no.strip()
                        elif sr_no:
                            if sr_no.endswith('.0'):
                                sr_no = sr_no[:-2]
                            stu_id = str(sr_no).strip()
                        else:
                            stu_id = str(row_idx)

                        joining_date = parse_flex_date(dob_val)

                        # Create or Update Student
                        student, is_created = Student.objects.update_or_create(
                            student_id=stu_id,
                            defaults={
                                'name': name,
                                'parent_name': parent_name or None,
                                'parent_mobile': mobile or '',
                                'phone': mobile or '',
                                'email': email or None,
                                'class_field': class_val,
                                'address': address or '',
                                'joining_date': joining_date,
                                'status': 'active',
                            }
                        )

                        # Auto-create User account for Student Portal Login
                        if not student.user:
                            user_uname = student.student_id
                            existing_user = User.objects.filter(username=user_uname).first()
                            if not existing_user:
                                new_u = User.objects.create_user(
                                    username=user_uname,
                                    password=student.student_id,  # Default password = Student ID
                                    first_name=student.name[:30],
                                )
                                student.user = new_u
                                student.save(update_fields=['user'])
                            else:
                                student.user = existing_user
                                student.save(update_fields=['user'])

                        Progress.objects.get_or_create(student=student)

                        if is_created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except Exception as e:
                        errors.append(f"Row {row_idx}: {str(e)}")

                if created_count > 0 or updated_count > 0:
                    messages.success(
                        request,
                        f'✅ {created_count} {_("new students added")}, {updated_count} {_("students updated successfully.")}'
                    )

                for error in errors[:10]:
                    messages.warning(request, error)

                return redirect('student_list')

            except Exception as e:
                messages.error(request, f'{_("Error reading file:")} {str(e)}')
    else:
        form = CSVImportForm()

    return render(request, 'students/csv_import.html', {'form': form})




# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def attendance_list(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    auto_mark_absent_on_the_fly()

    today = timezone.localdate()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    date_str = request.GET.get('date', '').strip()

    # Determine start_date and end_date
    if start_date_str:
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date_obj = today
    elif date_str:
        try:
            start_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date_obj = today
    else:
        start_date_obj = today

    if end_date_str:
        try:
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date_obj = start_date_obj
    else:
        end_date_obj = start_date_obj

    search_query = request.GET.get('search', '').strip()
    class_filter = request.GET.get('class', '').strip()

    students = Student.objects.filter(status='active').order_by('student_id')

    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | Q(student_id__icontains=search_query)
        )

    if class_filter:
        students = students.filter(class_field=class_filter)

    # For daily attendance marking, use start_date_obj
    attendance_records = Attendance.objects.filter(date=start_date_obj).select_related('student')

    attendance_data = []
    for student in students:
        record = attendance_records.filter(student=student).first()
        attendance_data.append({
            'student': student,
            'record': record,
            'status': record.status if record else 'absent',
            'remarks': record.remarks if record else '',
        })

    context = {
        'attendance_data': attendance_data,
        'start_date': start_date_obj.strftime('%Y-%m-%d'),
        'end_date': end_date_obj.strftime('%Y-%m-%d'),
        'date_filter': start_date_obj.strftime('%Y-%m-%d'),
        'date_filter_display': start_date_obj.strftime('%d-%m-%Y'),
        'search_query': search_query,
        'class_filter': class_filter,
    }
    return render(request, 'attendance/list.html', context)


@login_required(login_url='login')
@require_http_methods(["POST"])
def attendance_save(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    date_str = request.POST.get('date')

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        messages.error(request, _('Invalid date.'))
        return redirect('attendance_list')

    # Get student IDs posted in the form
    posted_student_ids = []
    for key in request.POST.keys():
        if key.startswith('status_'):
            try:
                posted_student_ids.append(int(key.split('_')[1]))
            except (ValueError, IndexError):
                pass

    students = Student.objects.filter(id__in=posted_student_ids)

    try:
        with transaction.atomic():
            for student in students:
                status = request.POST.get(f'status_{student.id}', 'absent')
                remarks = request.POST.get(f'remarks_{student.id}', '')

                # Validate status
                if status not in ('present', 'absent', 'leave'):
                    status = 'absent'

                Attendance.objects.update_or_create(
                    student=student,
                    date=date_obj,
                    defaults={'status': status, 'remarks': remarks}
                )

        messages.success(request, _('Attendance saved successfully.'))
    except Exception as e:
        messages.error(request, f'{_("Error saving attendance:")} {str(e)}')

    from django.urls import reverse
    # Preserve filter params on redirect
    redirect_url = f"{reverse('attendance_list')}?start_date={date_obj}"
    end_date = request.POST.get('end_date', '').strip()
    class_filter = request.POST.get('class_filter', '').strip()
    search_query = request.POST.get('search_query', '').strip()
    if end_date:
        redirect_url += f"&end_date={end_date}"
    if class_filter:
        redirect_url += f"&class={class_filter}"
    if search_query:
        redirect_url += f"&search={search_query}"

    return redirect(redirect_url)


@login_required(login_url='login')
@require_http_methods(["POST"])
def attendance_bulk_action(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    date_str = request.POST.get('date')
    action = request.POST.get('action', 'present')

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        messages.error(request, _('Invalid date.'))
        return redirect('attendance_list')

    if action not in ('present', 'absent', 'leave'):
        action = 'absent'

    # Respect class / search filter if posted
    class_filter = request.POST.get('class_filter', '').strip()
    search_query = request.POST.get('search_query', '').strip()

    students = Student.objects.filter(status='active')
    if class_filter:
        students = students.filter(class_field=class_filter)
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | Q(student_id__icontains=search_query)
        )

    with transaction.atomic():
        for student in students:
            Attendance.objects.update_or_create(
                student=student,
                date=date_obj,
                defaults={'status': action, 'remarks': ''}
            )

    action_labels = {
        'present': _('Present'),
        'absent': _('Absent'),
        'leave': _('Leave'),
    }
    messages.success(request, f'{_("All students marked as")} {action_labels.get(action, action)}.')
    from django.urls import reverse
    return redirect(f"{reverse('attendance_list')}?start_date={date_obj}")


@login_required(login_url='login')
def attendance_pdf_export(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    today = timezone.localdate()
    start_date_str = request.GET.get('start_date') or request.GET.get('date') or today.strftime('%Y-%m-%d')
    end_date_str = request.GET.get('end_date') or start_date_str

    try:
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = today

    try:
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        end_date_obj = start_date_obj

    if start_date_obj > end_date_obj:
        start_date_obj, end_date_obj = end_date_obj, start_date_obj

    class_filter = request.GET.get('class', '').strip()
    search_query = request.GET.get('search', '').strip()

    attendance_records = Attendance.objects.filter(
        date__gte=start_date_obj, date__lte=end_date_obj
    ).select_related('student').order_by('date', 'student__class_field', 'student__name')

    if class_filter:
        attendance_records = attendance_records.filter(student__class_field=class_filter)
    if search_query:
        attendance_records = attendance_records.filter(
            Q(student__name__icontains=search_query) | Q(student__student_id__icontains=search_query)
        )

    return generate_pdf_attendance(attendance_records, start_date_obj, end_date_obj)


@login_required(login_url='login')
def attendance_excel_export(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    today = timezone.localdate()
    start_date_str = request.GET.get('start_date') or request.GET.get('date') or today.strftime('%Y-%m-%d')
    end_date_str = request.GET.get('end_date') or start_date_str

    try:
        start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date_obj = today

    try:
        end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        end_date_obj = start_date_obj

    if start_date_obj > end_date_obj:
        start_date_obj, end_date_obj = end_date_obj, start_date_obj

    class_filter = request.GET.get('class', '').strip()
    search_query = request.GET.get('search', '').strip()

    attendance_records = Attendance.objects.filter(
        date__gte=start_date_obj, date__lte=end_date_obj
    ).select_related('student').order_by('date', 'student__class_field', 'student__name')

    if class_filter:
        attendance_records = attendance_records.filter(student__class_field=class_filter)
    if search_query:
        attendance_records = attendance_records.filter(
            Q(student__name__icontains=search_query) | Q(student__student_id__icontains=search_query)
        )

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    if start_date_obj == end_date_obj:
        filename = f"attendance_{start_date_obj}"
    else:
        filename = f"attendance_{start_date_obj}_to_{end_date_obj}"

    if class_filter:
        filename += f"_grade_{class_filter}"
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return generate_excel_report('attendance', attendance_records, start_date_obj, response, end_date=end_date_obj)


# ---------------------------------------------------------------------------
# Fees (admin only)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def fee_list(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    fees = Fee.objects.select_related('student')

    status_filter = request.GET.get('status', '')
    if status_filter:
        fees = fees.filter(status=status_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        fees = fees.filter(student__name__icontains=search_query)

    paginator = Paginator(fees, 25)
    page_number = request.GET.get('page')
    fees_page = paginator.get_page(page_number)

    total_paid = Fee.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    total_pending = Fee.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'fees': fees_page,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_paid': total_paid,
        'total_pending': total_pending,
    }
    return render(request, 'fees/list.html', context)


@login_required(login_url='login')
def fee_create(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = FeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Fee added successfully.'))
            return redirect('fee_list')
    else:
        form = FeeForm()

    return render(request, 'fees/form.html', {'form': form, 'title': _('Add Fee')})


@login_required(login_url='login')
def fee_edit(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    fee = get_object_or_404(Fee, pk=pk)

    if request.method == 'POST':
        form = FeeForm(request.POST, instance=fee)
        if form.is_valid():
            form.save()
            messages.success(request, _('Fee updated successfully.'))
            return redirect('fee_list')
    else:
        form = FeeForm(instance=fee)

    return render(request, 'fees/form.html', {'form': form, 'title': _('Edit Fee')})


@login_required(login_url='login')
def fee_delete(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    fee = get_object_or_404(Fee, pk=pk)

    if request.method == 'POST':
        fee.delete()
        messages.success(request, _('Fee deleted successfully.'))
        return redirect('fee_list')

    return render(request, 'fees/confirm_delete.html', {'fee': fee})


@login_required(login_url='login')
@require_http_methods(["POST"])
def fee_mark_paid(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    fee = get_object_or_404(Fee, pk=pk)
    fee.status = 'paid'
    fee.payment_date = timezone.localdate()
    fee.save()
    messages.success(request, _('Fee marked as paid.'))
    return redirect('fee_list')


@login_required(login_url='login')
def fee_pdf_receipt(request, pk):
    fee = get_object_or_404(Fee, pk=pk)
    # Students can only view their own fee receipts
    if is_student_user(request.user):
        student = get_student_for_user(request.user)
        if fee.student != student:
            raise Http404
    return generate_pdf_receipt(fee)


# ---------------------------------------------------------------------------
# Quiz management (admin CRUD)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def quiz_list(request):
    quizzes = Quiz.objects.annotate(
        question_count=Count('questions'),
        attempt_count=Count('results'),
    ).order_by('id')

    is_student = is_student_user(request.user)

    # Search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        quizzes = quizzes.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    # Category / Grade filter
    category = request.GET.get('category', 'all').strip()
    if category == 'std56':
        quizzes = quizzes.filter(
            Q(title__icontains='STD 5-6') | Q(title__icontains='ધોરણ ૫-૬') | Q(title__icontains='Basics') | Q(title__icontains='Fundamentals') |
            Q(title__icontains='Input') | Q(title__icontains='Output') | Q(title__icontains='Hardware') |
            Q(title__icontains='Paint') | Q(title__icontains='Safety') | Q(title__icontains='Windows') |
            Q(title__icontains='પરિચય') | Q(title__icontains='ઇનપુટ') | Q(title__icontains='આઉટપુટ') |
            Q(title__icontains='હાર્ડવેર') | Q(title__icontains='પેઇન્ટ') | Q(title__icontains='સુરક્ષા') |
            Q(title__icontains='વિન્ડોઝ')
        )
    elif category == 'msoffice':
        quizzes = quizzes.filter(
            Q(title__icontains='Word') | Q(title__icontains='Excel') | Q(title__icontains='PowerPoint') |
            Q(title__icontains='વર્ડ') | Q(title__icontains='એક્સેલ') | Q(title__icontains='પાવરપોઇન્ટ')
        )
    elif category == 'networking':
        quizzes = quizzes.filter(
            Q(title__icontains='Network') | Q(title__icontains='Internet') |
            Q(title__icontains='Mail') | Q(title__icontains='Email') | Q(title__icontains='Cyber') | Q(title__icontains='Security') |
            Q(title__icontains='નેટવર્ક') | Q(title__icontains='ઇન્ટરનેટ') | Q(title__icontains='મેઇલ') | Q(title__icontains='સાયબર')
        )
    elif category == 'coding':
        quizzes = quizzes.filter(
            Q(title__icontains='Coding') | Q(title__icontains='Algorithm') | Q(title__icontains='Logic') | Q(title__icontains='Evolution') |
            Q(title__icontains='કોડિંગ') | Q(title__icontains='અલ્ગોરિધમ') | Q(title__icontains='ઇતિહાસ')
        )

    # Student filtering
    taken_ids = []
    if is_student:
        student = get_student_for_user(request.user)
        taken_ids = list(QuizResult.objects.filter(student=student).values_list('quiz_id', flat=True))
        quizzes = quizzes.filter(is_active=True)

    paginator = Paginator(quizzes, 12)
    page_number = request.GET.get('page')
    quizzes_page = paginator.get_page(page_number)

    context = {
        'quizzes': quizzes_page,
        'taken_ids': taken_ids,
        'is_student_view': is_student,
        'search_query': search_query,
        'active_category': category,
        'total_count': quizzes.count(),
    }

    return render(request, 'quiz/list.html', context)


@login_required(login_url='login')
def quiz_create(request):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save()
            messages.success(request, _('Quiz created successfully.'))
            return redirect('quiz_questions', pk=quiz.pk)
    else:
        form = QuizForm()

    return render(request, 'quiz/form.html', {'form': form, 'title': _('Create Quiz')})


@login_required(login_url='login')
def quiz_edit(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    quiz = get_object_or_404(Quiz, pk=pk)

    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, _('Quiz updated successfully.'))
            return redirect('quiz_questions', pk=quiz.pk)
    else:
        form = QuizForm(instance=quiz)

    return render(request, 'quiz/form.html', {'form': form, 'title': _('Edit Quiz')})


@login_required(login_url='login')
def quiz_delete(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    quiz = get_object_or_404(Quiz, pk=pk)

    if request.method == 'POST':
        quiz.delete()
        messages.success(request, _('Quiz deleted successfully.'))
        return redirect('quiz_list')

    return render(request, 'quiz/confirm_delete.html', {'quiz': quiz})


@login_required(login_url='login')
def quiz_questions(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    quiz = get_object_or_404(Quiz, pk=pk)
    questions = Question.objects.filter(quiz=quiz)

    context = {
        'quiz': quiz,
        'questions': questions,
        'question_count': questions.count(),
    }
    return render(request, 'quiz/questions.html', context)


@login_required(login_url='login')
def question_create(request, quiz_pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    quiz = get_object_or_404(Quiz, pk=quiz_pk)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            messages.success(request, _('Question added successfully.'))
            return redirect('quiz_questions', pk=quiz.pk)
    else:
        form = QuestionForm()

    question_count = Question.objects.filter(quiz=quiz).count()
    return render(request, 'quiz/question_form.html', {
        'form': form, 'quiz': quiz,
        'question_count': question_count,
        'title': _('Add Question'),
    })


@login_required(login_url='login')
def question_edit(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    question = get_object_or_404(Question, pk=pk)

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, _('Question updated successfully.'))
            return redirect('quiz_questions', pk=question.quiz.pk)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'quiz/question_form.html', {
        'form': form, 'quiz': question.quiz, 'title': _('Edit Question')
    })


@login_required(login_url='login')
def question_delete(request, pk):
    if is_student_user(request.user):
        return redirect('student_dashboard')

    question = get_object_or_404(Question, pk=pk)
    quiz_pk = question.quiz.pk

    if request.method == 'POST':
        question.delete()
        messages.success(request, _('Question deleted successfully.'))
        return redirect('quiz_questions', pk=quiz_pk)

    return render(request, 'quiz/question_confirm_delete.html', {'question': question})


# ---------------------------------------------------------------------------
# Quiz taking (student only)
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def quiz_take(request, pk):
    # Only students can take quizzes
    student = get_student_for_user(request.user)
    if not student:
        messages.error(request, _('Only students can take quizzes.'))
        return redirect('quiz_list')

    if student.status != 'active':
        messages.error(request, _('Your account is inactive.'))
        return redirect('student_dashboard')

    quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
    questions = Question.objects.filter(quiz=quiz).order_by('id')

    if questions.count() == 0:
        messages.error(request, _('This quiz has no questions yet.'))
        return redirect('quiz_list')

    if request.method == 'POST':
        # Prevent duplicate submission using session token
        submission_token = request.POST.get('submission_token')
        session_token_key = f'quiz_{quiz.pk}_token'

        if session_token_key in request.session:
            if request.session[session_token_key] == submission_token:
                # Token matches — valid first submission, clear it
                del request.session[session_token_key]
            else:
                # Token mismatch or already used — duplicate submission
                messages.warning(request, _('Quiz already submitted.'))
                return redirect('student_dashboard')
        else:
            messages.warning(request, _('Invalid submission. Please start the quiz again.'))
            return redirect('quiz_list')

        with transaction.atomic():
            quiz_result = QuizResult.objects.create(
                student=student,
                quiz=quiz,
                time_taken=max(0, int(request.POST.get('time_taken', 0))),
            )

            correct_count = 0
            wrong_count = 0
            unanswered_count = 0

            for question in questions:
                selected_option = request.POST.get(f'question_{question.id}', 'unanswered')
                if selected_option not in ('A', 'B', 'C', 'D'):
                    selected_option = 'unanswered'

                # Server-side scoring: never trust client-submitted correctness
                is_correct = (selected_option == question.correct_option)

                if selected_option == 'unanswered':
                    unanswered_count += 1
                elif is_correct:
                    correct_count += 1
                else:
                    wrong_count += 1

                StudentAnswer.objects.create(
                    quiz_result=quiz_result,
                    question=question,
                    selected_option=selected_option,
                    is_correct=is_correct,
                )

            total_possible = quiz.get_total_marks()
            quiz_result.correct_answers = correct_count
            quiz_result.wrong_answers = wrong_count
            quiz_result.unanswered = unanswered_count
            quiz_result.total_marks = Decimal(correct_count) * Decimal(quiz.marks_per_question)
            quiz_result.percentage = (
                (quiz_result.total_marks / Decimal(total_possible)) * 100
                if total_possible > 0 else Decimal(0)
            )
            quiz_result.passed = quiz_result.percentage >= quiz.passing_percentage
            quiz_result.save()

        _update_student_progress(student)
        messages.success(request, _('Quiz submitted successfully!'))
        return redirect('quiz_result', pk=quiz_result.pk)

    # GET — show quiz; generate a one-time submission token
    import uuid as _uuid
    token = str(_uuid.uuid4())
    session_token_key = f'quiz_{quiz.pk}_token'
    request.session[session_token_key] = token

    context = {
        'quiz': quiz,
        'questions': questions,
        'question_count': questions.count(),
        'submission_token': token,
        'student': student,
    }
    return render(request, 'quiz/take.html', context)


# ---------------------------------------------------------------------------
# Quiz results — IDOR-protected
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def quiz_result(request, pk):
    result = get_object_or_404(QuizResult, pk=pk)

    # IDOR protection: students can only view their OWN results
    if is_student_user(request.user):
        student = get_student_for_user(request.user)
        if result.student != student:
            raise Http404

    student_answers = StudentAnswer.objects.filter(
        quiz_result=result
    ).select_related('question').order_by('question__id')

    context = {
        'quiz_result': result,
        'student_answers': student_answers,
        'time_taken_formatted': get_formatted_time(result.time_taken),
        'is_student_view': is_student_user(request.user),
    }
    return render(request, 'quiz/result.html', context)


@login_required(login_url='login')
def quiz_result_pdf(request, pk):
    result = get_object_or_404(QuizResult, pk=pk)

    # IDOR protection
    if is_student_user(request.user):
        student = get_student_for_user(request.user)
        if result.student != student:
            raise Http404

    return generate_pdf_result(result)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@login_required(login_url='login')
def analytics(request):
    if is_student_user(request.user):
        # Student sees their own analytics
        student = get_student_for_user(request.user)
        quiz_results = QuizResult.objects.filter(student=student)
        total_attempts = quiz_results.count()
        avg_score = quiz_results.aggregate(avg=Avg('percentage'))['avg'] or 0
        best_score = quiz_results.aggregate(best=Max('percentage'))['best'] or 0
        passed_count = quiz_results.filter(passed=True).count()
        failed_count = quiz_results.filter(passed=False).count()
        quiz_performance = []
        context = {
            'total_attempts': total_attempts,
            'avg_score': round(avg_score, 2),
            'best_score': round(best_score, 2),
            'passed_count': passed_count,
            'failed_count': failed_count,
            'quiz_performance': quiz_performance,
            'is_student_view': True,
            'student': student,
        }
    else:
        total_attempts = QuizResult.objects.count()
        avg_score = QuizResult.objects.aggregate(avg=Avg('percentage'))['avg'] or 0
        best_score = QuizResult.objects.aggregate(best=Max('percentage'))['best'] or 0
        passed_count = QuizResult.objects.filter(passed=True).count()
        failed_count = QuizResult.objects.filter(passed=False).count()
        quiz_performance = Quiz.objects.annotate(
            avg_percentage=Avg('results__percentage'),
            attempt_count=Count('results')
        ).filter(results__isnull=False)

        context = {
            'total_attempts': total_attempts,
            'avg_score': round(avg_score, 2),
            'best_score': round(best_score, 2),
            'passed_count': passed_count,
            'failed_count': failed_count,
            'quiz_performance': quiz_performance,
        }

    return render(request, 'analytics.html', context)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _update_student_progress(student):
    """Recalculate and persist student progress after a quiz attempt."""
    quiz_results = QuizResult.objects.filter(student=student)

    avg_score = quiz_results.aggregate(avg=Avg('percentage'))['avg'] or 0
    # Fix Bug 9: use Max, not Avg for best_score
    best_score = quiz_results.aggregate(best=Max('percentage'))['best'] or 0

    if quiz_results.count() > 1:
        first_result = quiz_results.order_by('taken_date').first()
        recent_result = quiz_results.order_by('-taken_date').first()
        if first_result.percentage > 0:
            improvement = float(
                (recent_result.percentage - first_result.percentage) / first_result.percentage * 100
            )
        else:
            improvement = 0
    else:
        improvement = 0

    Progress.objects.update_or_create(
        student=student,
        defaults={
            'total_tests_taken': quiz_results.count(),
            'average_score': Decimal(str(avg_score)),
            'best_score': Decimal(str(best_score)),
            'improvement_percentage': Decimal(str(round(improvement, 2))),
        }
    )


# Keep old name for compatibility
def update_student_progress(student):
    _update_student_progress(student)
