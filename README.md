# Notification Service

A microservice for managing user notifications following Domain-Driven Design (DDD) and Clean Architecture principles.

## 🎯 Overview

The Notification Service is responsible for:
- Managing user notification preferences
- Sending notifications via email
- Handling notification delivery failures and retries
- Processing notification requests from other services

## 🏗️ Architecture

This service follows Clean Architecture with clear separation of concerns:

```
├── Domain Layer (Business Logic)
│   ├── Entities: NotificationRequest, NotificationPreferences
│   ├── Value Objects: UserID, NotificationEmail, NotificationID
│   ├── Enums: NotificationType, NotificationStatus
│   └── Commands: SendNotification, UpdatePreferences, RetryNotification
│
├── Service Layer (Application Logic)
│   ├── Handlers: Command and event handlers
│   ├── Message Bus: Command/event routing
│   └── Unit of Work: Transaction management
│
├── Adapters (Infrastructure)
│   ├── Database: PostgreSQL with SQLAlchemy ORM
│   ├── Email Provider: SMTP email adapter
│   └── Message Broker: RabbitMQ pub/sub
│
└── Entrypoints (Interface)
    ├── REST API: FastAPI endpoints
    └── Message Consumers: Queue subscribers
```

## 🚀 Features

### Notification Types
- `EMAIL_VERIFICATION`: Account verification emails
- `PASSWORD_RESET`: Password reset notifications
- `WELCOME`: New user welcome messages
- `SECURITY_ALERT`: Security-related notifications

### Core Capabilities
- ✅ User preference management
- ✅ Email notification delivery
- ✅ Automatic retry mechanism for failed notifications
- ✅ Event-driven architecture with domain events
- ✅ Transactional consistency with Unit of Work pattern
- ✅ Comprehensive logging and monitoring

## 🛠️ Technology Stack

- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Message Broker**: RabbitMQ
- **ORM**: SQLAlchemy
- **Testing**: pytest
- **Containerization**: Docker & Docker Compose

## 📋 Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+
- RabbitMQ 3.12+

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd notification-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL and RabbitMQ
docker-compose up -d postgres rabbitmq

# Wait for services to be ready
make wait-for-services
```

### 3. Run Database Migrations

```bash
# Apply database schema
make migrate
```

### 4. Start the Service

```bash
# Development mode
make run-dev

# Production mode
make run-prod
```

The service will be available at `http://localhost:8000`

## 📖 API Documentation

### Endpoints

#### Notification Preferences

```http
POST /preferences
Content-Type: application/json

{
  "userid": "1234567890abcdef1234567890abcdef",
  "notification_email": "user@example.com",
  "preferences": {
    "email_verification": true,
    "password_reset": true,
    "welcome": true,
    "security_alert": true
  }
}
```

```http
GET /preferences/{userid}
```

```http
PUT /preferences/{userid}
Content-Type: application/json

{
  "preferences": {
    "email_verification": false,
    "security_alert": true
  }
}
```

#### Send Notifications

```http
POST /notifications/send
Content-Type: application/json

{
  "notification_id": "abcdef1234567890abcdef1234567890",
  "userid": "1234567890abcdef1234567890abcdef",
  "notification_type": "welcome",
  "recipient_email": "user@example.com",
  "subject": "Welcome to our platform!",
  "content": "Welcome {{user_name}}, thanks for joining!",
  "template_vars": {
    "user_name": "John Doe"
  }
}
```

#### Retry Failed Notifications

```http
POST /notifications/{notification_id}/retry
```

### Interactive API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Testing

### Run All Tests

```bash
# Run complete test suite
make test

# Run with coverage
make test-coverage

# Run specific test categories
make test-unit
make test-integration
make test-e2e
```

### Test Categories

- **Unit Tests**: Domain logic and business rules
- **Integration Tests**: Database and repository operations
- **E2E Tests**: Full API workflows

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/notifications

# Message Broker
RABBITMQ_URL=amqp://user:password@localhost:5672/

# Email Provider
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# Service
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Configuration Files

- `config/base/logger_config.yml`: Logging configuration
- `config/conf/`: Database and message broker configurations
- `pyproject.toml`: Python project configuration

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the service image
docker build -t notification-service .

# Run with Docker Compose
docker-compose up -d
```

### Production Deployment

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Monitoring & Observability

### Health Checks

```http
GET /health
```

### Metrics

- Application metrics via `/metrics` endpoint
- Database connection pooling metrics
- Message broker queue metrics

### Logging

- Structured JSON logging
- Correlation ID tracking across requests
- Request/response logging with filtering

## 🔄 Message Broker Integration

### Published Events

- `NotificationRequested`: When a notification is requested
- `NotificationSent`: When a notification is successfully sent
- `NotificationFailed`: When a notification fails
- `NotificationPreferencesCreated`: When user preferences are created
- `NotificationPreferencesUpdated`: When user preferences are updated

### Subscribed Events

- User service events for account changes
- Other service events requiring notifications

## 🚨 Error Handling

### Retry Strategy

- Failed notifications are automatically retried up to 3 times
- Exponential backoff between retry attempts
- Failed notifications after max retries are logged for manual investigation

### Error Responses

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid email address format",
  "details": {
    "field": "recipient_email",
    "value": "invalid-email"
  }
}
```

## 🧑‍💻 Development

### Project Structure

```
src/
├── domain/           # Business logic
├── service_layer/    # Application services
├── adapters/         # Infrastructure adapters
├── entrypoints/      # API and message handlers
└── core/            # Shared utilities
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints throughout
- Maintain test coverage above 85%
- Follow Clean Architecture principles

### Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📚 Additional Resources

- [Domain-Driven Design](https://www.domainlanguage.com/ddd/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

