# Django Gym Management System

A comprehensive ERP system for gym and fitness center management, built with Django REST Framework.

## Features

- **Client Management**: Track clients with VAT numbers, contact information, and complete history
- **Package System**: Create custom packages with flexible installment plans
- **Appointment Scheduling**: Manage client appointments with conflict detection
- **Financial Tracking**: Monitor revenue, outstanding payments, and overdue installments
- **Role-Based Access Control**: Three user roles with different permission levels
- **Global Statistics**: Business intelligence dashboard for managers and admins

## User Roles

- **Admin**: Full access to all features including statistics and summaries
- **Manager**: Access to statistics, summaries, and all operational features
- **Staff**: Access to standard operational features (clients, packages, appointments)

## Tech Stack

- **Framework**: Django 6.0.3
- **API**: Django REST Framework
- **Authentication**: JWT (Simple JWT)
- **Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Database**: SQLite (development)

## Installation

### Prerequisites

- Python 3.14+
- pip
- virtualenv (recommended)

### Setup

1. **Clone the repository**
   ```bash
   cd /path/to/DjangoProject
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install django djangorestframework djangorestframework-simplejwt drf-spectacular
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://127.0.0.1:8000/`

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://127.0.0.1:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://127.0.0.1:8000/api/schema/redoc/`

## API Endpoints

### Authentication

#### Signup
```http
POST /api/signup/
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "role": "staff"  // Options: "admin", "manager", "staff"
}
```

#### Login
```http
POST /api/token/
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Refresh Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Clients

**Permissions**: All authenticated users

```http
GET    /api/clients/           # List all clients (paginated)
POST   /api/clients/           # Create new client
GET    /api/clients/{id}/      # Get client details
PUT    /api/clients/{id}/      # Update client
DELETE /api/clients/{id}/      # Delete client
GET    /api/clients/{id}/summary/  # Get client summary (Manager/Admin only)
```

**Client Summary Response** (Manager/Admin only):
```json
{
  "client_name": "Acme Gym",
  "total_debt": 1500.00,
  "active_packages_count": 2,
  "next_appointment": "2026-03-25T10:00:00Z",
  "next_appointment_title": "Personal Training",
  "last_appointment": "2026-03-20T15:00:00Z",
  "last_appointment_title": "Consultation"
}
```

### Packages

**Permissions**: All authenticated users

```http
GET    /api/packages/          # List all packages
POST   /api/packages/          # Create package with installments
GET    /api/packages/{id}/     # Get package details
PUT    /api/packages/{id}/     # Update package
DELETE /api/packages/{id}/     # Delete package
```

**Create Package Example**:
```json
{
  "client": 1,
  "name": "Gold Membership",
  "total_price": 1200.00,
  "number_of_installments": 12
}
```
This automatically generates 12 monthly installments of 100.00 each.

### Installments

**Permissions**: All authenticated users

```http
GET    /api/installments/      # List all installments
POST   /api/installments/      # Create installment
GET    /api/installments/{id}/ # Get installment details
PUT    /api/installments/{id}/ # Update installment (e.g., mark as paid)
DELETE /api/installments/{id}/ # Delete installment
```

**Mark as Paid**:
```json
{
  "is_paid": true
}
```

### Appointments

**Permissions**: All authenticated users

```http
GET    /api/appointments/      # List all appointments
POST   /api/appointments/      # Create appointment
GET    /api/appointments/{id}/ # Get appointment details
PUT    /api/appointments/{id}/ # Update appointment
DELETE /api/appointments/{id}/ # Delete appointment
```

**Create Appointment Example**:
```json
{
  "client": 1,
  "package": 1,
  "title": "Personal Training Session",
  "start_time": "2026-03-25T10:00:00Z",
  "end_time": "2026-03-25T11:00:00Z",
  "notes": "Focus on cardio"
}
```

**Validations**:
- Client must have at least one package
- End time must be after start time
- No overlapping appointments for the same client

### Global Statistics

**Permissions**: Manager and Admin only

```http
GET /api/stats/
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "financial": {
    "total_revenue_ever": 50000.00,
    "expected_this_month": 5000.00,
    "collected_this_month": 4500.00,
    "total_overdue_amount": 2000.00
  },
  "operational": {
    "total_clients": 150,
    "active_packages": 200,
    "appointments_today": 8
  },
  "kpi": {
    "collection_rate": 90.0
  }
}
```

## Authentication

All protected endpoints require JWT authentication. Include the access token in the Authorization header:

```http
Authorization: Bearer {access_token}
```

Access tokens expire after a set period. Use the refresh token to obtain a new access token without requiring the user to log in again.

## Permission Matrix

| Endpoint | Admin | Manager | Staff |
|----------|-------|---------|-------|
| Signup | ✓ | ✓ | ✓ |
| Login | ✓ | ✓ | ✓ |
| Clients (CRUD) | ✓ | ✓ | ✓ |
| Client Summary | ✓ | ✓ | ✗ |
| Packages (CRUD) | ✓ | ✓ | ✓ |
| Installments (CRUD) | ✓ | ✓ | ✓ |
| Appointments (CRUD) | ✓ | ✓ | ✓ |
| Global Statistics | ✓ | ✓ | ✗ |

## Database Models

### User
- username (unique)
- email
- password (hashed)
- role (admin/manager/staff)

### Client
- name
- vat_number (unique)
- email

### Package
- client (ForeignKey)
- name
- total_price
- created_at

### Installment
- package (ForeignKey)
- amount
- due_date
- is_paid (boolean)

### Appointment
- client (ForeignKey)
- package (ForeignKey, nullable)
- title
- start_time
- end_time
- notes

## Development

### Project Structure
```
DjangoProject/
├── DjangoGym/          # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── erp/                # Main app
│   ├── models.py       # Data models
│   ├── views.py        # API views
│   ├── serializers.py  # DRF serializers
│   ├── permissions.py  # Custom permissions
│   └── migrations/     # Database migrations
├── manage.py
└── db.sqlite3          # SQLite database
```

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Configuration

### Settings (DjangoGym/settings.py)

- **SECRET_KEY**: Change in production
- **DEBUG**: Set to `False` in production
- **ALLOWED_HOSTS**: Add your domain in production
- **DATABASES**: Configure PostgreSQL/MySQL for production
- **TIME_ZONE**: Default is UTC

### Pagination

Default pagination is set to 20 items per page with a maximum of 100. Clients can request different page sizes:

```http
GET /api/clients/?limit=50&page=2
```

## Security Considerations

⚠️ **Production Deployment**:

1. Change the `SECRET_KEY` in settings.py
2. Set `DEBUG = False`
3. Configure `ALLOWED_HOSTS`
4. Use a production database (PostgreSQL recommended)
5. Enable HTTPS
6. Configure CORS properly
7. Set up proper logging
8. Use environment variables for sensitive data

## License

This project is for educational and business purposes.

## Support

For issues and questions, please contact the development team.

---

**Version**: 1.0.4
**Last Updated**: March 2026
