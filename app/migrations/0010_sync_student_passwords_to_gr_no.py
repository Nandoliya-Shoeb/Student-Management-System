from django.db import migrations
from django.contrib.auth.hashers import make_password


def set_passwords_to_gr_no(apps, schema_editor):
    Student = apps.get_model('app', 'Student')
    User = apps.get_model('auth', 'User')

    for student in Student.objects.all():
        gr_no = (student.student_id or '').strip()
        if not gr_no:
            continue
        if student.user:
            user = student.user
            user.password = make_password(gr_no)
            user.save(update_fields=['password'])
        else:
            user = User.objects.filter(username=gr_no).first()
            if not user:
                user = User.objects.create(
                    username=gr_no,
                    password=make_password(gr_no),
                    first_name=(student.name or '')[:30],
                    is_active=True,
                )
            else:
                user.password = make_password(gr_no)
                user.save(update_fields=['password'])
            student.user = user
            student.save(update_fields=['user'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_update_student_id_verbose_name_to_gr_no'),
    ]

    operations = [
        migrations.RunPython(set_passwords_to_gr_no, reverse_code=migrations.RunPython.noop),
    ]
