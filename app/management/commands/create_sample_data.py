from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from app.models import Student, Attendance, Fee, Quiz, Question, QuizResult, StudentAnswer, Progress


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        # Clear existing data
        Student.objects.all().delete()
        Quiz.objects.all().delete()

        self.stdout.write('Creating sample students...')
        
        # Create sample students
        students_data = [
            ('STU001', 'Rahul Patel', 'Mr. Patel', '9876543210', 'rahul@example.com', '5'),
            ('STU002', 'Priya Shah', 'Mrs. Shah', '9876543211', 'priya@example.com', '6'),
            ('STU003', 'Arjun Kumar', 'Mr. Kumar', '9876543212', 'arjun@example.com', '7'),
            ('STU004', 'Neha Singh', 'Mrs. Singh', '9876543213', 'neha@example.com', '8'),
            ('STU005', 'Aditya Verma', 'Mr. Verma', '9876543214', 'aditya@example.com', '5'),
        ]

        students = []
        for student_id, name, parent_name, parent_mobile, email, class_field in students_data:
            student = Student.objects.create(
                student_id=student_id,
                name=name,
                parent_name=parent_name,
                parent_mobile=parent_mobile,
                email=email,
                phone=parent_mobile,
                class_field=class_field,
                address='123 Main Street',
                joining_date=datetime.now().date() - timedelta(days=365),
                status='active'
            )
            students.append(student)

        self.stdout.write('Creating sample attendance records...')
        
        # Create sample attendance
        today = datetime.now().date()
        for student in students:
            for days_back in range(1, 31):
                date = today - timedelta(days=days_back)
                status = 'present' if (days_back % 3) != 0 else 'absent'
                Attendance.objects.create(
                    student=student,
                    date=date,
                    status=status,
                    remarks=''
                )

        self.stdout.write('Creating sample fees...')
        
        # Create sample fees
        for student in students:
            for month in range(1, 4):
                Fee.objects.create(
                    student=student,
                    amount=Decimal('5000.00'),
                    fee_type='monthly',
                    status='paid' if month <= 2 else 'pending',
                    due_date=today + timedelta(days=30),
                    payment_date=today - timedelta(days=60) if month <= 2 else None,
                    payment_method='cash' if month <= 2 else None
                )

        self.stdout.write('Creating sample quiz...')
        
        # Create sample quiz
        quiz = Quiz.objects.create(
            title='General Knowledge Quiz',
            description='A quiz about general knowledge topics',
            total_questions=20,
            marks_per_question=1,
            passing_percentage=50,
            is_active=True
        )

        self.stdout.write('Creating sample questions...')
        
        # Create sample questions
        questions_data = [
            ('What is the capital of India?', 'New Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'A', 'The capital of India is New Delhi.'),
            ('Which planet is known as the Red Planet?', 'Mars', 'Venus', 'Jupiter', 'Saturn', 'A', 'Mars is called the Red Planet due to its reddish appearance.'),
            ('Who wrote the Ramayana?', 'Valmiki', 'Vyasa', 'Tulsidas', 'Kalidasa', 'A', 'Valmiki is credited with writing the Ramayana.'),
            ('What is the largest ocean in the world?', 'Pacific Ocean', 'Atlantic Ocean', 'Indian Ocean', 'Arctic Ocean', 'A', 'The Pacific Ocean is the largest ocean.'),
            ('Which country is home to the Great Wall?', 'China', 'India', 'Japan', 'Korea', 'A', 'The Great Wall is located in China.'),
            ('What is the smallest unit of life?', 'Cell', 'Atom', 'Molecule', 'Organ', 'A', 'The cell is the smallest unit of life.'),
            ('How many continents are there?', '7', '5', '6', '8', 'A', 'There are 7 continents on Earth.'),
            ('What is the chemical symbol for gold?', 'Au', 'Ag', 'Fe', 'Cu', 'A', 'Gold has the chemical symbol Au.'),
            ('Which is the longest river in the world?', 'Nile', 'Amazon', 'Yangtze', 'Mississippi', 'A', 'The Nile is the longest river in the world.'),
            ('What year did the Titanic sink?', '1912', '1910', '1915', '1920', 'A', 'The Titanic sank in 1912.'),
            ('How many strings does a violin have?', '4', '6', '8', '10', 'A', 'A violin typically has 4 strings.'),
            ('What is the speed of light?', '300,000 km/s', '150,000 km/s', '450,000 km/s', '200,000 km/s', 'A', 'The speed of light is approximately 300,000 km/s.'),
            ('Which element has the atomic number 1?', 'Hydrogen', 'Helium', 'Lithium', 'Beryllium', 'A', 'Hydrogen has atomic number 1.'),
            ('What is the capital of France?', 'Paris', 'Lyon', 'Marseille', 'Toulouse', 'A', 'Paris is the capital of France.'),
            ('How many sides does a hexagon have?', '6', '5', '7', '8', 'A', 'A hexagon has 6 sides.'),
            ('What is the boiling point of water?', '100°C', '90°C', '110°C', '80°C', 'A', 'Water boils at 100°C at sea level.'),
            ('Who painted the Mona Lisa?', 'Leonardo da Vinci', 'Michelangelo', 'Raphael', 'Donatello', 'A', 'Leonardo da Vinci painted the Mona Lisa.'),
            ('What is the currency of Japan?', 'Yen', 'Won', 'Baht', 'Rupee', 'A', 'The currency of Japan is the Yen.'),
            ('How many bones are in the human body?', '206', '180', '230', '250', 'A', 'The human body has 206 bones.'),
            ('What is the largest animal in the world?', 'Blue Whale', 'Elephant', 'Giraffe', 'Hippopotamus', 'A', 'The Blue Whale is the largest animal in the world.'),
        ]

        for i, (q_text, opt_a, opt_b, opt_c, opt_d, correct, explanation) in enumerate(questions_data):
            Question.objects.create(
                quiz=quiz,
                question_text=q_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=correct,
                explanation=explanation
            )

        self.stdout.write('Creating sample quiz results...')
        
        # Create sample quiz results for each student
        for student in students:
            for attempt in range(1, 3):
                result = QuizResult.objects.create(
                    student=student,
                    quiz=quiz,
                    correct_answers=15 + attempt,
                    wrong_answers=5 - attempt,
                    unanswered=0,
                    total_marks=20,
                    percentage=int((15 + attempt) * 100 / 20),
                    passed=True if (15 + attempt) >= 10 else False,
                    taken_date=today - timedelta(days=5 * attempt),
                    time_taken=2700  # 45 minutes in seconds
                )

                # Create sample answers
                questions = quiz.questions.all()
                for idx, question in enumerate(questions):
                    is_correct = idx < (15 + attempt)
                    selected = question.correct_option if is_correct else ['B', 'C', 'D', 'A'][idx % 4]
                    StudentAnswer.objects.create(
                        quiz_result=result,
                        question=question,
                        selected_option=selected,
                        is_correct=is_correct
                    )

        self.stdout.write('Creating sample progress records...')
        
        # Create sample progress
        for student in students:
            Progress.objects.create(
                student=student,
                total_tests_taken=2,
                average_score=Decimal('75.00'),
                best_score=Decimal('80.00'),
                improvement_percentage=Decimal('10.00')
            )

        self.stdout.write(self.style.SUCCESS('Successfully created sample data!'))
