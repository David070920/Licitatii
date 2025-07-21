# Romanian Public Procurement Platform

A comprehensive platform for monitoring and analyzing Romanian public procurement data, serving both business intelligence and transparency needs.

## 🚀 Features

- **Advanced Tender Search**: Powerful search and filtering capabilities
- **Risk Analysis**: Automated detection of procurement risks and anomalies
- **Business Intelligence**: Analytics and reporting for business users
- **Transparency Platform**: Public access to procurement data and statistics
- **Real-time Monitoring**: Live updates and alerts for tender changes
- **API Access**: RESTful API for programmatic access
- **Multi-user Support**: Role-based access control for different user types

## 🏗️ Architecture

- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for session management and caching
- **Background Tasks**: Celery for data processing
- **Authentication**: JWT-based with role-based permissions
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (optional)
- Git

### Automated Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Licitatii
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Run setup script**:
```bash
python setup_dev.py
```

4. **Set up PostgreSQL database**:
```bash
# Create database and user
createdb procurement_db
createuser procurement -P  # Set password when prompted

# Update DATABASE_URL in .env file
DATABASE_URL=postgresql://procurement:yourpassword@localhost:5432/procurement_db
```

5. **Initialize database**:
```bash
python init_db.py
```

6. **Start the application**:
```bash
uvicorn app.main:app --reload
```

7. **Access the API**:
   - API Documentation: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc
   - API Base: http://localhost:8000

### Manual Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Create environment file**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set up database**:
```bash
# Start PostgreSQL
# Create database: procurement_db
# Update DATABASE_URL in .env

# Run migrations
alembic upgrade head
```

4. **Initialize with sample data**:
```bash
python init_db.py
```

## 📊 Default Credentials

After running `python init_db.py`, you can use:
- **Email**: admin@licitatii.ro
- **Password**: admin123

## 🔧 Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/db

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Application
DEBUG=true
LOG_LEVEL=INFO
```

## 📚 API Documentation

### Authentication

Most endpoints require authentication. To authenticate:

1. **Register a new user**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

2. **Login to get access token**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=SecurePass123"
```

3. **Use the access token**:
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

### Key Endpoints

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user info
- `GET /api/v1/tenders` - Search tenders
- `GET /api/v1/dashboard/metrics` - Dashboard metrics
- `GET /api/v1/visualizations/dashboard/metrics` - Visualization data

## 🗄️ Database Schema

The platform uses a comprehensive database schema with:

- **Users & Authentication**: User management with role-based access
- **Tenders**: Complete tender information with relationships
- **Companies**: Bidding companies and contracting authorities
- **Risk Analysis**: Risk scores and pattern detection
- **Audit Logs**: Complete activity tracking

## 🔍 Risk Detection

The platform includes several risk detection algorithms:

- **Single Bidder Detection**: Identifies tenders with only one bidder
- **Price Anomaly Detection**: Detects unusual pricing patterns
- **Frequent Winner Analysis**: Identifies patterns of repeated winners
- **Geographic Clustering**: Detects geographic anomalies in procurement

## 👥 User Types

- **Anonymous Users**: View public tenders and statistics
- **Registered Citizens**: Create alerts and save searches
- **Business Users**: Advanced search, analytics, and reporting
- **Journalists**: Investigation tools and bulk data access
- **Administrators**: User management and system monitoring

## 📊 Data Sources

The platform ingests data from:

- **SICAP (SEAP)**: Primary Romanian procurement system
- **ANRMAP**: National regulatory authority data
- **EU TED**: European tender database
- **Local Municipalities**: Various municipal websites

## 🚀 Development

### Project Structure

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
│   └── ...
├── db/                     # Database models
│   └── models.py           # SQLAlchemy models
├── schemas/                # Pydantic schemas
│   ├── auth.py            # Authentication schemas
│   ├── user.py            # User schemas
│   └── ...
└── services/               # Business logic services
    └── ...
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t romanian-procurement .

# Run container
docker run -p 8000:8000 romanian-procurement
```

## 🌐 Production Deployment

### Railway Deployment

1. **Install Railway CLI**:
```bash
npm install -g @railway/cli
```

2. **Deploy**:
```bash
railway login
railway init
railway up
```

3. **Add database**:
```bash
railway add postgresql
```

### Environment Variables

Set these in your production environment:

```env
DATABASE_URL=postgresql://...
SECRET_KEY=production-secret-key
CORS_ORIGINS=["https://your-frontend.com"]
```

## 📈 Monitoring

The platform includes:

- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus-compatible metrics
- **Logging**: Structured logging with different levels
- **Error Tracking**: Sentry integration support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the API documentation at `/api/v1/docs`
- Review the architecture documentation in the markdown files
- Create an issue in the repository

## 🔮 Roadmap

- [ ] Advanced risk detection algorithms
- [ ] Real-time data ingestion pipeline
- [ ] Mobile application
- [ ] Advanced analytics dashboard
- [ ] Machine learning integration
- [ ] Multi-language support
- [ ] Advanced reporting system
- [ ] API rate limiting and quotas
- [ ] Advanced caching strategies
- [ ] Comprehensive monitoring dashboard

---

**Romanian Public Procurement Platform** - Bringing transparency and efficiency to public procurement through advanced technology and data analysis.