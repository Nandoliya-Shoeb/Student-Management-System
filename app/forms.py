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
        label=_('Login Password (લૉગિન પાસવર્ડ)'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Default: GR.NO (ખાલી રાખશો તો GR.NO જ પાસવર્ડ રહેશે)'),
        }),
        help_text=_('ખાલી રાખશો તો વિદ્યાર્થીનો GR.NO જ તેમનો પાસવર્ડ રહેશે.')
    )
    password_confirm = forms.CharField(
        label=_('Confirm Password (કન્ફર્મ પાસવર્ડ)'),
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _(' Repeat password / રિપીટ પાસવર્ડ'),
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get('password')
        confirm = cleaned_data.get('password_confirm')
        if pwd and confirm and pwd != confirm:
            raise forms.ValidationError(_('Passwords do not match.'))
        if pwd and not confirm:
            raise forms.ValidationError(_('Please confirm your password.'))
        return cleaned_data


class StudentForm(forms.ModelForm):
    parent_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
        label=_('Parent / Guardian Name'),
    )

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
                'placeholder': '626',
            }),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional', 'required': False}),
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
        student_id = self.cleaned_data.get('student_id', '').strip()
        if not student_id:
            raise forms.ValidationError(_('GR.NO is required.'))
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
    due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label=_('Due Date'),
    )
    fee_month = forms.ChoiceField(
        choices=[
            (1, 'January (જાન્યુઆરી)'),
            (2, 'February (ફેબ્રુઆરી)'),
            (3, 'March (માર્ચ)'),
            (4, 'April (એપ્રિલ)'),
            (5, 'May (મે)'),
            (6, 'June (જૂન)'),
            (7, 'July (જુલાઈ)'),
            (8, 'August (ઓગસ્ટ)'),
            (9, 'September (સપ્ટેમ્બર)'),
            (10, 'October (ઓક્ટોબર)'),
            (11, 'November (નવેમ્બર)'),
            (12, 'December (ડિસેમ્બર)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Fee Month (ક્યા મહિનાની ફી?)'),
    )
    fee_year = forms.IntegerField(
        min_value=2020,
        max_value=2040,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label=_('Fee Year (વર્ષ)'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order students by class and numeric student_id
        try:
            from django.db.models.functions import Cast
            from django.db.models import IntegerField
            qs = Student.objects.filter(status='active').annotate(
                num_id=Cast('student_id', IntegerField())
            ).order_by('class_field', 'num_id')
        except Exception:
            qs = Student.objects.filter(status='active').order_by('class_field', 'student_id')

        self.fields['student'].queryset = qs
        self.fields['student'].label_from_instance = lambda obj: f"[{obj.get_class_field_display()}] {obj.student_id} - {obj.name}"

    class Meta:
        model = Fee
        fields = [
            'student', 'fee_month', 'fee_year', 'amount', 'fee_type', 'status',
            'due_date', 'payment_date', 'payment_method',
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'fee_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
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
    CLASS_CHOICES = [
        ('8', _('Grade 8 (ધોરણ ૮)')),
        ('7', _('Grade 7 (ધોરણ ૭)')),
        ('6', _('Grade 6 (ધોરણ ૬)')),
        ('5', _('Grade 5 (ધોરણ ૫)')),
    ]

    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls, .csv, .txt'}),
        label=_('Select Excel / CSV File'),
    )
    default_class = forms.ChoiceField(
        choices=CLASS_CHOICES,
        initial='6',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Select Class / Grade (ધોરણ પસંદ કરો)'),
        help_text=_('This class will be assigned to students if not specified in the file.')
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        valid_extensions = ('.xlsx', '.xls', '.csv', '.txt')
        if not csv_file.name.lower().endswith(valid_extensions):
            raise forms.ValidationError(_('Please upload a valid Excel (.xlsx, .xls) or CSV file.'))
        if csv_file.size > 20 * 1024 * 1024:
            raise forms.ValidationError(_('File size exceeds 20MB limit.'))
        return csv_file

