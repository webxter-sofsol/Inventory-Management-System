# System Architecture Documentation

## Overview

This Django-based Inventory Management System follows a layered architecture pattern with clear separation of concerns. The system manages products, categories, stock transactions, and user authentication with email-based login.

## Technology Stack

- **Framework**: Django 4.2.7
- **Database**: SQLite3 (development)
- **API**: Django REST Framework
- **Authentication**: Custom email-based authentication
- **Testing**: pytest, Hypothesis (property-based testing)
- **Python Version**: 3.x

## Project Structure

```
inventory-management-system/
├── config/              # Project configuration
├── accounts/            # User authentication module
├── inventory/           # Core inventory management module
├── templates/           # HTML templates
├── static/              # Static files (CSS, JS, images)
├── tests/               # Test suite
└── manage.py           # Django management script
```

## Core Modules

### 1. Configuration Module (`config/`)

**Purpose**: Central project configuration and URL routing

**Key Files**:
- `settings.py` - Django settings, database config, authentication setup
- `urls.py` - Root URL configuration
- `wsgi.py` - WSGI application entry point
- `asgi.py` - ASGI application entry point

**Key Configurations**:
- Custom user model: `accounts.CustomUser`
- Email-based authentication backend
- REST Framework setup
- Static files configuration
- Logging configuration

### 2. Accounts Module (`accounts/`)

**Purpose**: User authentication and management

**Key Components**:
- `models.py` - CustomUser model with email authentication
- `views.py` - Login, register, logout views
- `forms.py` - Authentication forms
- `backends.py` - Email authentication backend
- `urls.py` - Authentication URL patterns

**Features**:
- Email-based login (no username)
- Custom user manager
- Session-based authentication
- User registration and management
### 3. Inventory Module (`inventory/`)

**Purpose**: Core business logic for inventory management

**Key Components**:

#### Models (`models.py`)
- `Category` - Product categories
- `Product` - Inventory items with stock tracking
- `StockTransaction` - Purchase/sale records
- `LowStockAlert` - Automated stock alerts
- `AIInteractionLog` - AI service interaction logging

#### Services (`services.py`)
Business logic layer with three main service classes:

- `ProductService` - Product CRUD, search, bulk operations
- `TransactionService` - Stock transactions, inventory updates
- `AlertService` - Low stock alert management

#### Views (`views.py`)
- Dashboard view
- Product CRUD views (List, Create, Update, Delete)
- Category management views
- Transaction recording and history views
- Bulk update operations
- AJAX endpoints for real-time validation

#### Forms (`forms.py`)
- `ProductForm` - Product creation/editing with validation
- `TransactionForm` - Stock transaction recording
- `BulkUpdateForm` - Bulk quantity/price updates
- `CategoryForm` - Category management

#### URL Routing (`urls.py`)
- Product management endpoints
- Category management endpoints
- Transaction endpoints
- Bulk operation endpoints
## Data Models and Relationships

### Entity Relationship Overview

```
CustomUser (1) -----> (M) StockTransaction
Category (1) -------> (M) Product
Product (1) --------> (M) StockTransaction
Product (1) --------> (1) LowStockAlert
```

### Model Details

#### CustomUser
- Email-based authentication (no username)
- Extends Django's AbstractUser
- Related to StockTransaction via foreign key

#### Category
- Simple categorization for products
- One-to-many relationship with Product
- PROTECT on delete (prevents deletion if products exist)

#### Product
- Core inventory entity
- Tracks quantity, price, alert thresholds
- Computed properties: total_value, is_low_stock, stock_status
- Database indexes on name, category, quantity for performance

#### StockTransaction
- Immutable transaction log
- Records all inventory changes (purchases/sales)
- Links to Product and User
- Ordered by timestamp (most recent first)

#### LowStockAlert
- One-to-one relationship with Product
- Automatically managed by AlertService
- Tracks active/inactive status
## Architecture Patterns

### 1. Layered Architecture

**Presentation Layer** (Views/Templates)
- Django views handle HTTP requests/responses
- Templates render HTML with context data
- Forms handle user input validation

**Business Logic Layer** (Services)
- Service classes encapsulate business rules
- Atomic transactions ensure data consistency
- Custom exceptions for business rule violations

**Data Access Layer** (Models)
- Django ORM for database operations
- Model methods for computed properties
- Database constraints and validation

### 2. Service Layer Pattern

The system uses dedicated service classes to encapsulate business logic:

**ProductService**:
- Product lifecycle management
- Search and filtering operations
- Bulk update operations with atomic transactions

**TransactionService**:
- Stock transaction processing
- Inventory level updates
- Transaction history retrieval

**AlertService**:
- Automated alert creation/resolution
- Low stock threshold monitoring
- Alert status management

### 3. Authentication Architecture

**Custom Authentication Backend**:
- Email-based login instead of username
- Integrates with Django's authentication system
- Maintains session-based authentication

