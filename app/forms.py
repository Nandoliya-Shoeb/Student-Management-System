from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Student, Attendance, Fee, Quiz, Question
import csv
import io


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        label=_('Username / Student ID'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('admin or STU001'),
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password'),
            'autocomplete': 'current-password',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'password')


class StudentUserForm(forms.Form):
    """Used when creating a new student to set their login password."""
    password = forms.CharField(
        label=_('Login Password'),
        min_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Minimum 6 characters'),
        }),
        help_text=_('Student will use their Student ID + this password to login.')
    )
    password_confirm = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Repeat password'),
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('password')
        confirm = cleaned_data.get('password_confirm')
        if pwd and confirm and pwd != confirm:
            raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned_data


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'student_id', 'name', 'parent_name', 'parent_mobile',
            'email', 'phone', 'photo', 'class_field', 'address',
            'joining_date', 'status',
        ]
        widgets = {
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'STU001',
                'style': 'text-transform: uppercase;',
                'oninput': 'this.value = this.value.toUpperCase()'
            }),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'class_field': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id', '').strip().upper()
        if not student_id:
            raise forms.ValidationError(_('Student ID is required.'))
        return student_id


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['status', 'remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BulkAttendanceForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('Date')
    )
    action = forms.ChoiceField(
        choices=[
            ('present', _('Mark All Present')),
            ('absent', _('Mark All Absent')),
            ('leave', _('Mark All Leave')),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Action')
    )


class FeeForm(forms.ModelForm):
    class Meta:
        model = Fee
        fields = [
            'student', 'amount', 'fee_type', 'status',
            'due_date', 'payment_date', 'payment_method',
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fee_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = [
            'title', 'description', 'total_questions',
            'marks_per_question', 'passing_percentage', 'is_active',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'total_questions': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'marks_per_question': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_text', 'option_a', 'option_b', 'option_c',
            'option_d', 'correct_option', 'explanation',
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_option': forms.Select(attrs={'class': 'form-select'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        label=_('CSV File'),
        help_text=_(
            'CSV columns: student_id, name, parent_name, parent_mobile, '
            'email, phone, class_field, address, joining_date'
        )
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError(_('Please upload a CSV file.'))
        if csv_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('File size exceeds 10MB limit.'))
        return csv_file
