from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Student, Attendance


class Command(BaseCommand):
    help = 'Auto-mark active students as Absent if they have no attendance record for today by 06:00 PM'

    def handle(self, *args, **options):
        today = timezone.localdate()
        active_students = Student.objects.filter(status='active')

        absent_count = 0
        already_marked = 0

        for student in active_students:
            record, created = Attendance.objects.get_or_create(
                student=student,
                date=today,
                defaults={
                    'status': 'absent',
                    'auto_marked': True,
                    'remarks': 'Auto-marked absent (No login between 09:00 AM - 06:00 PM)'
                }
            )

            if created:
                absent_count += 1
            else:
                already_marked += 1

        self.stdout.write(self.style.SUCCESS(
            f'Auto-absent check completed for {today}: {absent_count} students marked Absent, {already_marked} already had records.'
        ))
