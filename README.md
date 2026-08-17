# Student Management System

A comprehensive Django-based Student Management System with bilingual support (English + Gujarati).

## Features

- **Authentication**: Secure login/logout with session-based authentication
- **Student Management**: CRUD operations, search, filter, bulk CSV import
- **Attendance Tracking**: Date-based marking, bulk actions, attendance history, percentage calculation
- **Fee Management**: Payment tracking, receipt generation, pending fee reports
- **Quiz System**: Create quizzes, manage questions, take quizzes with timer, server-side scoring
- **Results & Analytics**: View quiz results, performance tracking, historical data analysis
- **Reports**: PDF and Excel export for attendance, fees, and results
- **Bilingual Support**: Complete English + Gujarati interface with language persistence
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Prerequisites

- Python 3.11+
- pip (Python package installer)
- Virtual environment (recommended)

## Installation

1. **Clone or navigate to the project directory**:
```bash
cd student_management
```

2. **Create a virtual environment** (optional but recommended):
```bash
python -m venv venv
# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Create a `.env` file** (copy from `.env.example`):
```bash
cp .env.example .env
```

5. **Run migrations**:
```bash
python manage.py migrate
```

6. **Create a superuser** (admin account):
```bash
python manage.py createsuperuser
# Enter username, email, and password when prompted
# Default credentials for testing:
# Username: admin
# Password: password
```

7. **Load sample data** (optional):
```bash
python manage.py create_sample_data
```

8. **Run the development server**:
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000`

## Default Login Credentials

- **Username**: admin
- **Password**: password

## Using the Application

### Login
- Navigate to `http://127.0.0.1:8000`
- Enter admin credentials or other user credentials
- Click "Login"

### Language Switching
- Look for the language dropdown in the navbar (top right)
- Select "English" or "ગુજરાતી" (Gujarati)
- The interface will immediately switch to the selected language
- Language preference persists across page navigations

### Admin Dashboard
- View key statistics: total students, pending fees, attendance percentage, quiz performance
- Quick access to recent activities
- Navigate to specific sections using the sidebar menu

### Student Management
- **View Students**: Browse all students with pagination (25 per page)
- **Search**: Search by student name or ID
- **Filter**: Filter by class or status
- **Add Student**: Click "Add Student" to create a new student record
- **Edit/Delete**: Click on a student to edit or delete their information
- **CSV Import**: Bulk import students from CSV file

### Attendance
- **Mark Attendance**: Select date and mark students as Present/Absent/Leave
- **Bulk Actions**: Use "All Present" or "All Absent" buttons for quick marking
- **View History**: Check attendance records for past dates
- **Export**: Download attendance as PDF or Excel

### Fees
- **View Fees**: Browse fee records with payment status
- **Add Fee**: Create new fee entries
- **Mark Paid**: Update payment status and method
- **Generate Receipt**: Download PDF receipt for paid fees
- **Export**: Get fee reports in Excel format

### Quiz
- **Create Quiz**: Define quiz with 20 questions (mandatory)
- **Add Questions**: Add MCQ questions with 4 options and explanation
- **Take Quiz**: Students answer all questions with timer
- **View Results**: Review quiz results with detailed analysis
- **Performance**: Track improvement and analytics

## Project Structure

```
student_management/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── Procfile                 # Deployment configuration
├── runtime.txt              # Python version for deployment
│
├── student_management/      # Main project configuration
│   ├── settings.py         # Django settings
│   ├── urls.py             # URL routing
│   ├── wsgi.py             # WSGI application
│   └── asgi.py             # ASGI application
│
├── app/                     # Main application
│   ├── models.py           # Database models
│   ├── views.py            # View functions
│   ├── forms.py            # Form classes
│   ├── urls.py             # App URL patterns
│   ├── utils.py            # Utility functions
│   ├── admin.py            # Admin configuration
│   ├── tests.py            # Test cases
│   ├── management/
│   │   └── commands/
│   │       └── create_sample_data.py  # Sample data generator
│   └── migrations/         # Database migrations
│
├── templates/              # HTML templates
│   ├── base.html          # Base template with navbar
│   ├── login.html         # Login page
│   ├── dashboard.html     # Dashboard
│   ├── students/          # Student templates
│   ├── attendance/        # Attendance templates
│   ├── fees/              # Fee templates
│   ├── quiz/              # Quiz templates
│   └── analytics.html     # Analytics page
│
├── static/                 # Static files
│   ├── css/
│   │   └── style.css      # Main stylesheet
│   └── js/
│       └── main.js        # JavaScript functionality
│
└── locale/                 # Translation files
    └── gu/
        └── LC_MESSAGES/
            └── django.po  # Gujarati translations
```

## Testing

Run the automated test suite:

```bash
python manage.py test app
```

This will run:
- Model tests (creation, constraints, validation)
- Authentication tests (login, logout, authorization)
- View tests (CRUD operations, permissions)
- Form tests (validation)
- Total: 18+ test cases

## Creating Translations

The application supports bilingual interface. To translate to a new language:

1. **Create translation files**:
```bash
python manage.py makemessages -l xx  # Replace 'xx' with language code
```

2. **Edit the .po file** in `locale/xx/LC_MESSAGES/django.po`

3. **Compile messages**:
```bash
python manage.py compilemessages
```

## Deployment

### Environment Variables

Create `.env` file with production settings:

```env
DEBUG=False
SECRET_KEY=<generate-a-secure-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Using Gunicorn

```bash
pip install gunicorn
gunicorn student_management.wsgi:application
```

### Deployment Platforms

#### Railway
1. Connect GitHub repository
2. Set environment variables in dashboard
3. Deploy automatically

#### Render
1. Connect GitHub repository
2. Configure environment variables
3. Deploy from main branch

#### PythonAnywhere
1. Upload code
2. Configure Python version
3. Set up WSGI file
4. Configure environment variables

## Troubleshooting

### Static Files Not Loading
```bash
python manage.py collectstatic --noinput
```

### Gujarati Text Not Displaying
- Ensure browser supports Gujarati fonts
- Check that Noto Sans Gujarati font is loaded
- Refresh browser cache

### Translation Not Working
- Ensure `.mo` files are compiled from `.po` files
- Check `LANGUAGES` and `LOCALE_PATHS` in settings
- Verify language code in database

### Database Issues
- Delete `db.sqlite3` and run migrations again
- Check file permissions in project directory
- Ensure DATABASE_URL is correct

## Security Considerations

- Change the `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Use HTTPS in production
- Keep Django and dependencies updated
- Validate all user inputs
- Use environment variables for sensitive data
- Enable CSRF protection (enabled by default)

## Performance Optimization

- Use `select_related()` and `prefetch_related()` for queries
- Enable caching for frequently accessed data
- Use database indexes (already configured)
- Minimize static file sizes
- Use CDN for static files in production

## Support & Documentation

- Django Official Documentation: https://docs.djangoproject.com/
- Django i18n Guide: https://docs.djangoproject.com/en/4.2/topics/i18n/
- Gujarati Unicode: https://en.wikipedia.org/wiki/Gujarati_script

## License

This project is provided as-is for educational purposes.

## Contributors

- Copilot CLI Developer

---

**Last Updated**: 2026-08-16
**Django Version**: 4.2.8
**Python Version**: 3.11+
