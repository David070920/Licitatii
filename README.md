# Romanian Public Procurement Platform

A comprehensive platform for monitoring and analyzing Romanian public procurement data, serving both business intelligence and transparency needs.

## Features

- **Advanced Tender Search**: Powerful search and filtering capabilities
- **Risk Analysis**: Automated detection of procurement risks and anomalies
- **Business Intelligence**: Analytics and reporting for business users
- **Transparency Platform**: Public access to procurement data and statistics
- **Real-time Monitoring**: Live updates and alerts for tender changes
- **API Access**: RESTful API for programmatic access
- **Multi-user Support**: Role-based access control for different user types

## Architecture

- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for session management and caching
- **Background Tasks**: Celery for data processing
- **Authentication**: JWT-based with role-based permissions
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Licitatii
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Update the `.env` file with your configuration

4. Start services with Docker Compose:
```bash
docker-compose up -d
```

5. The API will be available at:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/api/v1/docs
   - Celery Flower: http://localhost:5555

### Local Development

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up database:
```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Run database migrations
python -m alembic upgrade head
```

4. Start the application:
```bash
uvicorn app.main:app --reload
```

5. Start Celery worker (in another terminal):
```bash
celery -A app.services.celery_app worker --loglevel=info
```

6. Start Celery beat (in another terminal):
```bash
celery -A app.services.celery_app beat --loglevel=info
```

## API Documentation

The API documentation is automatically generated and available at:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Authentication

Most endpoints require authentication. To authenticate:

1. Register a new user:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

2. Login to get access token:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"
```

3. Use the access token in subsequent requests:
```bash
curl -X GET "http://localhost:8000/api/v1/tenders" \
  -H "Authorization: Bearer <access_token>"
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run tests with verbose output
pytest -v
```

## Project Structure

```
app/
├── __init__.py
├── main.py                 # FastAPI application entry point
├── api/                    # API endpoints
│   └── v1/
│       ├── endpoints/      # API route handlers
│       └── router.py       # API router configuration
├── auth/                   # Authentication and authorization
│   ├── jwt_handler.py      # JWT token handling
│   └── security.py         # Security utilities
├── core/                   # Core application components
│   ├── config.py           # Configuration management
│   ├── database.py         # Database configuration
│   ├── logging.py          # Logging configuration
│   └── middleware.py       # Custom middleware
├── db/                     # Database models and migrations
│   └── models.py           # SQLAlchemy models
└── services/               # Business logic services
    └── celery_app.py       # Celery configuration

tests/                      # Test suite
├── conftest.py             # Test configuration
└── test_*.py               # Test files

docker-compose.yml          # Docker services configuration
Dockerfile                  # Application container
requirements.txt            # Python dependencies
.env.example               # Environment variables template
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_HOST`: Redis server host
- `SECRET_KEY`: JWT secret key (change in production)
- `ALLOWED_HOSTS`: CORS allowed hosts
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Data Sources

The platform ingests data from:

- **SICAP (SEAP)**: Primary Romanian procurement system
- **ANRMAP**: National regulatory authority data
- **EU TED**: European tender database
- **Local Municipalities**: Various municipal websites

## Risk Detection

The platform includes several risk detection algorithms:

- **Single Bidder Detection**: Identifies tenders with only one bidder
- **Price Anomaly Detection**: Detects unusual pricing patterns
- **Frequent Winner Analysis**: Identifies patterns of repeated winners
- **Geographic Clustering**: Detects geographic anomalies in procurement

## User Types

- **Anonymous Users**: View public tenders and statistics
- **Registered Citizens**: Create alerts and save searches
- **Business Users**: Advanced search, analytics, and reporting
- **Journalists**: Investigation tools and bulk data access
- **Administrators**: User management and system monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team.