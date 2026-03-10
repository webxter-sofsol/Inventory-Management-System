# Inventory Management System

A Django-based web application for managing product inventory, tracking stock levels, and monitoring sales and purchase transactions.

## Features

- Email-based user authentication
- Product management with categories
- Stock transaction tracking (purchases and sales)
- Low-stock alerts with configurable thresholds
- Real-time dashboard with inventory metrics
- Transaction history and audit trail
- Inventory reporting with CSV and PDF export
- REST API for AI integration
- Mobile-responsive interface with Bootstrap 5
- Real-time updates with HTMX

## Technology Stack

- **Backend**: Django 4.2+
- **Database**: SQLite 3
- **Frontend**: Django Templates + Bootstrap 5 + HTMX
- **API**: Django REST Framework
- **Testing**: pytest + pytest-django + Hypothesis
- **Reporting**: ReportLab (PDF) + Python CSV

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

8. Access the application at `http://localhost:8000`

## Running Tests

Run all tests:
```bash
pytest
```

Run specific test types:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m property      # Property-based tests only
```

Run with coverage:
```bash
pytest --cov=inventory --cov=accounts
```

## Project Structure

```
inventory_system/
├── config/              # Project configuration
├── accounts/            # Authentication app
├── inventory/           # Main inventory app
├── templates/           # HTML templates
├── static/              # Static files (CSS, JS, images)
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── properties/     # Property-based tests
└── manage.py
```

## Development

- Follow Django best practices
- Write tests for all new features
- Use property-based testing for correctness validation
- Ensure mobile responsiveness (320px - 2560px)
- Maintain security best practices (CSRF, XSS prevention, SQL injection prevention)

## License

Proprietary - All rights reserved