**User Model Extension**:
- Extends AbstractUser with email as USERNAME_FIELD
- Custom user manager for user creation
- Database optimization with email indexing
## Module Interactions and Data Flow

### 1. User Authentication Flow

```
User Request → EmailAuthenticationBackend → CustomUser Model → Session Creation
```

1. User submits email/password via login form
2. EmailAuthenticationBackend validates credentials
3. CustomUser model queried by email
4. Session created on successful authentication
5. User redirected to dashboard

### 2. Product Management Flow

```
View → Form Validation → Service Layer → Model → Database
```

1. User interacts with ProductForm
2. Form validates input (XSS prevention, business rules)
3. ProductService handles business logic
4. Product model persists to database
5. Success/error messages returned to user

### 3. Transaction Processing Flow

```
Transaction Request → Stock Validation → Atomic Update → Alert Check
```

1. User submits transaction via TransactionForm
2. TransactionService validates stock availability
3. Atomic transaction updates Product quantity
4. StockTransaction record created
5. AlertService checks/updates low stock alerts
6. Success confirmation returned

### 4. Alert Management Flow

```
Stock Change → AlertService → Alert Creation/Resolution → Dashboard Display
```

1. Product quantity changes trigger alert check
2. AlertService compares quantity to threshold
3. LowStockAlert created/updated/deleted as needed
4. Active alerts displayed on dashboard
## Security Features

### 1. Input Validation and Sanitization
- Form-level validation for all user inputs
- HTML escaping to prevent XSS attacks
- Decimal validation for monetary values
- Integer validation for quantities

### 2. Authentication Security
- Email-based authentication
- Password validation (Django's built-in validators)
- Session-based authentication
- Login required decorators on sensitive views

### 3. Database Security
- Model-level validation constraints
- Foreign key constraints with appropriate on_delete behavior
- Database indexes for performance
- Atomic transactions for data consistency

### 4. Business Logic Security
- Overselling prevention in TransactionService
- Stock validation before sales
- Bulk operation validation (all-or-nothing)
- User permission checks via LoginRequiredMixin

## Performance Optimizations

### 1. Database Optimizations
- Strategic database indexes on frequently queried fields
- select_related() for foreign key relationships
- Pagination for large datasets (20-50 items per page)
- Optimized querysets in service layer

### 2. Caching Strategy
- Django's built-in session caching
- Template fragment caching opportunities
- Static file optimization

### 3. Query Optimization
- Prefetch related data in list views
- Efficient filtering in ProductService.search_products()
- Atomic transactions for bulk operations
## Testing Architecture

### 1. Test Structure
```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interactions
└── properties/     # Property-based tests using Hypothesis
```

### 2. Testing Strategies

**Unit Tests**:
- Service layer business logic
- Model methods and properties
- Form validation
- Authentication backend

**Integration Tests**:
- View-service-model interactions
- Transaction processing workflows
- Alert system integration

**Property-Based Tests**:
- Hypothesis framework for generating test data
- Invariant testing for business rules
- Edge case discovery

### 3. Test Coverage Areas
- Authentication flows
- Product CRUD operations
- Transaction processing
- Alert management
- Form validation
- Bulk operations

## API Architecture

### REST Framework Integration
- Session-based authentication for API endpoints
- Serializers for data validation and transformation
- ViewSets for CRUD operations
- Permission classes for access control

### API Endpoints Structure
```
/api/
├── products/       # Product management API
├── categories/     # Category management API
├── transactions/   # Transaction recording API
└── alerts/         # Alert management API
```
## Deployment Architecture

### 1. Development Environment
- SQLite database for local development
- Django development server
- Debug mode enabled
- Console and file logging

### 2. Production Considerations
- PostgreSQL/MySQL for production database
- WSGI server (Gunicorn/uWSGI)
- Reverse proxy (Nginx)
- Static file serving
- Environment-based configuration
- Secure secret key management

### 3. Static Files Management
- Separate static and media file handling
- Collectstatic for production deployment
- CDN integration possibilities

## Extension Points

### 1. Modular Design
- Clear separation between apps (accounts, inventory)
- Service layer abstraction for business logic
- Pluggable authentication backends
- Extensible model relationships

### 2. Future Enhancements
- Multi-warehouse support (extend Product model)
- Advanced reporting (new reporting app)
- API rate limiting
- Real-time notifications
- Mobile app integration via REST API
- Advanced search with Elasticsearch

### 3. Integration Capabilities
- REST API for external system integration
- Webhook support for real-time updates
- Import/export functionality
- Third-party service integration (AI services logged via AIInteractionLog)

## Conclusion

This inventory management system demonstrates a well-structured Django application with:
- Clear separation of concerns through layered architecture
- Robust business logic encapsulation in service classes
- Comprehensive security measures
- Performance optimizations
- Extensive testing coverage
- Scalable and maintainable codebase

The modular design allows for easy extension and maintenance while providing a solid foundation for inventory management operations.