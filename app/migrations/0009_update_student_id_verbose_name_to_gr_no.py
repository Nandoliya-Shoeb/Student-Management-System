from django.db import migrations, models


def strip_std_prefixes(apps, schema_editor):
    Student = apps.get_model('app', 'Student')
    for student in Student.objects.all():
        old_id = student.student_id or ''
        clean_id = old_id.upper().replace('STD', '').replace('STU', '').replace('GR', '').strip()
        if clean_id and clean_id != old_id:
            if not Student.objects.filter(student_id=clean_id).exclude(id=student.id).exists():
                student.student_id = clean_id
                student.save(update_fields=['student_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_make_student_fields_flexible'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='student_id',
            field=models.CharField(max_length=50, unique=True, verbose_name='GR.NO'),
        ),
        migrations.RunPython(strip_std_prefixes, reverse_code=migrations.RunPython.noop),
    ]

