from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import datetime

from .models import Student, Attendance, Fee, Quiz, Question, QuizResult, StudentAnswer, Progress
from .utils import calculate_attendance_percentage, calculate_student_performance


class StudentModelTest(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            student_id='STU001',
            name='Rahul Patel',
            parent_name='Mr. Patel',
            parent_mobile='9876543210',
            email='rahul@example.com',
            phone='9876543210',
            class_field='5',
            address='123 Main Street',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )

    def test_student_creation(self):
        self.assertEqual(self.student.name, 'Rahul Patel')
        self.assertEqual(self.student.student_id, 'STU001')
        self.assertEqual(self.student.class_field, '5')

    def test_student_id_auto_uppercase(self):
        stu = Student.objects.create(
            student_id='stu999',
            name='Test Upper',
            parent_name='Parent',
            parent_mobile='9876543210',
            phone='9876543210',
            class_field='5',
            address='123 Main Street',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )
        self.assertEqual(stu.student_id, 'STU999')

    def test_duplicate_student_id(self):
        with self.assertRaises(Exception):
            Student.objects.create(
                student_id='STU001',
                name='Another Student',
                parent_name='Parent',
                parent_mobile='9876543210',
                email='test@example.com',
                phone='9876543210',
                class_field='6',
                address='123 Street',
                joining_date=datetime.date(2026, 1, 1)
            )


class AttendanceTest(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            student_id='STU001',
            name='Rahul Patel',
            parent_name='Mr. Patel',
            parent_mobile='9876543210',
            email='rahul@example.com',
            phone='9876543210',
            class_field='5',
            address='123 Main Street',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )
        self.date = datetime.date(2026, 8, 16)

    def test_attendance_creation(self):
        attendance = Attendance.objects.create(
            student=self.student,
            date=self.date,
            status='present',
            remarks=''
        )
        self.assertEqual(attendance.status, 'present')
        self.assertEqual(attendance.student, self.student)

    def test_duplicate_attendance_protection(self):
        Attendance.objects.create(
            student=self.student,
            date=self.date,
            status='present'
        )
        with self.assertRaises(Exception):
            Attendance.objects.create(
                student=self.student,
                date=self.date,
                status='absent'
            )

    def test_attendance_percentage_calc(self):
        Attendance.objects.create(student=self.student, date=datetime.date(2026, 8, 1), status='present')
        Attendance.objects.create(student=self.student, date=datetime.date(2026, 8, 2), status='present')
        Attendance.objects.create(student=self.student, date=datetime.date(2026, 8, 3), status='absent')
        Attendance.objects.create(student=self.student, date=datetime.date(2026, 8, 4), status='leave')

        pct = calculate_attendance_percentage(self.student)
        # 2 present out of 4 total = 50.0%
        self.assertEqual(pct, 50.0)


class FeeTest(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            student_id='STU001',
            name='Rahul Patel',
            parent_name='Mr. Patel',
            parent_mobile='9876543210',
            email='rahul@example.com',
            phone='9876543210',
            class_field='5',
            address='123 Main Street',
            joining_date=datetime.date(2026, 1, 1)
        )

    def test_fee_creation(self):
        fee = Fee.objects.create(
            student=self.student,
            amount=Decimal('5000.00'),
            fee_type='monthly',
            status='pending',
            due_date=datetime.date(2026, 8, 20)
        )
        self.assertEqual(fee.status, 'pending')
        self.assertIsNotNone(fee.receipt_number)


class StudentAuthAndSecurityTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@school.com', password='adminpassword'
        )

        # Student 1 (STU001)
        self.user1 = User.objects.create_user(
            username='STU001', password='stu1password', first_name='Rahul Patel'
        )
        self.student1 = Student.objects.create(
            user=self.user1,
            student_id='STU001',
            name='Rahul Patel',
            parent_name='Mr. Patel',
            parent_mobile='9876543210',
            email='rahul@example.com',
            phone='9876543210',
            class_field='5',
            address='123 Main Street',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )

        # Student 2 (STU002)
        self.user2 = User.objects.create_user(
            username='STU002', password='stu2password', first_name='Priya Shah'
        )
        self.student2 = Student.objects.create(
            user=self.user2,
            student_id='STU002',
            name='Priya Shah',
            parent_name='Mr. Shah',
            parent_mobile='9876543211',
            email='priya@example.com',
            phone='9876543211',
            class_field='6',
            address='456 Cross Street',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )

        # Create a Quiz
        self.quiz = Quiz.objects.create(
            title='General Knowledge',
            description='Basic test',
            total_questions=2,
            marks_per_question=5,
            passing_percentage=50,
            is_active=True
        )
        self.q1 = Question.objects.create(
            quiz=self.quiz,
            question_text='Capital of Gujarat?',
            option_a='Ahmedabad', option_b='Gandhinagar', option_c='Surat', option_d='Vadodara',
            correct_option='B'
        )
        self.q2 = Question.objects.create(
            quiz=self.quiz,
            question_text='Sun rises in the?',
            option_a='East', option_b='West', option_c='North', option_d='South',
            correct_option='A'
        )

        # Create Result for Student 2
        self.result2 = QuizResult.objects.create(
            student=self.student2,
            quiz=self.quiz,
            correct_answers=2,
            wrong_answers=0,
            unanswered=0,
            total_marks=Decimal('10.00'),
            percentage=Decimal('100.00'),
            passed=True,
            time_taken=120
        )

        # Create Fee for Student 2
        self.fee2 = Fee.objects.create(
            student=self.student2,
            amount=Decimal('4000.00'),
            fee_type='monthly',
            status='paid',
            due_date=datetime.date(2026, 8, 1)
        )

    def test_student_login_with_student_id(self):
        response = self.client.post(reverse('login'), {
            'username': 'STU001',
            'password': 'stu1password'
        })
        self.assertRedirects(response, reverse('student_dashboard'))

    def test_session_expiry_10_hours(self):
        self.client.post(reverse('login'), {
            'username': 'STU001',
            'password': 'stu1password'
        })
        # 10 Hours in seconds = 36000
        self.assertEqual(self.client.session.get_expiry_age(), 10 * 60 * 60)

    def test_student_cannot_access_admin_dashboard(self):
        self.client.login(username='STU001', password='stu1password')
        response = self.client.get(reverse('dashboard'))
        # Should redirect to student dashboard
        self.assertRedirects(response, reverse('student_dashboard'))

    def test_student_cannot_access_other_student_result_idor(self):
        # Student 1 logs in
        self.client.login(username='STU001', password='stu1password')
        # Student 1 tries to view Student 2's result (result2)
        response = self.client.get(reverse('quiz_result', kwargs={'pk': self.result2.pk}))
        # Must return 404
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_other_student_fee_receipt_idor(self):
        self.client.login(username='STU001', password='stu1password')
        response = self.client.get(reverse('fee_pdf_receipt', kwargs={'pk': self.fee2.pk}))
        self.assertEqual(response.status_code, 404)

    def test_quiz_take_and_server_side_scoring(self):
        self.client.login(username='STU001', password='stu1password')

        # GET quiz page to initialize session token
        get_res = self.client.get(reverse('quiz_take', kwargs={'pk': self.quiz.pk}))
        self.assertEqual(get_res.status_code, 200)

        token = self.client.session.get(f'quiz_{self.quiz.pk}_token')
        self.assertIsNotNone(token)

        # POST answers: Q1=B (correct), Q2=C (wrong)
        post_data = {
            'submission_token': token,
            'time_taken': '65',
            f'question_{self.q1.id}': 'B',
            f'question_{self.q2.id}': 'C',
        }
        post_res = self.client.post(reverse('quiz_take', kwargs={'pk': self.quiz.pk}), post_data)
        self.assertEqual(post_res.status_code, 302)

        # Verify created QuizResult
        result = QuizResult.objects.filter(student=self.student1, quiz=self.quiz).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.correct_answers, 1)
        self.assertEqual(result.wrong_answers, 1)
        self.assertEqual(result.unanswered, 0)
        self.assertEqual(result.total_marks, Decimal('5.00')) # 1 * 5
        self.assertEqual(result.percentage, Decimal('50.00')) # 5/10 * 100
        self.assertTrue(result.passed)

        # Student progress should also be updated
        self.student1.refresh_from_db()
        self.assertEqual(self.student1.progress.total_tests_taken, 1)
        self.assertEqual(self.student1.progress.average_score, Decimal('50.00'))

    def test_duplicate_quiz_submission_blocked(self):
        self.client.login(username='STU001', password='stu1password')

        # GET quiz page
        self.client.get(reverse('quiz_take', kwargs={'pk': self.quiz.pk}))
        token = self.client.session.get(f'quiz_{self.quiz.pk}_token')

        post_data = {
            'submission_token': token,
            'time_taken': '30',
            f'question_{self.q1.id}': 'B',
            f'question_{self.q2.id}': 'A',
        }
        # First submission
        self.client.post(reverse('quiz_take', kwargs={'pk': self.quiz.pk}), post_data)
        count_after_first = QuizResult.objects.filter(student=self.student1, quiz=self.quiz).count()
        self.assertEqual(count_after_first, 1)

        # Duplicate submission with same token
        self.client.post(reverse('quiz_take', kwargs={'pk': self.quiz.pk}), post_data)
        count_after_second = QuizResult.objects.filter(student=self.student1, quiz=self.quiz).count()
        self.assertEqual(count_after_second, 1) # Must remain 1


class AttendanceViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@school.com', password='adminpassword'
        )
        self.client.login(username='admin', password='adminpassword')

        self.student = Student.objects.create(
            student_id='STU001',
            name='Rahul Patel',
            parent_name='Mr. Patel',
            parent_mobile='9876543210',
            email='rahul@example.com',
            phone='9876543210',
            class_field='5',
            address='123 Main Street',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )

    def test_attendance_save_and_update(self):
        date_str = '2026-08-16'
        post_data = {
            'date': date_str,
            f'status_{self.student.id}': 'present',
            f'remarks_{self.student.id}': 'On time',
        }
        res = self.client.post(reverse('attendance_save'), post_data)
        self.assertEqual(res.status_code, 302)

        record = Attendance.objects.filter(student=self.student, date=datetime.date(2026, 8, 16)).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, 'present')
        self.assertEqual(record.remarks, 'On time')

        # Update to 'leave'
        post_data[f'status_{self.student.id}'] = 'leave'
        post_data[f'remarks_{self.student.id}'] = 'Sick leave'
        res2 = self.client.post(reverse('attendance_save'), post_data)
        self.assertEqual(res2.status_code, 302)

        record.refresh_from_db()
        self.assertEqual(record.status, 'leave')
        self.assertEqual(record.remarks, 'Sick leave')
        # Ensure only 1 row exists for this date
        self.assertEqual(Attendance.objects.filter(student=self.student, date=datetime.date(2026, 8, 16)).count(), 1)

    def test_attendance_filter_by_class_and_search(self):
        # Create student in Grade 6
        stu6 = Student.objects.create(
            student_id='STU006',
            name='Amit Sharma',
            parent_name='Mr. Sharma',
            parent_mobile='9876543212',
            phone='9876543212',
            class_field='6',
            address='789 Road',
            joining_date=datetime.date(2026, 1, 1),
            status='active'
        )
        # Filter by Grade 5 (should only include Rahul)
        res_class5 = self.client.get(reverse('attendance_list'), {'class': '5'})
        self.assertEqual(res_class5.status_code, 200)
        students_c5 = [item['student'] for item in res_class5.context['attendance_data']]
        self.assertIn(self.student, students_c5)
        self.assertNotIn(stu6, students_c5)

        # Filter by search 'Amit'
        res_search = self.client.get(reverse('attendance_list'), {'search': 'Amit'})
        self.assertEqual(res_search.status_code, 200)
        students_search = [item['student'] for item in res_search.context['attendance_data']]
        self.assertIn(stu6, students_search)
        self.assertNotIn(self.student, students_search)
