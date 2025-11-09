# Election Cart Backend 🗳️

Production-ready Django REST API for the Election Cart e-commerce platform.

## Features

- 🔐 JWT Authentication with Firebase integration
- 📦 Product Management (Packages & Campaigns)
- 🛒 Shopping Cart & Order Processing
- 💳 Razorpay Payment Integration
- 📤 Dynamic Resource Upload System
- 🖼️ Cloudinary CDN for media files
- 👥 Multi-role Admin Panel (Admin, Staff, Manager)
- 📊 Analytics & Reporting
- 🧾 Invoice Generation
- ✅ Order Checklist System

## Tech Stack

- **Framework**: Django 4.2+ & Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT + Firebase
- **Payment**: Razorpay
- **Storage**: Cloudinary
- **Server**: Gunicorn
- **Monitoring**: Sentry

## Production Ready ✅

- Security headers configured
- Rate limiting on critical endpoints
- Comprehensive logging
- Health check endpoint
- Error tracking with Sentry
- Static files optimized with WhiteNoise
- Database connection pooling
- SSL/HTTPS enforced

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Cloudinary account
- Razorpay account
- Firebase project

### Installation

```bash
# Clone repository
git clone https://github.com/shiblymohammed/electioncart_backend.git
cd electioncart_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Configure environment variables (see below)
# Edit .env with your credentials

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Variables

See `.env.example` for all required variables:

- `DJANGO_SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `DATABASE_URL`: PostgreSQL connection string
- `RAZORPAY_KEY_ID`: Razorpay API key
- `RAZORPAY_KEY_SECRET`: Razorpay secret
- `CLOUDINARY_*`: Cloudinary credentials
- `SENTRY_DSN`: Sentry error tracking DSN
- `CORS_ALLOWED_ORIGINS`: Frontend URLs

## Deployment

### Railway (Recommended)

1. Push code to GitHub
2. Create new Railway project
3. Connect GitHub repository
4. Add PostgreSQL database
5. Configure environment variables
6. Deploy automatically

See `RAILWAY_DEPLOYMENT_GUIDE.md` for detailed instructions.

## API Documentation

### Authentication
- `POST /api/auth/signup/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh JWT token

### Products
- `GET /api/packages/` - List packages
- `GET /api/campaigns/` - List campaigns
- `GET /api/packages/{id}/` - Package details
- `GET /api/campaigns/{id}/` - Campaign details

### Cart & Orders
- `GET /api/cart/` - View cart
- `POST /api/cart/add/` - Add to cart
- `POST /api/orders/create/` - Create order
- `POST /api/orders/{id}/payment/verify/` - Verify payment

### Admin Panel
- `GET /api/admin/orders/` - List orders
- `PATCH /api/admin/orders/{id}/` - Update order
- `GET /api/admin/analytics/` - Analytics data

## Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test products
python manage.py test orders

# Check deployment readiness
python manage.py check --deploy
```

## Security

- All secrets stored in environment variables
- DEBUG defaults to False
- HTTPS enforced in production
- Security headers configured
- Rate limiting on authentication endpoints
- SQL injection protection via ORM
- XSS protection enabled
- CSRF protection enabled

## Monitoring

- **Health Check**: `/health/`
- **Error Tracking**: Sentry integration
- **Logging**: Comprehensive file and console logging
- **Uptime Monitoring**: UptimeRobot compatible

## Project Structure

```
backend/
├── authentication/      # User authentication & JWT
├── products/           # Products, packages, campaigns
├── cart/              # Shopping cart
├── orders/            # Order processing & payments
├── admin_panel/       # Admin dashboard APIs
├── election_cart/     # Django settings
├── templates/         # Error page templates
├── logs/             # Application logs
└── manage.py
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is proprietary and confidential.

## Support

For issues and questions, please open a GitHub issue.

---

**Status**: Production Ready ✅  
**Version**: 1.0.0  
**Last Updated**: November 2025
