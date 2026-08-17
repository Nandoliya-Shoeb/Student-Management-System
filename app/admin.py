from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Student, Attendance, Fee, Quiz, Question, QuizResult, StudentAnswer, Progress


class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fields = ('student_id', 'name', 'class_field', 'status')
    extra = 0


class CustomUserAdmin(UserAdmin):
    inlines = (StudentInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'class_field', 'status', 'has_login', 'joining_date')
    list_filter = ('class_field', 'status')
    search_fields = ('student_id', 'name', 'email')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Account'), {'fields': ('user', 'student_id', 'status')}),
        (_('Personal Info'), {'fields': ('name', 'email', 'phone', 'photo', 'address')}),
        (_('Academic'), {'fields': ('class_field', 'joining_date')}),
        (_('Family'), {'fields': ('parent_name', 'parent_mobile')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def has_login(self, obj):
        return obj.user is not None
    has_login.boolean = True
    has_login.short_description = _('Has Login')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'remarks')
    list_filter = ('status', 'date')
    search_fields = ('student__name', 'student__student_id')
    date_hierarchy = 'date'
    list_per_page = 50


@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'fee_type', 'status', 'due_date', 'receipt_number')
    list_filter = ('status', 'fee_type')
    search_fields = ('student__name', 'receipt_number')
    readonly_fields = ('receipt_number', 'created_at', 'updated_at')
    list_per_page = 25


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ('question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'total_questions', 'marks_per_question', 'passing_percentage', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title',)
    inlines = [QuestionInline]
    list_per_page = 20


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question_text_short', 'correct_option')
    list_filter = ('quiz', 'correct_option')
    search_fields = ('question_text', 'quiz__title')
    list_per_page = 30

    def question_text_short(self, obj):
        return obj.question_text[:60] + '...' if len(obj.question_text) > 60 else obj.question_text
    question_text_short.short_description = _('Question')


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct')
    can_delete = False


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'correct_answers', 'percentage', 'passed', 'taken_date')
    list_filter = ('passed', 'quiz')
    search_fields = ('student__name', 'quiz__title')
    readonly_fields = ('taken_date',)
    inlines = [StudentAnswerInline]
    list_per_page = 25


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'total_tests_taken', 'average_score', 'best_score', 'last_updated')
    search_fields = ('student__name',)
    readonly_fields = ('last_updated',)
