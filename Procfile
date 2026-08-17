release: python manage.py migrate --noinput
web: gunicorn student_management.wsgi:application --log-file -
