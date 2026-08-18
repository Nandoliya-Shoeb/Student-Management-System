from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class Student(models.Model):
    CLASS_CHOICES = [
        ('5', _('Grade 5')),
        ('6', _('Grade 6')),
        ('7', _('Grade 7')),
        ('8', _('Grade 8')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student',
        verbose_name=_('User Account'),
    )
    student_id = models.CharField(max_length=50, unique=True, verbose_name=_('Student ID'))
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    parent_name = models.CharField(max_length=100, verbose_name=_('Parent Name'))
    parent_mobile = models.CharField(max_length=15, verbose_name=_('Parent Mobile'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    phone = models.CharField(max_length=15, verbose_name=_('Phone'))
    photo = models.ImageField(upload_to='student_photos/', null=True, blank=True, verbose_name=_('Photo'))
    class_field = models.CharField(max_length=1, choices=CLASS_CHOICES, verbose_name=_('Class'))
    address = models.TextField(verbose_name=_('Address'))
    joining_date = models.DateField(verbose_name=_('Joining Date'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name=_('Status'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = _('Student')
        verbose_name_plural = _('Students')
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['name']),
        ]
    
    def clean(self):
        if self.student_id:
            self.student_id = self.student_id.strip().upper()

    def save(self, *args, **kwargs):
        if self.student_id:
            self.student_id = self.student_id.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.student_id})"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', _('Present')),
        ('absent', _('Absent')),
        ('leave', _('Leave')),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records', verbose_name=_('Student'))
    date = models.DateField(verbose_name=_('Date'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name=_('Status'))
    remarks = models.TextField(blank=True, verbose_name=_('Remarks'))
    # Auto attendance fields
    login_time = models.TimeField(null=True, blank=True, verbose_name=_('Login Time'))
    auto_marked = models.BooleanField(default=False, verbose_name=_('Auto Marked'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date']
        verbose_name = _('Attendance')
        verbose_name_plural = _('Attendance')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['student', 'date']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"


class Fee(models.Model):
    FEE_TYPE_CHOICES = [
        ('monthly', _('Monthly')),
        ('exam', _('Exam')),
        ('project', _('Project')),
    ]
    
    STATUS_CHOICES = [
        ('paid', _('Paid')),
        ('pending', _('Pending')),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('online', _('Online')),
        ('check', _('Check')),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fees', verbose_name=_('Student'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name=_('Amount'))
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, verbose_name=_('Fee Type'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name=_('Status'))
    due_date = models.DateField(verbose_name=_('Due Date'))
    payment_date = models.DateField(null=True, blank=True, verbose_name=_('Payment Date'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, verbose_name=_('Payment Method'))
    receipt_number = models.CharField(max_length=50, unique=True, verbose_name=_('Receipt Number'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date']
        verbose_name = _('Fee')
        verbose_name_plural = _('Fees')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['student', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.amount} - {self.fee_type}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"REC-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)


class Quiz(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    description = models.TextField(verbose_name=_('Description'))
    total_questions = models.IntegerField(default=20, validators=[MinValueValidator(1)], verbose_name=_('Total Questions'))
    marks_per_question = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name=_('Marks per Question'))
    passing_percentage = models.IntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name=_('Passing Percentage'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Quiz')
        verbose_name_plural = _('Quizzes')
    
    def __str__(self):
        return self.title
    
    def get_total_marks(self):
        return self.total_questions * self.marks_per_question


class Question(models.Model):
    OPTION_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions', verbose_name=_('Quiz'))
    question_text = models.TextField(verbose_name=_('Question Text'))
    option_a = models.CharField(max_length=500, verbose_name=_('Option A'))
    option_b = models.CharField(max_length=500, verbose_name=_('Option B'))
    option_c = models.CharField(max_length=500, verbose_name=_('Option C'))
    option_d = models.CharField(max_length=500, verbose_name=_('Option D'))
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES, verbose_name=_('Correct Option'))
    explanation = models.TextField(blank=True, verbose_name=_('Explanation'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['quiz', 'id']
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.id}"
    
    def get_option_by_label(self, label):
        if label == 'A':
            return self.option_a
        elif label == 'B':
            return self.option_b
        elif label == 'C':
            return self.option_c
        elif label == 'D':
            return self.option_d
        return None


class QuizResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_results', verbose_name=_('Student'))
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results', verbose_name=_('Quiz'))
    correct_answers = models.IntegerField(default=0, verbose_name=_('Correct Answers'))
    wrong_answers = models.IntegerField(default=0, verbose_name=_('Wrong Answers'))
    unanswered = models.IntegerField(default=0, verbose_name=_('Unanswered'))
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Total Marks'))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Percentage'))
    passed = models.BooleanField(default=False, verbose_name=_('Passed'))
    taken_date = models.DateTimeField(auto_now_add=True)
    time_taken = models.IntegerField(help_text=_('Time in seconds'), verbose_name=_('Time Taken'))
    
    class Meta:
        ordering = ['-taken_date']
        verbose_name = _('Quiz Result')
        verbose_name_plural = _('Quiz Results')
        indexes = [
            models.Index(fields=['student', '-taken_date']),
            models.Index(fields=['quiz', '-taken_date']),
        ]
    
    def __str__(self):
        return f"{self.student.name} - {self.quiz.title} - {self.percentage}%"


class StudentAnswer(models.Model):
    OPTION_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('unanswered', _('Unanswered')),
    ]
    
    quiz_result = models.ForeignKey(QuizResult, on_delete=models.CASCADE, related_name='student_answers', verbose_name=_('Quiz Result'))
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name=_('Question'))
    selected_option = models.CharField(max_length=20, choices=OPTION_CHOICES, default='unanswered', verbose_name=_('Selected Option'))
    is_correct = models.BooleanField(default=False, verbose_name=_('Is Correct'))
    
    class Meta:
        unique_together = ('quiz_result', 'question')
        verbose_name = _('Student Answer')
        verbose_name_plural = _('Student Answers')
    
    def __str__(self):
        return f"{self.quiz_result.student.name} - Q{self.question.id}"


class Progress(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='progress', verbose_name=_('Student'))
    total_tests_taken = models.IntegerField(default=0, verbose_name=_('Total Tests Taken'))
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Average Score'))
    best_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Best Score'))
    improvement_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Improvement Percentage'))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_('Last Updated'))
    
    class Meta:
        verbose_name = _('Progress')
        verbose_name_plural = _('Progress')
    
    def __str__(self):
        return f"{self.student.name} - Progress"
