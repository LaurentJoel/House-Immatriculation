# Cameroon House Immatriculation & Tax Collection System

A nationwide digital platform to register and uniquely identify all buildings in Cameroon, automate property tax assessment and collection, enable field verification through mobile applications, and provide citizen-facing services.

## Quick Start

```bash
# 1. Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# 2. Set up backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Run migrations
flask db upgrade

# 4. Run development server
flask run --debug

# 5. Run tests
pytest --cov=app -v
```

## Project Structure

```
ImmatriculationDomicile/
├── backend/          # Flask API server
├── frontend/
│   ├── admin/        # React.js admin dashboard
│   └── citizen/      # Next.js citizen portal
├── mobile/           # Flutter field agent app
├── docker/           # Docker configs (nginx, postgres)
├── scripts/          # Utility scripts
├── docs/             # Additional documentation
└── backups/          # Database backups
```

## Documentation

See [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for the complete technical specification.
