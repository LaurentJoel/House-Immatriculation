# CAMEROON HOUSE IMMATRICULATION & TAX COLLECTION SYSTEM

## Technical Design Document (TDD)

---

**Document Version:** 1.2  
**Date:** February 6, 2026  
**Project Code:** IMMAT-CMR-2026  
**Classification:** Internal Technical Document  

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Design Patterns & Principles](#5-design-patterns--principles)
6. [Database Design](#6-database-design)
7. [API Specification](#7-api-specification)
8. [Frontend Applications](#8-frontend-applications)
9. [Internationalization (i18n)](#9-internationalization-i18n)
10. [Caching Architecture](#10-caching-architecture)
11. [Security Architecture](#11-security-architecture)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Test-Driven Development Plan](#13-test-driven-development-plan)
14. [Testing Strategy](#14-testing-strategy)
15. [Maintenance & Operations](#15-maintenance--operations)
16. [Appendices](#16-appendices)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Project Purpose

This document serves as the comprehensive technical guide for the **Cameroon House Immatriculation and Tax Collection System** - a nationwide digital platform designed to:

- Register and uniquely identify all residential and commercial buildings
- Automate property tax assessment and collection
- Enable field verification through mobile applications
- Provide citizen-facing services for tax payments and property certificates
- Generate analytics for government decision-making

### 1.2 Key Decisions Summary

| Aspect | Decision |
|--------|----------|
| **Backend Framework** | Flask (Python) with PostgreSQL/PostGIS |
| **Frontend - Web** | React.js with Ant Design |
| **Frontend - Mobile** | Flutter (cross-platform) |
| **Database** | PostgreSQL 15 + PostGIS 3.3 |
| **Design Pattern** | Layered Architecture + Repository Pattern |
| **Deployment** | Docker-based on-premise (data sovereignty) |
| **Languages** | French (default) + English (bilingual) |
| **Phase 1 Pilot** | Yaoundé and Douala regions |

### 1.3 Data Sovereignty Compliance

All data remains within Cameroon's borders:
- On-premise Docker deployment in government data centers
- No cloud dependencies
- Full control over data access and storage
- Compliance with national data protection regulations

---

## 2. PROJECT OVERVIEW

### 2.1 Business Objectives

1. **Complete Property Registration**: Assign unique immatriculation numbers to all buildings
2. **Automated Tax Assessment**: Calculate property taxes based on building characteristics
3. **Efficient Tax Collection**: Multiple payment channels including mobile money
4. **Field Verification**: Mobile app for agents to verify and update property data
5. **Citizen Services**: Self-service portal for property owners
6. **Analytics & Reporting**: Real-time dashboards for government officials

### 2.2 Target Users & Interfaces

The system has **3 distinct interfaces**:

| # | Interface | Technology | Users | Purpose |
|---|-----------|------------|-------|--------|
| **1** | Admin Dashboard | React.js + Ant Design | Staff, Managers, Tax collectors, GIS team | House CRUD, user management, payments, reports, analytics, map review |
| **2** | Citizen Portal | Next.js (Responsive) | Property owners | Property lookup, tax status, online payment, certificate download |
| **3** | Field Agent Mobile App | Flutter | Field verification agents | GPS navigation, offline mode, photo capture, verification forms |

**Note:** The Citizen Portal is fully responsive and works on both desktop and mobile browsers. There is no separate mobile app for citizens.

#### User Roles by Interface

| User Role | Interface | Primary Functions |
|-----------|-----------|-------------------|
| **Field Agents** | Mobile App (Flutter) | GPS verification, photo capture, offline data collection |
| **Tax Collectors** | Admin Dashboard | Record payments, generate receipts |
| **Back-Office Staff** | Admin Dashboard | Data management, user administration |
| **Citizens** | Citizen Portal (Web - Responsive) | View property, pay taxes, download certificates |
| **Management** | Admin Dashboard | Reports, statistics, geographic visualization |
| **GIS Team** | Admin Dashboard | Quality control, satellite detection review |

### 2.3 Immatriculation Number Format

```
CMR-{REGION_CODE}-{COMMUNE_CODE}-{SEQUENCE_NUMBER}

Example: CMR-CE-YDE-0001234
- CMR: Country code (Cameroon)
- CE: Region code (Centre)
- YDE: Commune code (Yaoundé)
- 0001234: 7-digit sequence number
```

---

## 3. SYSTEM ARCHITECTURE

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│  Flutter Mobile │  React.js Web   │  React.js Web   │  React.js Web     │
│  (Field Agents) │  (Admin Panel)  │  (Citizen)      │  (Analytics)      │
│                 │                 │                 │                   │
│  • Offline sync │  • User mgmt    │  • Property     │  • Reports        │
│  • GPS/Camera   │  • Data CRUD    │    lookup       │  • Charts         │
│  • Verification │  • Reports      │  • Payments     │  • Maps           │
└────────┬────────┴────────┬────────┴────────┬────────┴─────────┬─────────┘
         │                 │                 │                  │
         └─────────────────┴────────┬────────┴──────────────────┘
                                    │ HTTPS/REST
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (Nginx)                             │
│  • SSL Termination  • Rate Limiting  • Load Balancing  • Routing        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER (Flask)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                         PRESENTATION LAYER                               │
│                    (REST API Routes / Endpoints)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                          SERVICE LAYER                                   │
│  • HouseService      • TaxService        • PaymentService               │
│  • ImmatriculationService  • UserService  • ReportService               │
├─────────────────────────────────────────────────────────────────────────┤
│                         REPOSITORY LAYER                                 │
│  • HouseRepository   • PaymentRepository  • UserRepository              │
│  • BoundaryRepository  • TaxRepository                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                           MODEL LAYER                                    │
│               (SQLAlchemy ORM + GeoAlchemy2 Models)                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   PostgreSQL    │       │      Redis      │       │      MinIO      │
│   + PostGIS     │       │                 │       │                 │
│                 │       │  • Session      │       │  • Documents    │
│  • Houses       │       │  • Cache        │       │  • Photos       │
│  • Payments     │       │  • Rate limit   │       │  • Certificates │
│  • Users        │       │                 │       │                 │
│  • Boundaries   │       │                 │       │                 │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

### 3.2 Component Interactions

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Mobile     │    │   Web App    │    │   External   │
│    App       │    │  (React)     │    │   Systems    │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       │    HTTPS/JSON     │    HTTPS/JSON     │    API Integration
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Nginx Proxy   │
                  │   (SSL + LB)    │
                  └────────┬────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Flask API  │ │  Flask API  │ │  Flask API  │
    │  Instance 1 │ │  Instance 2 │ │  Instance 3 │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  PostgreSQL │     │    Redis    │     │    MinIO    │
│  (Primary)  │     │   Cluster   │     │   Storage   │
├─────────────┤     └─────────────┘     └─────────────┘
│  PostgreSQL │
│  (Replica)  │
└─────────────┘
```

---

## 4. TECHNOLOGY STACK

### 4.1 Complete Stack Overview

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Backend** | Python | 3.11+ | Core programming language |
| | Flask | 3.0+ | Web framework |
| | SQLAlchemy | 2.0+ | ORM |
| | GeoAlchemy2 | 0.14+ | Spatial ORM extension |
| | Flask-Babel | 4.0+ | Internationalization |
| | Flask-JWT-Extended | 4.6+ | Authentication |
| | Celery | 5.3+ | Background tasks |
| | Gunicorn | 21+ | WSGI server |
| **Database** | PostgreSQL | 15+ | Primary database |
| | PostGIS | 3.3+ | Spatial extension |
| **Cache** | Redis | 7+ | Caching & sessions |
| **Storage** | MinIO | Latest | S3-compatible object storage |
| **Web Frontend** | React.js | 18+ | UI framework |
| | Ant Design | 5+ | UI component library |
| | Leaflet.js | 1.9+ | Interactive maps |
| | react-i18next | 13+ | Internationalization |
| | Recharts | 2+ | Charts & analytics |
| **Mobile** | Flutter | 3.16+ | Cross-platform mobile |
| | sqflite | 2.3+ | Local SQLite database |
| | flutter_map | 6+ | Mobile maps |
| **DevOps** | Docker | 24+ | Containerization |
| | Docker Compose | 2.23+ | Container orchestration |
| | Nginx | 1.25+ | Reverse proxy & load balancer |
| **Tools** | GDAL | 3.8+ | Geospatial data processing |
| | Rasterio | 1.3+ | Satellite imagery processing |
| | OpenCV | 4.8+ | Computer vision |

### 4.2 Backend Directory Structure

```
backend/
├── app/
│   ├── __init__.py                 # Flask application factory
│   ├── config.py                   # Configuration management
│   │
│   ├── api/                        # Presentation Layer
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Authentication endpoints
│   │   │   ├── houses.py           # House management
│   │   │   ├── payments.py         # Payment processing
│   │   │   ├── users.py            # User management
│   │   │   ├── reports.py          # Report generation
│   │   │   └── verification.py     # Field verification
│   │   │
│   │   └── schemas/                # Request/Response DTOs
│   │       ├── __init__.py
│   │       ├── house_schema.py
│   │       ├── payment_schema.py
│   │       └── user_schema.py
│   │
│   ├── services/                   # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── house_service.py
│   │   ├── tax_service.py
│   │   ├── payment_service.py
│   │   ├── immatriculation_service.py
│   │   ├── notification_service.py
│   │   └── report_service.py
│   │
│   ├── repositories/               # Data Access Layer
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── house_repository.py
│   │   ├── payment_repository.py
│   │   ├── user_repository.py
│   │   └── boundary_repository.py
│   │
│   ├── models/                     # Domain Models
│   │   ├── __init__.py
│   │   ├── house.py
│   │   ├── payment.py
│   │   ├── user.py
│   │   ├── admin_boundary.py
│   │   └── tax_category.py
│   │
│   ├── core/                       # Core Utilities
│   │   ├── __init__.py
│   │   ├── security.py             # JWT, password hashing
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── events.py               # Event dispatcher
│   │   └── permissions.py          # RBAC
│   │
│   ├── utils/                      # Helper Functions
│   │   ├── __init__.py
│   │   ├── geo_utils.py            # Geospatial utilities
│   │   ├── tax_calculator.py       # Tax calculations
│   │   └── validators.py           # Input validation
│   │
│   └── translations/               # i18n Files
│       ├── fr/
│       │   └── LC_MESSAGES/
│       │       ├── messages.po
│       │       └── messages.mo
│       └── en/
│           └── LC_MESSAGES/
│               ├── messages.po
│               └── messages.mo
│
├── migrations/                     # Alembic database migrations
├── tests/                          # Unit and integration tests
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Development dependencies
├── Dockerfile                      # Container definition
├── wsgi.py                         # WSGI entry point
└── babel.cfg                       # Babel configuration
```

### 4.3 Frontend Directory Structure

```
frontend/
├── admin/                          # Admin Dashboard
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── houses/
│   │   │   ├── payments/
│   │   │   └── users/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── locales/
│   │   │   ├── fr/
│   │   │   └── en/
│   │   ├── utils/
│   │   ├── i18n.js
│   │   ├── App.jsx
│   │   └── index.jsx
│   ├── package.json
│   └── Dockerfile
│
├── citizen/                        # Citizen Portal
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── locales/
│   │   └── ...
│   ├── package.json
│   └── Dockerfile
│
└── mobile/                         # Flutter Mobile App
    ├── lib/
    │   ├── models/
    │   ├── screens/
    │   ├── services/
    │   ├── widgets/
    │   ├── l10n/
    │   │   ├── app_fr.arb
    │   │   └── app_en.arb
    │   └── main.dart
    ├── pubspec.yaml
    └── ...
```

---

## 5. DESIGN PATTERNS & PRINCIPLES

### 5.1 Architectural Patterns

#### 5.1.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│              (Flask Routes / API Endpoints)                  │
│                                                              │
│  Responsibilities:                                           │
│  • HTTP request/response handling                           │
│  • Input validation                                         │
│  • Authentication/Authorization checks                      │
│  • Response formatting                                      │
├─────────────────────────────────────────────────────────────┤
│                     SERVICE LAYER                            │
│          (Business Logic & Domain Operations)                │
│                                                              │
│  Responsibilities:                                           │
│  • Business rules implementation                            │
│  • Tax calculations                                         │
│  • Immatriculation number generation                        │
│  • Cross-entity operations                                  │
├─────────────────────────────────────────────────────────────┤
│                    REPOSITORY LAYER                          │
│              (Data Access Abstraction)                       │
│                                                              │
│  Responsibilities:                                           │
│  • Database queries                                         │
│  • Data mapping                                             │
│  • Query optimization                                       │
│  • Transaction management                                   │
├─────────────────────────────────────────────────────────────┤
│                      MODEL LAYER                             │
│                (Domain Entities / ORM)                       │
│                                                              │
│  Responsibilities:                                           │
│  • Entity definitions                                       │
│  • Relationships                                            │
│  • Validation rules                                         │
└─────────────────────────────────────────────────────────────┘
```

#### 5.1.2 Repository Pattern Implementation

```python
# base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[T]:
        pass
    
    @abstractmethod
    def create(self, entity: T) -> T:
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        pass
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        pass

# house_repository.py
class HouseRepository(BaseRepository[House]):
    def __init__(self, db_session):
        self.session = db_session
    
    def get_by_id(self, house_id: int) -> Optional[House]:
        return self.session.query(House).filter_by(house_id=house_id).first()
    
    def get_by_immatriculation(self, immat_num: str) -> Optional[House]:
        return self.session.query(House).filter_by(
            immatriculation_number=immat_num
        ).first()
    
    def find_in_bounds(self, min_lat, min_lon, max_lat, max_lon) -> List[House]:
        return self.session.query(House).filter(
            func.ST_Within(
                House.geom,
                func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            )
        ).all()
```

### 5.2 Design Patterns Used

| Pattern | Component | Purpose |
|---------|-----------|---------|
| **Repository** | Data access | Abstract database operations |
| **Service Layer** | Business logic | Encapsulate business rules |
| **Factory** | Object creation | Create complex objects (reports, calculators) |
| **Strategy** | Tax calculation | Different tax rules per category/region |
| **Observer** | Events | Notify on payment, status changes |
| **DTO** | API layer | Clean data transfer between layers |
| **Singleton** | Configuration | Single instance for config/connections |
| **Decorator** | Authentication | Route-level auth checks |

### 5.3 SOLID Principles Application

| Principle | Application |
|-----------|-------------|
| **S** - Single Responsibility | Each service handles one domain (HouseService, TaxService) |
| **O** - Open/Closed | Tax calculators extensible via strategy pattern |
| **L** - Liskov Substitution | Repository interfaces allow different implementations |
| **I** - Interface Segregation | Specific repository interfaces per entity |
| **D** - Dependency Inversion | Services depend on repository interfaces, not implementations |

---

## 6. DATABASE DESIGN

### 6.1 Entity-Relationship Diagram

```
┌─────────────────────────┐     ┌─────────────────────────┐
│        USERS            │     │    ADMIN_BOUNDARIES     │
├─────────────────────────┤     ├─────────────────────────┤
│ user_id (PK)            │     │ boundary_id (PK)        │
│ username                │     │ name_fr                 │
│ email                   │     │ name_en                 │
│ password_hash           │     │ boundary_type           │
│ role                    │     │ parent_boundary_id (FK) │
│ preferred_language      │     │ geom (GEOMETRY)         │
│ created_at              │     │ tax_rate                │
│ updated_at              │     │ population              │
└─────────────────────────┘     └───────────┬─────────────┘
                                            │
                                            │ contains
                                            ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│     TAX_CATEGORIES      │     │         HOUSES          │
├─────────────────────────┤     ├─────────────────────────┤
│ category_id (PK)        │◄────│ house_id (PK)           │
│ code                    │     │ immatriculation_number  │
│ name_fr                 │     │ geom (POINT)            │
│ name_en                 │     │ building_footprint      │
│ description_fr          │     │ address                 │
│ description_en          │     │ neighborhood            │
│ base_rate               │     │ commune                 │
└─────────────────────────┘     │ department              │
                                │ region                  │
                                │ building_type           │
                                │ building_levels         │
                                │ footprint_area          │
                                │ estimated_area          │
                                │ owner_name              │
                                │ owner_id                │
                                │ phone_number            │
                                │ email                   │
                                │ tax_category (FK)       │
                                │ base_tax_value          │
                                │ tax_rate                │
                                │ annual_tax              │
                                │ verification_status     │
                                │ source_data             │
                                │ confidence_score        │
                                │ created_at              │
                                │ updated_at              │
                                └───────────┬─────────────┘
                                            │
                                            │ 1:N
                                            ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│    HOUSE_DOCUMENTS      │     │     TAX_PAYMENTS        │
├─────────────────────────┤     ├─────────────────────────┤
│ document_id (PK)        │     │ payment_id (PK)         │
│ house_id (FK)           │     │ house_id (FK)           │
│ document_type           │     │ immatriculation_number  │
│ file_path               │     │ payment_year            │
│ uploaded_by             │     │ payment_period          │
│ uploaded_at             │     │ amount_due              │
└─────────────────────────┘     │ amount_paid             │
                                │ payment_date            │
                                │ payment_method          │
                                │ transaction_id          │
                                │ collected_by            │
                                │ notes                   │
                                │ created_at              │
                                └─────────────────────────┘
```

### 6.2 Complete Database Schema

```sql
-- ============================================
-- SCHEMA CREATION
-- ============================================
CREATE SCHEMA IF NOT EXISTS immatriculation;

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE immatriculation.users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    phone_number VARCHAR(20),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    -- Roles: admin, manager, tax_collector, field_agent, viewer
    preferred_language VARCHAR(2) DEFAULT 'fr',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ADMINISTRATIVE BOUNDARIES
-- ============================================
CREATE TABLE immatriculation.admin_boundaries (
    boundary_id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE,
    name_fr VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    boundary_type VARCHAR(50) NOT NULL,
    -- Types: region, department, commune, neighborhood
    parent_boundary_id INTEGER REFERENCES immatriculation.admin_boundaries(boundary_id),
    geom GEOMETRY(MultiPolygon, 4326),
    tax_rate DECIMAL(5,4) DEFAULT 0.01,
    population INTEGER,
    total_houses INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TAX CATEGORIES
-- ============================================
CREATE TABLE immatriculation.tax_categories (
    category_id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name_fr VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    description_fr TEXT,
    description_en TEXT,
    base_rate_per_sqm DECIMAL(10,2) DEFAULT 1000,
    tax_multiplier DECIMAL(5,2) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE
);

-- Default categories
INSERT INTO immatriculation.tax_categories (code, name_fr, name_en, description_fr, description_en, tax_multiplier)
VALUES 
    ('RESIDENTIAL', 'Résidentiel', 'Residential', 'Habitation principale', 'Primary residence', 1.0),
    ('COMMERCIAL', 'Commercial', 'Commercial', 'Usage commercial', 'Commercial use', 1.5),
    ('INDUSTRIAL', 'Industriel', 'Industrial', 'Usage industriel', 'Industrial use', 2.0),
    ('MIXED', 'Mixte', 'Mixed', 'Usage mixte', 'Mixed use', 1.25),
    ('GOVERNMENT', 'Gouvernemental', 'Government', 'Bâtiment public', 'Public building', 0.0);

-- ============================================
-- HOUSES TABLE (Main Entity)
-- ============================================
CREATE TABLE immatriculation.houses (
    house_id SERIAL PRIMARY KEY,
    immatriculation_number VARCHAR(50) UNIQUE,
    
    -- Spatial data
    geom GEOMETRY(Point, 4326),
    building_footprint GEOMETRY(Polygon, 4326),
    
    -- Location hierarchy
    address TEXT,
    neighborhood VARCHAR(100),
    commune VARCHAR(100),
    department VARCHAR(100),
    region VARCHAR(100),
    
    -- Building characteristics
    building_type VARCHAR(50),
    building_levels INTEGER DEFAULT 1,
    roof_material VARCHAR(50),
    wall_material VARCHAR(50),
    construction_year INTEGER,
    
    -- Size metrics (in square meters)
    footprint_area DECIMAL(10,2),
    estimated_area DECIMAL(10,2),
    land_area DECIMAL(10,2),
    
    -- Owner information
    owner_name VARCHAR(200),
    owner_id VARCHAR(50),
    phone_number VARCHAR(20),
    email VARCHAR(100),
    
    -- Tax information
    tax_category_id INTEGER REFERENCES immatriculation.tax_categories(category_id),
    base_tax_value DECIMAL(15,2),
    tax_rate DECIMAL(5,4),
    annual_tax DECIMAL(15,2),
    
    -- Status tracking
    immatriculation_date DATE,
    last_tax_payment DATE,
    payment_status VARCHAR(20) DEFAULT 'UNPAID',
    -- Status: PAID, PARTIAL, UNPAID, EXEMPT
    verification_status VARCHAR(20) DEFAULT 'PENDING',
    -- Status: PENDING, AUTO_DETECTED, VERIFIED, REJECTED
    
    -- Data source
    source_data VARCHAR(50) DEFAULT 'manual',
    -- Source: osm, satellite, field, manual
    confidence_score DECIMAL(3,2) DEFAULT 0.5,
    verified_by INTEGER REFERENCES immatriculation.users(user_id),
    verified_at TIMESTAMP,
    
    -- Audit fields
    created_by INTEGER REFERENCES immatriculation.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT enforce_srid_geom CHECK (ST_SRID(geom) = 4326),
    CONSTRAINT enforce_srid_footprint CHECK (building_footprint IS NULL OR ST_SRID(building_footprint) = 4326),
    CONSTRAINT valid_payment_status CHECK (payment_status IN ('PAID', 'PARTIAL', 'UNPAID', 'EXEMPT')),
    CONSTRAINT valid_verification_status CHECK (verification_status IN ('PENDING', 'AUTO_DETECTED', 'VERIFIED', 'REJECTED'))
);

-- ============================================
-- TAX PAYMENTS
-- ============================================
CREATE TABLE immatriculation.tax_payments (
    payment_id SERIAL PRIMARY KEY,
    house_id INTEGER REFERENCES immatriculation.houses(house_id) ON DELETE CASCADE,
    immatriculation_number VARCHAR(50),
    
    -- Payment period
    payment_year INTEGER NOT NULL,
    payment_period VARCHAR(20) DEFAULT 'ANNUAL',
    -- Period: Q1, Q2, Q3, Q4, ANNUAL
    
    -- Amounts
    amount_due DECIMAL(15,2) NOT NULL,
    amount_paid DECIMAL(15,2) NOT NULL,
    penalty_amount DECIMAL(15,2) DEFAULT 0,
    
    -- Transaction details
    payment_date DATE NOT NULL,
    payment_method VARCHAR(50),
    -- Methods: CASH, MOBILE_MONEY_MTN, MOBILE_MONEY_ORANGE, BANK_TRANSFER, CHECK
    transaction_id VARCHAR(100),
    receipt_number VARCHAR(50) UNIQUE,
    
    -- Collection info
    collected_by INTEGER REFERENCES immatriculation.users(user_id),
    collection_point VARCHAR(100),
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- HOUSE DOCUMENTS
-- ============================================
CREATE TABLE immatriculation.house_documents (
    document_id SERIAL PRIMARY KEY,
    house_id INTEGER REFERENCES immatriculation.houses(house_id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    -- Types: PHOTO, CERTIFICATE, DEED, OTHER
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    file_size INTEGER,
    mime_type VARCHAR(100),
    description TEXT,
    uploaded_by INTEGER REFERENCES immatriculation.users(user_id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- VERIFICATION HISTORY
-- ============================================
CREATE TABLE immatriculation.verification_history (
    verification_id SERIAL PRIMARY KEY,
    house_id INTEGER REFERENCES immatriculation.houses(house_id) ON DELETE CASCADE,
    verified_by INTEGER REFERENCES immatriculation.users(user_id),
    verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    gps_latitude DECIMAL(10,8),
    gps_longitude DECIMAL(11,8),
    notes TEXT,
    device_info VARCHAR(200)
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_houses_geom ON immatriculation.houses USING GIST(geom);
CREATE INDEX idx_houses_footprint ON immatriculation.houses USING GIST(building_footprint);
CREATE INDEX idx_houses_immat ON immatriculation.houses(immatriculation_number);
CREATE INDEX idx_houses_location ON immatriculation.houses(region, department, commune);
CREATE INDEX idx_houses_status ON immatriculation.houses(payment_status, verification_status);
CREATE INDEX idx_houses_owner ON immatriculation.houses(owner_name, owner_id);
CREATE INDEX idx_payments_house ON immatriculation.tax_payments(house_id);
CREATE INDEX idx_payments_year ON immatriculation.tax_payments(payment_year);
CREATE INDEX idx_payments_date ON immatriculation.tax_payments(payment_date);
CREATE INDEX idx_boundaries_geom ON immatriculation.admin_boundaries USING GIST(geom);
CREATE INDEX idx_boundaries_type ON immatriculation.admin_boundaries(boundary_type);

-- ============================================
-- TRIGGERS
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_houses_timestamp
    BEFORE UPDATE ON immatriculation.houses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON immatriculation.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_boundaries_timestamp
    BEFORE UPDATE ON immatriculation.admin_boundaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- FUNCTIONS
-- ============================================

-- Generate immatriculation number
CREATE OR REPLACE FUNCTION generate_immatriculation_number(
    p_region_code VARCHAR(3),
    p_commune_code VARCHAR(5)
) RETURNS VARCHAR(50) AS $$
DECLARE
    v_sequence INTEGER;
BEGIN
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(immatriculation_number FROM '[0-9]+$') AS INTEGER)
    ), 0) + 1
    INTO v_sequence
    FROM immatriculation.houses
    WHERE immatriculation_number LIKE 'CMR-' || p_region_code || '-' || p_commune_code || '-%';
    
    RETURN 'CMR-' || p_region_code || '-' || p_commune_code || '-' || LPAD(v_sequence::TEXT, 7, '0');
END;
$$ LANGUAGE plpgsql;

-- Calculate annual tax
CREATE OR REPLACE FUNCTION calculate_annual_tax(
    p_estimated_area DECIMAL,
    p_tax_category_id INTEGER,
    p_commune VARCHAR
) RETURNS DECIMAL AS $$
DECLARE
    v_base_rate DECIMAL;
    v_multiplier DECIMAL;
    v_commune_rate DECIMAL;
BEGIN
    -- Get category rates
    SELECT base_rate_per_sqm, tax_multiplier
    INTO v_base_rate, v_multiplier
    FROM immatriculation.tax_categories
    WHERE category_id = p_tax_category_id;
    
    -- Get commune tax rate
    SELECT COALESCE(tax_rate, 0.01)
    INTO v_commune_rate
    FROM immatriculation.admin_boundaries
    WHERE name_fr = p_commune AND boundary_type = 'commune';
    
    RETURN p_estimated_area * v_base_rate * v_multiplier * v_commune_rate;
END;
$$ LANGUAGE plpgsql;
```

---

## 7. API SPECIFICATION

### 7.1 API Overview

| Endpoint Group | Base Path | Description |
|----------------|-----------|-------------|
| Authentication | `/api/v1/auth` | Login, logout, token refresh |
| Houses | `/api/v1/houses` | House CRUD operations |
| Payments | `/api/v1/payments` | Payment processing |
| Users | `/api/v1/users` | User management |
| Reports | `/api/v1/reports` | Report generation |
| Verification | `/api/v1/verification` | Field verification |
| Admin | `/api/v1/admin` | Administrative functions |

### 7.2 Authentication Endpoints

```
POST   /api/v1/auth/login           # User login
POST   /api/v1/auth/logout          # User logout
POST   /api/v1/auth/refresh         # Refresh JWT token
GET    /api/v1/auth/me              # Get current user info
PUT    /api/v1/auth/password        # Change password
```

### 7.3 Houses Endpoints

```
GET    /api/v1/houses               # List houses (paginated)
GET    /api/v1/houses/{id}          # Get house by ID
GET    /api/v1/houses/immat/{num}   # Get house by immatriculation number
POST   /api/v1/houses               # Create new house
PUT    /api/v1/houses/{id}          # Update house
DELETE /api/v1/houses/{id}          # Delete house

# Spatial queries
GET    /api/v1/houses/nearby        # Get houses near coordinates
GET    /api/v1/houses/bounds        # Get houses within bounding box
GET    /api/v1/houses/commune/{name}# Get houses in commune

# Search
GET    /api/v1/houses/search        # Search houses
```

### 7.4 Request/Response Examples

#### Create House

```http
POST /api/v1/houses
Content-Type: application/json
Authorization: Bearer {token}
Accept-Language: fr

{
    "address": "Rue de la Paix, Quartier Bastos",
    "commune": "Yaoundé I",
    "department": "Mfoundi",
    "region": "Centre",
    "building_type": "villa",
    "building_levels": 2,
    "footprint_area": 150.5,
    "owner_name": "Jean Dupont",
    "phone_number": "+237699123456",
    "tax_category_code": "RESIDENTIAL",
    "coordinates": {
        "latitude": 3.8667,
        "longitude": 11.5167
    }
}
```

#### Response

```json
{
    "status": "success",
    "message": "Maison enregistrée avec succès",
    "data": {
        "house_id": 12345,
        "immatriculation_number": "CMR-CE-YDE1-0012345",
        "address": "Rue de la Paix, Quartier Bastos",
        "commune": "Yaoundé I",
        "annual_tax": 45150.00,
        "verification_status": "PENDING",
        "created_at": "2026-02-06T10:30:00Z"
    }
}
```

### 7.5 Error Response Format

```json
{
    "status": "error",
    "code": "HOUSE_NOT_FOUND",
    "message": "Numéro d'immatriculation invalide",
    "details": {
        "immatriculation_number": "CMR-CE-YDE1-9999999"
    }
}
```

---

## 8. FRONTEND APPLICATIONS

### 8.0 Interface Overview

```
+-----------------------------------------------------------+
|                      INTERFACES (3)                       |
+-----------------+-----------------+-----------------------+
|   Admin Web     |   Citizen Web   |    Agent Mobile       |
|   (React.js)    |   (Next.js)     |    (Flutter)          |
|                 |   (Responsive)  |                       |
|   Desktop only  |  Desktop+Mobile |    Mobile only        |
+-----------------+-----------------+-----------------------+
         |                 |                   |
         +-----------------+-------------------+
                           |
                     Flask REST API
```

### 8.1 Admin Dashboard (React.js)

#### Features

| Module | Features |
|--------|----------|
| **Dashboard** | Statistics overview, recent activities, map view |
| **House Management** | CRUD operations, bulk import/export, spatial search |
| **User Management** | User CRUD, role assignment, activity logs |
| **Payment Management** | Record payments, generate receipts, reconciliation |
| **Reports** | Generate and export reports (PDF, Excel) |
| **System Settings** | Tax rates, categories, boundaries management |

#### Key Components

```
admin/src/
├── components/
│   ├── common/
│   │   ├── LanguageSwitcher.jsx
│   │   ├── PageHeader.jsx
│   │   ├── DataTable.jsx
│   │   └── MapView.jsx
│   ├── houses/
│   │   ├── HouseList.jsx
│   │   ├── HouseForm.jsx
│   │   ├── HouseDetail.jsx
│   │   └── HouseMap.jsx
│   ├── payments/
│   │   ├── PaymentList.jsx
│   │   ├── PaymentForm.jsx
│   │   └── ReceiptPrint.jsx
│   └── dashboard/
│       ├── StatCards.jsx
│       ├── RecentActivity.jsx
│       └── HeatMap.jsx
├── pages/
│   ├── DashboardPage.jsx
│   ├── HousesPage.jsx
│   ├── PaymentsPage.jsx
│   ├── UsersPage.jsx
│   └── ReportsPage.jsx
└── ...
```

### 8.2 Citizen Portal (Next.js - Responsive)

**Important:** This is a responsive web application that works on both desktop computers and mobile phones. Citizens do NOT need a separate mobile app.

#### Features

| Feature | Description |
|---------|-------------|
| **Property Lookup** | Search by immatriculation number or owner info |
| **Tax Status** | View current tax obligations and payment history |
| **Online Payment** | Pay via mobile money (MTN, Orange) or bank |
| **Certificate Download** | Download immatriculation certificate (PDF) |
| **Update Request** | Submit property information update requests |
| **Notifications** | Email/SMS alerts for tax due dates |

#### Responsive Design

- Desktop: Full-featured dashboard layout
- Tablet: Adapted navigation and forms
- Mobile: Bottom navigation, touch-optimized

### 8.3 Field Agent Mobile App (Flutter)

**Important:** This mobile app is exclusively for field verification agents. It requires features that only work on native mobile apps (GPS, camera, offline storage).

#### Features

| Feature | Description |
|---------|-------------|
| **GPS Navigation** | Navigate to assigned houses |
| **Offline Mode** | Work without internet connection (critical for remote areas) |
| **Camera Integration** | Capture photos of properties |
| **Form Submission** | Complete verification forms |
| **Data Sync** | Automatic sync when online |
| **Payment Collection** | Record cash payments in the field |
| **Task Assignment** | Receive and manage verification tasks |

#### Key Screens

```
mobile/lib/screens/
├── auth/
│   ├── login_screen.dart
│   └── splash_screen.dart
├── home/
│   ├── home_screen.dart
│   └── dashboard_screen.dart
├── houses/
│   ├── house_list_screen.dart
│   ├── house_detail_screen.dart
│   ├── house_map_screen.dart
│   └── verification_screen.dart
├── payments/
│   ├── payment_form_screen.dart
│   └── receipt_screen.dart
└── settings/
    ├── settings_screen.dart
    └── language_screen.dart
```

---

## 9. INTERNATIONALIZATION (i18n)

### 9.1 Supported Languages

| Language | Code | Status |
|----------|------|--------|
| French | `fr` | Primary (default) |
| English | `en` | Secondary |

### 9.2 Translation Coverage

| Component | Method |
|-----------|--------|
| **Backend API** | Flask-Babel (.po files) |
| **React Web** | react-i18next (JSON files) |
| **Flutter Mobile** | flutter_localizations (ARB files) |
| **Database Content** | Bilingual columns (name_fr, name_en) |
| **PDF Documents** | Dual templates |
| **SMS/Email** | Template per language |

### 9.3 Language Selection Priority

1. URL parameter (`?lang=en`)
2. HTTP Accept-Language header
3. User preference (stored in profile)
4. Default (French)

### 9.4 Sample Translation Structure

```json
// French (fr)
{
    "house": {
        "title": "Gestion des Maisons",
        "immatriculation_number": "Numéro d'immatriculation",
        "owner_name": "Nom du propriétaire",
        "tax_due": "Impôt dû"
    },
    "status": {
        "paid": "Payé",
        "unpaid": "Non payé",
        "verified": "Vérifié"
    }
}

// English (en)
{
    "house": {
        "title": "House Management",
        "immatriculation_number": "Immatriculation Number",
        "owner_name": "Owner Name",
        "tax_due": "Tax Due"
    },
    "status": {
        "paid": "Paid",
        "unpaid": "Unpaid",
        "verified": "Verified"
    }
}
```

---

## 10. CACHING ARCHITECTURE

### 10.1 Why Caching is Critical

| Problem | Without Cache | With Cache (Redis) |
|---------|---------------|-------------------|
| Tax calculation for same house | Hits DB every request | Instant from cache |
| Map tile rendering (thousands of houses) | Slow spatial queries | Sub-second response |
| Dashboard statistics | Aggregates millions of rows | Pre-computed, instant |
| Commune/Region lookup | Repeated DB joins | Cached reference data |
| User session validation | JWT decode + DB check every time | Redis session lookup |
| API rate limiting | Complex logic per request | Redis counter |

**Expected improvement:** 5-10x faster on read-heavy operations (90%+ of all requests).

### 10.2 Caching Layers

```
+-------------------------------------------------------------------+
|                        CACHING LAYERS                             |
+-------------------------------------------------------------------+
|                                                                   |
|  Layer 1: REFERENCE DATA CACHE (TTL: 24 hours)                   |
|  Data: Regions, Communes, Tax Categories, Commune Codes          |
|  Why: Read 1000x for every 1 write                               |
|                                                                   |
|  Layer 2: DASHBOARD STATS CACHE (TTL: 15 minutes)                |
|  Data: Total houses, payment stats, regional summaries           |
|  Why: Heavy aggregation queries on millions of rows              |
|                                                                   |
|  Layer 3: SPATIAL QUERY CACHE (TTL: 10 minutes)                  |
|  Data: Houses within bounding box per zoom level                 |
|  Why: PostGIS spatial queries on large datasets are expensive    |
|                                                                   |
|  Layer 4: TAX CALCULATION CACHE (TTL: Until params change)       |
|  Data: Annual tax per house                                      |
|  Why: Recalculating = multiple table joins every request         |
|                                                                   |
|  Layer 5: AUTH SESSION CACHE (TTL: 1 hour)                       |
|  Data: JWT token validation, user permissions                    |
|  Why: Every API request needs auth check                         |
|                                                                   |
|  Layer 6: RATE LIMITING (TTL: 1 minute sliding window)           |
|  Data: Request counts per IP/user                                |
|  Why: Prevent abuse, DDoS protection                             |
|                                                                   |
+-------------------------------------------------------------------+
```

### 10.3 Cache Summary Table

| Cache Layer | Key Pattern | TTL | Invalidation |
|-------------|-------------|-----|--------------|
| Reference data | `ref:communes`, `ref:regions`, `ref:tax_categories` | 24 hours | On admin update |
| Dashboard stats | `dash:stats:{region}` | 15 minutes | Auto-expire |
| Map / Spatial | `map:{zoom}:{bounds_hash}` | 10 minutes | Auto-expire |
| Tax calculations | `tax:{house_id}:{year}` | Until changed | On tax param update |
| Auth sessions | `auth:user:{user_id}` | 1 hour | On logout |
| Rate limits | `rate:{ip}:{endpoint}` | 1 minute | Auto-expire |

### 10.4 What NOT to Cache

| Data | Reason |
|------|--------|
| Payment transactions | Must always be real-time and accurate |
| Verification updates | Field agents need latest data |
| Owner personal info | Security risk if stale |
| Write operations | Must go directly to DB |

### 10.5 Cache Implementation

```python
# app/core/cache.py
import redis
import json
from functools import wraps

cache = redis.Redis(host='redis', port=6379, db=0)

def cached(ttl=300, prefix=''):
    """Cache decorator - TTL in seconds"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            result = cache.get(key)
            if result:
                return json.loads(result)
            result = func(*args, **kwargs)
            cache.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator

def invalidate_cache(prefix):
    """Clear all cached keys with a given prefix"""
    keys = cache.keys(f'{prefix}:*')
    if keys:
        cache.delete(*keys)
```

```python
# Usage in services
class DashboardService:
    @cached(ttl=900, prefix='dashboard')  # 15 min
    def get_statistics(self, region=None):
        return self.repo.aggregate_stats(region)

    @cached(ttl=86400, prefix='ref')  # 24h
    def get_all_communes(self):
        return self.repo.get_communes()

    @cached(ttl=600, prefix='map')  # 10 min
    def get_houses_in_bounds(self, min_lat, min_lon, max_lat, max_lon):
        return self.house_repo.find_in_bounds(min_lat, min_lon, max_lat, max_lon)

class TaxService:
    @cached(ttl=3600, prefix='tax')  # 1h
    def calculate_annual_tax(self, house_id, year):
        return self.repo.compute_tax(house_id, year)
    
    def update_tax_parameters(self):
        """When tax params change, invalidate all tax caches"""
        invalidate_cache('tax')
        invalidate_cache('dashboard')
```

### 10.6 Redis Configuration in Docker

```yaml
# Already in docker-compose.prod.yml
redis:
  image: redis:7-alpine
  container_name: immat_redis
  restart: always
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
  networks:
    - immat_network
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

---

## 11. SECURITY ARCHITECTURE

### 10.1 Authentication & Authorization

| Component | Implementation |
|-----------|----------------|
| **Authentication** | JWT (JSON Web Tokens) |
| **Password Storage** | bcrypt hashing |
| **Session Management** | Redis-backed sessions |
| **RBAC** | Role-based access control |

### 10.2 User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full system access |
| **manager** | Manage users, view all data, reports |
| **tax_collector** | Record payments, view houses |
| **field_agent** | Verify houses, update field data |
| **viewer** | Read-only access |

### 10.3 Security Measures

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Network                                            │
│  • Firewall (ports 80, 443 only)                            │
│  • SSL/TLS encryption (certificates)                        │
│  • DDoS protection (Nginx rate limiting)                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Application                                        │
│  • JWT authentication                                        │
│  • CORS configuration                                        │
│  • Input validation (schemas)                               │
│  • SQL injection prevention (ORM)                           │
│  • XSS prevention (React escaping)                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Data                                               │
│  • Database access control                                   │
│  • Encrypted backups                                         │
│  • Audit logging                                             │
│  • Data masking for sensitive fields                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. DEPLOYMENT ARCHITECTURE

### 11.1 On-Premise Docker Deployment

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GOVERNMENT DATA CENTER                            │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     PRODUCTION SERVER                            │    │
│  │                     (Ubuntu 22.04 LTS)                           │    │
│  │                     16-32 GB RAM, 8 cores, 500GB SSD             │    │
│  │                                                                  │    │
│  │   ┌──────────────────────────────────────────────────────────┐  │    │
│  │   │                    DOCKER ENGINE                          │  │    │
│  │   │                                                           │  │    │
│  │   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │    │
│  │   │  │  Nginx  │ │  Flask  │ │  Flask  │ │  Flask  │        │  │    │
│  │   │  │  Proxy  │ │  API 1  │ │  API 2  │ │  API 3  │        │  │    │
│  │   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘        │  │    │
│  │   │       │           └──────┬────┴──────┬────┘              │  │    │
│  │   │       │                  │           │                   │  │    │
│  │   │  ┌────┴────────────┐ ┌───┴───┐ ┌─────┴─────┐            │  │    │
│  │   │  │  Static Assets  │ │ Redis │ │   MinIO   │            │  │    │
│  │   │  └─────────────────┘ └───────┘ └───────────┘            │  │    │
│  │   │                                                          │  │    │
│  │   │  ┌───────────────────────────────────────────┐          │  │    │
│  │   │  │            PostgreSQL + PostGIS           │          │  │    │
│  │   │  └───────────────────────────────────────────┘          │  │    │
│  │   └──────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     BACKUP SERVER                                │    │
│  │         8GB RAM, 4 cores, 1TB HDD                                │    │
│  │         PostgreSQL Replica + File Backups                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Docker Compose Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: immat_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - admin-web
      - citizen-web
    networks:
      - immat_network

  api:
    build: ./backend
    container_name: immat_api
    restart: always
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/immatriculation
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - immat_network
    deploy:
      replicas: 3

  db:
    image: postgis/postgis:15-3.3
    container_name: immat_db
    restart: always
    environment:
      - POSTGRES_DB=immatriculation
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - immat_network

  redis:
    image: redis:7-alpine
    container_name: immat_redis
    restart: always
    networks:
      - immat_network

  minio:
    image: minio/minio:latest
    container_name: immat_minio
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - immat_network

  admin-web:
    build: ./frontend/admin
    container_name: immat_admin
    restart: always
    networks:
      - immat_network

  citizen-web:
    build: ./frontend/citizen
    container_name: immat_citizen
    restart: always
    networks:
      - immat_network

  db-backup:
    image: prodrigestivill/postgres-backup-local
    environment:
      - POSTGRES_HOST=db
      - POSTGRES_DB=immatriculation
      - SCHEDULE=@daily
      - BACKUP_KEEP_DAYS=30
    volumes:
      - ./backups:/backups
    networks:
      - immat_network

volumes:
  postgres_data:
  minio_data:

networks:
  immat_network:
    driver: bridge
```

### 11.3 Deployment Commands

```bash
# Initial deployment
git clone https://github.com/your-repo/immatriculation.git
cd immatriculation
cp .env.example .env  # Configure environment
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Database migration
docker-compose exec api flask db upgrade

# View logs
docker-compose logs -f api

# Scale API
docker-compose up -d --scale api=5

# Update deployment
git pull
docker-compose build
docker-compose up -d
```

---

## 13. TEST-DRIVEN DEVELOPMENT PLAN

### 13.0 Development Principle

**GOLDEN RULE: Nothing moves forward until the current step passes ALL tests with ZERO errors.**

```
For EVERY step below:
  1. Write the code
  2. Write the test for that code
  3. Run the test --> Must PASS
  4. Run error checks --> Must be ZERO errors
  5. Commit to Git
  6. Only then proceed to next step
```

### 13.1 Complete Step-by-Step Development Plan

---

#### SPRINT 1: PROJECT FOUNDATION (Days 1-3)

##### Step 1.1: Initialize Project Structure

**Action:** Create the complete folder structure and initialize Git

```bash
# Create root project
mkdir ImmatriculationSystem && cd ImmatriculationSystem
git init

# Backend structure
mkdir -p backend/app/{api/routes,api/schemas,services,repositories,models,core,utils,translations/{fr/LC_MESSAGES,en/LC_MESSAGES}}
mkdir -p backend/{migrations,tests/{unit,integration,e2e}}

# Frontend structure
mkdir -p frontend/{admin/src,citizen/src}

# Infrastructure
mkdir -p docker/{nginx,postgres/init}
mkdir -p backups docs scripts
```

**Test:**
```bash
# Verify all directories exist
test -d backend/app/api/routes && echo "PASS" || echo "FAIL"
test -d backend/app/services && echo "PASS" || echo "FAIL"
test -d backend/app/repositories && echo "PASS" || echo "FAIL"
test -d backend/app/models && echo "PASS" || echo "FAIL"
test -d backend/app/core && echo "PASS" || echo "FAIL"
test -d backend/tests && echo "PASS" || echo "FAIL"
test -d frontend/admin && echo "PASS" || echo "FAIL"
test -d frontend/citizen && echo "PASS" || echo "FAIL"
```

**Exit Criteria:** All directories exist. Git initialized.

---

##### Step 1.2: Docker Development Environment

**Action:** Create docker-compose.dev.yml with PostgreSQL/PostGIS, Redis, MinIO

**Test:**
```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml ps  # All services "Up"
docker-compose exec db psql -U immat_user -d immatriculation -c "SELECT PostGIS_version();"  # PostGIS works
docker-compose exec redis redis-cli ping  # Returns PONG
```

**Exit Criteria:** All 3 containers running. PostGIS responding. Redis responding.

---

##### Step 1.3: Python Environment & Dependencies

**Action:** Create requirements.txt, install all packages, create virtual environment

```
# requirements.txt
flask==3.0.0
flask-sqlalchemy==3.1.1
flask-migrate==4.0.5
flask-jwt-extended==4.6.0
flask-babel==4.0.0
flask-cors==4.0.0
flask-marshmallow==1.2.0
marshmallow-sqlalchemy==1.0.0
geoalchemy2==0.14.3
psycopg2-binary==2.9.9
redis==5.0.1
gunicorn==21.2.0
python-dotenv==1.0.0
celery==5.3.6
pytest==7.4.3
pytest-flask==1.3.0
pytest-cov==4.1.0
fakeredis==2.20.0
factory-boy==3.3.0
```

**Test:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -c "import flask; import sqlalchemy; import redis; import geoalchemy2; print('ALL IMPORTS OK')"
```

**Exit Criteria:** All packages installed. All imports succeed.

---

##### Step 1.4: Flask Application Factory

**Action:** Create app/__init__.py with create_app() factory

**Test:**
```python
# backend/tests/test_app.py
def test_app_creation(app):
    assert app is not None
    assert app.config['TESTING'] is True

def test_app_has_extensions(app):
    assert 'sqlalchemy' in app.extensions
    assert 'migrate' in app.extensions

def test_health_endpoint(client):
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
```

```bash
cd backend && pytest tests/test_app.py -v
# Expected: 3 passed, 0 failed
```

**Exit Criteria:** Flask app starts. Health endpoint returns 200. All tests pass.

---

##### Step 1.5: Configuration Management

**Action:** Create config.py with Development, Testing, Production configs

**Test:**
```python
# backend/tests/test_config.py
def test_development_config():
    app = create_app('development')
    assert app.config['DEBUG'] is True
    assert 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']

def test_testing_config():
    app = create_app('testing')
    assert app.config['TESTING'] is True

def test_production_config():
    app = create_app('production')
    assert app.config['DEBUG'] is False
```

```bash
pytest tests/test_config.py -v
# Expected: 3 passed, 0 failed
```

**Exit Criteria:** All 3 configs load correctly. Tests pass.

---

#### SPRINT 2: DATABASE & MODELS (Days 4-7)

##### Step 2.1: Database Schema Migration

**Action:** Create the complete SQL schema via Alembic migrations

**Test:**
```bash
cd backend
flask db init
flask db migrate -m "Initial schema creation"
flask db upgrade

# Verify all tables exist
docker-compose exec db psql -U immat_user -d immatriculation -c "\dt immatriculation.*"
# Expected: users, houses, tax_payments, tax_categories, admin_boundaries, house_documents, verification_history
```

```python
# backend/tests/test_database.py
def test_all_tables_exist(db_session):
    from sqlalchemy import inspect
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names(schema='immatriculation')
    assert 'users' in tables
    assert 'houses' in tables
    assert 'tax_payments' in tables
    assert 'tax_categories' in tables
    assert 'admin_boundaries' in tables
    assert 'house_documents' in tables

def test_postgis_enabled(db_session):
    result = db_session.execute(text("SELECT PostGIS_version()"))
    assert result is not None
```

```bash
pytest tests/test_database.py -v
# Expected: 2 passed, 0 failed
```

**Exit Criteria:** All 7 tables created. PostGIS extension active. All tests pass.

---

##### Step 2.2: SQLAlchemy Models

**Action:** Create all ORM models: User, House, TaxPayment, TaxCategory, AdminBoundary

**Test:**
```python
# backend/tests/unit/test_models.py
def test_user_model_creation(db_session):
    user = User(username='agent1', email='agent@gov.cm', role='field_agent')
    user.set_password('secure123')
    db_session.add(user)
    db_session.commit()
    assert user.user_id is not None
    assert user.check_password('secure123') is True
    assert user.preferred_language == 'fr'

def test_house_model_creation(db_session):
    house = House(
        immatriculation_number='CMR-CE-YDE1-0000001',
        commune='Yaounde I',
        region='Centre',
        footprint_area=150.5,
        building_levels=2
    )
    db_session.add(house)
    db_session.commit()
    assert house.house_id is not None
    assert house.verification_status == 'PENDING'
    assert house.payment_status == 'UNPAID'

def test_tax_category_defaults(db_session):
    categories = TaxCategory.query.all()
    assert len(categories) >= 5  # RESIDENTIAL, COMMERCIAL, INDUSTRIAL, MIXED, GOVERNMENT
    residential = TaxCategory.query.filter_by(code='RESIDENTIAL').first()
    assert residential.name_fr == 'Residentiel'
    assert residential.name_en == 'Residential'

def test_house_payment_relationship(db_session):
    house = House(immatriculation_number='CMR-CE-YDE1-0000002', commune='Yaounde I')
    payment = TaxPayment(payment_year=2026, amount_due=50000, amount_paid=50000, payment_date=date.today())
    house.payments.append(payment)
    db_session.add(house)
    db_session.commit()
    assert len(house.payments) == 1
```

```bash
pytest tests/unit/test_models.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** All models create, save, relate correctly. All tests pass.

---

##### Step 2.3: Spatial Model Features (PostGIS)

**Action:** Add geometry columns and spatial methods to House model

**Test:**
```python
# backend/tests/unit/test_spatial.py
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

def test_house_with_geometry(db_session):
    point = from_shape(Point(11.5167, 3.8667), srid=4326)
    house = House(
        immatriculation_number='CMR-CE-YDE1-0000003',
        geom=point,
        commune='Yaounde I'
    )
    db_session.add(house)
    db_session.commit()
    assert house.geom is not None

def test_spatial_query_nearby(db_session):
    """Test finding houses within radius"""
    # Create houses at known locations
    houses = create_houses_at_locations(db_session)
    
    # Query houses within 500m of test point
    nearby = House.query.filter(
        func.ST_DWithin(
            func.ST_Transform(House.geom, 32633),
            func.ST_Transform(func.ST_SetSRID(func.ST_MakePoint(11.5167, 3.8667), 4326), 32633),
            500
        )
    ).all()
    assert len(nearby) > 0
```

```bash
pytest tests/unit/test_spatial.py -v
# Expected: 2 passed, 0 failed
```

**Exit Criteria:** Spatial queries work. Houses can be queried by location.

---

#### SPRINT 3: CORE BACKEND - REPOSITORIES & SERVICES (Days 8-14)

##### Step 3.1: Base Repository

**Action:** Create BaseRepository abstract class

**Test:**
```python
# backend/tests/unit/test_base_repository.py
def test_base_repository_get_by_id(db_session, user_repo):
    user = create_test_user(db_session)
    found = user_repo.get_by_id(user.user_id)
    assert found is not None
    assert found.username == user.username

def test_base_repository_get_all(db_session, user_repo):
    create_test_users(db_session, count=5)
    users = user_repo.get_all()
    assert len(users) == 5

def test_base_repository_create(user_repo):
    user = User(username='new_user', email='new@gov.cm')
    created = user_repo.create(user)
    assert created.user_id is not None

def test_base_repository_delete(db_session, user_repo):
    user = create_test_user(db_session)
    result = user_repo.delete(user.user_id)
    assert result is True
    assert user_repo.get_by_id(user.user_id) is None
```

```bash
pytest tests/unit/test_base_repository.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** CRUD operations work via repository. All tests pass.

---

##### Step 3.2: House Repository

**Action:** Create HouseRepository with spatial queries

**Test:**
```python
# backend/tests/unit/test_house_repository.py
def test_get_by_immatriculation(db_session, house_repo):
    house = create_test_house(db_session, 'CMR-CE-YDE1-0000010')
    found = house_repo.get_by_immatriculation('CMR-CE-YDE1-0000010')
    assert found is not None
    assert found.house_id == house.house_id

def test_find_in_commune(db_session, house_repo):
    create_test_houses_in_commune(db_session, 'Yaounde I', 10)
    create_test_houses_in_commune(db_session, 'Douala I', 5)
    houses = house_repo.find_by_commune('Yaounde I')
    assert len(houses) == 10

def test_find_in_bounds(db_session, house_repo):
    create_test_houses_with_coords(db_session)
    houses = house_repo.find_in_bounds(3.85, 11.50, 3.90, 11.55)
    assert len(houses) > 0

def test_count_by_status(db_session, house_repo):
    create_houses_various_statuses(db_session)
    counts = house_repo.count_by_status()
    assert 'VERIFIED' in counts
    assert 'PENDING' in counts
```

```bash
pytest tests/unit/test_house_repository.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** All house queries work including spatial. Tests pass.

---

##### Step 3.3: Payment Repository

**Action:** Create PaymentRepository

**Test:**
```python
# backend/tests/unit/test_payment_repository.py
def test_create_payment(db_session, payment_repo):
    house = create_test_house(db_session)
    payment = payment_repo.create_payment(
        house_id=house.house_id,
        amount_due=50000, amount_paid=50000,
        payment_year=2026, payment_method='MOBILE_MONEY_MTN'
    )
    assert payment.payment_id is not None
    assert payment.receipt_number is not None

def test_get_payments_by_house(db_session, payment_repo):
    house = create_test_house(db_session)
    create_payments(db_session, house.house_id, count=3)
    payments = payment_repo.get_by_house(house.house_id)
    assert len(payments) == 3

def test_get_total_paid_by_year(db_session, payment_repo):
    house = create_test_house(db_session)
    create_payments(db_session, house.house_id, amounts=[20000, 15000, 15000], year=2026)
    total = payment_repo.total_paid_for_year(house.house_id, 2026)
    assert total == 50000
```

```bash
pytest tests/unit/test_payment_repository.py -v
# Expected: 3 passed, 0 failed
```

**Exit Criteria:** Payment CRUD works. Totals calculate correctly.

---

##### Step 3.4: Immatriculation Service

**Action:** Create ImmatriculationService with number generation logic

**Test:**
```python
# backend/tests/unit/test_immatriculation_service.py
def test_generate_immatriculation_number(immat_service):
    num = immat_service.generate_number('CE', 'YDE1')
    assert num.startswith('CMR-CE-YDE1-')
    assert len(num) == 20  # CMR-CE-YDE1-0000001

def test_sequential_numbers(immat_service, db_session):
    num1 = immat_service.generate_number('CE', 'YDE1')
    create_house_with_immat(db_session, num1)
    num2 = immat_service.generate_number('CE', 'YDE1')
    seq1 = int(num1.split('-')[-1])
    seq2 = int(num2.split('-')[-1])
    assert seq2 == seq1 + 1

def test_different_communes_independent(immat_service, db_session):
    num_yde = immat_service.generate_number('CE', 'YDE1')
    num_dla = immat_service.generate_number('LT', 'DLA1')
    assert 'YDE1' in num_yde
    assert 'DLA1' in num_dla

def test_validate_immatriculation_format(immat_service):
    assert immat_service.validate_format('CMR-CE-YDE1-0000001') is True
    assert immat_service.validate_format('INVALID') is False
    assert immat_service.validate_format('CMR-XX-YDE1-0000001') is False  # Invalid region
```

```bash
pytest tests/unit/test_immatriculation_service.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** Numbers generate correctly, sequentially, independently per commune.

---

##### Step 3.5: Tax Service

**Action:** Create TaxService with calculation logic

**Test:**
```python
# backend/tests/unit/test_tax_service.py
def test_calculate_residential_tax(tax_service, db_session):
    house = create_house(db_session, area=150, levels=2, category='RESIDENTIAL')
    tax = tax_service.calculate_annual_tax(house.house_id, 2026)
    assert tax > 0
    assert isinstance(tax, float)

def test_commercial_higher_than_residential(tax_service, db_session):
    res = create_house(db_session, area=100, category='RESIDENTIAL')
    com = create_house(db_session, area=100, category='COMMERCIAL')
    tax_res = tax_service.calculate_annual_tax(res.house_id, 2026)
    tax_com = tax_service.calculate_annual_tax(com.house_id, 2026)
    assert tax_com > tax_res

def test_government_exempt(tax_service, db_session):
    gov = create_house(db_session, area=200, category='GOVERNMENT')
    tax = tax_service.calculate_annual_tax(gov.house_id, 2026)
    assert tax == 0

def test_penalty_calculation(tax_service):
    penalty = tax_service.calculate_penalty(50000, months_late=3, rate=0.05)
    assert penalty == 7500  # 50000 * 0.05 * 3
```

```bash
pytest tests/unit/test_tax_service.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** Tax calculations correct for all categories. Penalties accurate.

---

##### Step 3.6: Cache Service (Redis)

**Action:** Create cache module with decorator and invalidation

**Test:**
```python
# backend/tests/unit/test_cache.py
import fakeredis

def test_cache_decorator_stores_result(fake_redis):
    @cached(ttl=300, prefix='test')
    def expensive_function():
        return {'result': 42}
    
    result1 = expensive_function()  # Cache MISS -> executes function
    result2 = expensive_function()  # Cache HIT -> from Redis
    assert result1 == result2
    assert result1 == {'result': 42}

def test_cache_ttl_expiry(fake_redis):
    @cached(ttl=1, prefix='test')
    def short_lived():
        return {'data': 'fresh'}
    
    result1 = short_lived()
    time.sleep(2)
    # After TTL, cache should miss and re-execute
    result2 = short_lived()
    assert result1 == result2

def test_cache_invalidation(fake_redis):
    @cached(ttl=300, prefix='dashboard')
    def get_stats():
        return {'total': 100}
    
    get_stats()  # Populate cache
    invalidate_cache('dashboard')  # Clear
    
    keys = fake_redis.keys('dashboard:*')
    assert len(keys) == 0

def test_cache_different_args(fake_redis):
    @cached(ttl=300, prefix='tax')
    def get_tax(house_id, year):
        return {'house': house_id, 'year': year, 'tax': house_id * 1000}
    
    result1 = get_tax(1, 2026)
    result2 = get_tax(2, 2026)
    assert result1 != result2  # Different args -> different cache entries
```

```bash
pytest tests/unit/test_cache.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** Caching works: store, retrieve, expire, invalidate. All pass.

---

#### SPRINT 4: API ENDPOINTS (Days 15-21)

##### Step 4.1: Authentication API

**Action:** Create auth routes: login, logout, refresh, me

**Test:**
```python
# backend/tests/integration/test_auth_api.py
def test_login_success(client, db_session):
    create_test_user(db_session, username='admin', password='admin123')
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'admin123'
    })
    assert response.status_code == 200
    assert 'access_token' in response.json

def test_login_wrong_password(client, db_session):
    create_test_user(db_session, username='admin', password='admin123')
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin', 'password': 'wrong'
    })
    assert response.status_code == 401

def test_protected_route_without_token(client):
    response = client.get('/api/v1/auth/me')
    assert response.status_code == 401

def test_protected_route_with_token(client, auth_headers):
    response = client.get('/api/v1/auth/me', headers=auth_headers)
    assert response.status_code == 200
    assert 'username' in response.json

def test_token_refresh(client, auth_headers):
    response = client.post('/api/v1/auth/refresh', headers=auth_headers)
    assert response.status_code == 200
    assert 'access_token' in response.json

def test_logout(client, auth_headers):
    response = client.post('/api/v1/auth/logout', headers=auth_headers)
    assert response.status_code == 200
```

```bash
pytest tests/integration/test_auth_api.py -v
# Expected: 6 passed, 0 failed
```

**Exit Criteria:** Login, logout, token refresh, protected routes all work.

---

##### Step 4.2: Houses API

**Action:** Create house CRUD endpoints + spatial queries

**Test:**
```python
# backend/tests/integration/test_houses_api.py
def test_create_house(client, auth_headers):
    response = client.post('/api/v1/houses', headers=auth_headers, json={
        'commune': 'Yaounde I', 'department': 'Mfoundi', 'region': 'Centre',
        'building_type': 'villa', 'building_levels': 2,
        'footprint_area': 150.5, 'owner_name': 'Jean Dupont',
        'phone_number': '+237699123456', 'tax_category_code': 'RESIDENTIAL',
        'coordinates': {'latitude': 3.8667, 'longitude': 11.5167}
    })
    assert response.status_code == 201
    assert 'immatriculation_number' in response.json['data']
    assert response.json['data']['immatriculation_number'].startswith('CMR-CE-YDE1-')

def test_get_house_by_id(client, auth_headers, db_session):
    house = create_test_house(db_session)
    response = client.get(f'/api/v1/houses/{house.house_id}', headers=auth_headers)
    assert response.status_code == 200

def test_get_house_by_immatriculation(client, auth_headers, db_session):
    house = create_test_house(db_session, 'CMR-CE-YDE1-0000001')
    response = client.get('/api/v1/houses/immat/CMR-CE-YDE1-0000001', headers=auth_headers)
    assert response.status_code == 200

def test_update_house(client, auth_headers, db_session):
    house = create_test_house(db_session)
    response = client.put(f'/api/v1/houses/{house.house_id}', headers=auth_headers, json={
        'owner_name': 'Updated Name', 'building_levels': 3
    })
    assert response.status_code == 200

def test_list_houses_paginated(client, auth_headers, db_session):
    create_test_houses(db_session, count=25)
    response = client.get('/api/v1/houses?page=1&per_page=10', headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json['data']) == 10
    assert response.json['total'] == 25

def test_get_nearby_houses(client, auth_headers, db_session):
    create_test_houses_with_coords(db_session)
    response = client.get('/api/v1/houses/nearby?lat=3.8667&lon=11.5167&radius=500', headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json['data']) > 0

def test_house_not_found(client, auth_headers):
    response = client.get('/api/v1/houses/99999', headers=auth_headers)
    assert response.status_code == 404

def test_bilingual_error_message_fr(client, auth_headers):
    response = client.get('/api/v1/houses/99999', headers={**auth_headers, 'Accept-Language': 'fr'})
    assert 'introuvable' in response.json['message'].lower() or 'invalide' in response.json['message'].lower()

def test_bilingual_error_message_en(client, auth_headers):
    response = client.get('/api/v1/houses/99999', headers={**auth_headers, 'Accept-Language': 'en'})
    assert 'not found' in response.json['message'].lower()
```

```bash
pytest tests/integration/test_houses_api.py -v
# Expected: 9 passed, 0 failed
```

**Exit Criteria:** Full house CRUD, spatial queries, pagination, i18n errors all work.

---

##### Step 4.3: Payments API

**Action:** Create payment endpoints

**Test:**
```python
# backend/tests/integration/test_payments_api.py
def test_create_payment(client, auth_headers, db_session):
    house = create_test_house(db_session)
    response = client.post('/api/v1/payments', headers=auth_headers, json={
        'house_id': house.house_id,
        'amount_paid': 25000, 'payment_method': 'MOBILE_MONEY_MTN',
        'payment_year': 2026, 'payment_period': 'Q1'
    })
    assert response.status_code == 201
    assert 'receipt_number' in response.json['data']

def test_payment_updates_house_status(client, auth_headers, db_session):
    house = create_test_house(db_session, annual_tax=50000)
    # Pay full amount
    client.post('/api/v1/payments', headers=auth_headers, json={
        'house_id': house.house_id,
        'amount_paid': 50000, 'payment_method': 'CASH',
        'payment_year': 2026, 'payment_period': 'ANNUAL'
    })
    # Check house status updated
    response = client.get(f'/api/v1/houses/{house.house_id}', headers=auth_headers)
    assert response.json['data']['payment_status'] == 'PAID'

def test_partial_payment_status(client, auth_headers, db_session):
    house = create_test_house(db_session, annual_tax=50000)
    client.post('/api/v1/payments', headers=auth_headers, json={
        'house_id': house.house_id,
        'amount_paid': 20000, 'payment_method': 'CASH',
        'payment_year': 2026, 'payment_period': 'Q1'
    })
    response = client.get(f'/api/v1/houses/{house.house_id}', headers=auth_headers)
    assert response.json['data']['payment_status'] == 'PARTIAL'

def test_payment_history(client, auth_headers, db_session):
    house = create_test_house(db_session)
    create_payments(db_session, house.house_id, count=5)
    response = client.get(f'/api/v1/payments?house_id={house.house_id}', headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json['data']) == 5
```

```bash
pytest tests/integration/test_payments_api.py -v
# Expected: 4 passed, 0 failed
```

**Exit Criteria:** Payments create, house status auto-updates, history works.

---

##### Step 4.4: Verification API (for Mobile)

**Action:** Create field verification endpoints

**Test:**
```python
# backend/tests/integration/test_verification_api.py
def test_get_nearby_unverified(client, agent_headers, db_session):
    create_unverified_houses(db_session, count=10)
    response = client.get('/api/v1/verification/nearby?lat=3.8667&lon=11.5167&radius=1000', headers=agent_headers)
    assert response.status_code == 200
    assert len(response.json['data']) > 0
    for house in response.json['data']:
        assert house['verification_status'] in ['PENDING', 'AUTO_DETECTED']

def test_verify_house(client, agent_headers, db_session):
    house = create_unverified_house(db_session)
    response = client.post('/api/v1/verification/verify', headers=agent_headers, json={
        'immatriculation_number': house.immatriculation_number,
        'owner_name': 'Jean Verified', 'phone_number': '+237699000000',
        'building_levels': 3, 'building_type': 'villa',
        'gps_latitude': 3.8667, 'gps_longitude': 11.5167
    })
    assert response.status_code == 200
    # Check status updated
    updated = House.query.get(house.house_id)
    assert updated.verification_status == 'VERIFIED'
    assert updated.confidence_score == 1.0

def test_verification_history_created(client, agent_headers, db_session):
    house = create_unverified_house(db_session)
    client.post('/api/v1/verification/verify', headers=agent_headers, json={
        'immatriculation_number': house.immatriculation_number,
        'owner_name': 'Test', 'building_levels': 1, 'building_type': 'house'
    })
    history = VerificationHistory.query.filter_by(house_id=house.house_id).all()
    assert len(history) == 1
    assert history[0].new_status == 'VERIFIED'
```

```bash
pytest tests/integration/test_verification_api.py -v
# Expected: 3 passed, 0 failed
```

**Exit Criteria:** Field agents can find and verify houses. History recorded.

---

##### Step 4.5: Cache Integration with API

**Action:** Wire cache decorator into services used by API

**Test:**
```python
# backend/tests/integration/test_api_cache.py
def test_cached_dashboard_stats(client, auth_headers, fake_redis):
    response1 = client.get('/api/v1/reports/dashboard', headers=auth_headers)
    response2 = client.get('/api/v1/reports/dashboard', headers=auth_headers)
    assert response1.json == response2.json
    # Verify cache was hit on second call
    keys = fake_redis.keys('dashboard:*')
    assert len(keys) > 0

def test_cache_invalidated_on_new_house(client, auth_headers, fake_redis):
    # Get stats (populates cache)
    client.get('/api/v1/reports/dashboard', headers=auth_headers)
    # Add house (should invalidate cache)
    client.post('/api/v1/houses', headers=auth_headers, json={...})
    # Check cache cleared
    keys = fake_redis.keys('dashboard:*')
    assert len(keys) == 0

def test_reference_data_cached(client, auth_headers, fake_redis):
    response = client.get('/api/v1/admin/communes', headers=auth_headers)
    keys = fake_redis.keys('ref:*')
    assert len(keys) > 0
```

```bash
pytest tests/integration/test_api_cache.py -v
# Expected: 3 passed, 0 failed
```

**Exit Criteria:** Caching active in API. Invalidation working. Performance improved.

---

#### SPRINT 5: ADMIN DASHBOARD - REACT (Days 22-30)

##### Step 5.1: React Project Setup

**Action:** Initialize React with Ant Design, routing, i18n

**Test:**
```bash
cd frontend/admin
npm start  # Must compile without errors
npm test   # Default tests pass
```

**Exit Criteria:** React app starts. No compilation errors.

---

##### Step 5.2: Authentication Pages

**Action:** Login page with API integration

**Test (Cypress E2E):**
```javascript
// frontend/admin/cypress/e2e/auth.cy.js
describe('Authentication', () => {
  it('shows login page', () => {
    cy.visit('/login')
    cy.get('input[name="username"]').should('be.visible')
    cy.get('input[name="password"]').should('be.visible')
  })
  
  it('logs in successfully', () => {
    cy.visit('/login')
    cy.get('input[name="username"]').type('admin')
    cy.get('input[name="password"]').type('admin123')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/dashboard')
  })
  
  it('shows error on wrong credentials', () => {
    cy.visit('/login')
    cy.get('input[name="username"]').type('wrong')
    cy.get('input[name="password"]').type('wrong')
    cy.get('button[type="submit"]').click()
    cy.get('.ant-message-error').should('be.visible')
  })
})
```

```bash
npx cypress run --spec "cypress/e2e/auth.cy.js"
# Expected: 3 passing
```

**Exit Criteria:** Login page renders. Authentication works end-to-end.

---

##### Step 5.3: Dashboard Page

**Action:** Statistics cards, map view, recent activity

**Test:**
```javascript
// frontend/admin/src/pages/__tests__/DashboardPage.test.jsx
test('renders dashboard with stats cards', async () => {
  renderWithProviders(<DashboardPage />)
  await waitFor(() => {
    expect(screen.getByText(/Total Houses/i)).toBeInTheDocument()
    expect(screen.getByText(/Payments/i)).toBeInTheDocument()
    expect(screen.getByText(/Verified/i)).toBeInTheDocument()
  })
})

test('renders map component', () => {
  renderWithProviders(<DashboardPage />)
  expect(screen.getByTestId('dashboard-map')).toBeInTheDocument()
})
```

```bash
cd frontend/admin && npm test -- --watchAll=false
# Expected: All tests pass
```

**Exit Criteria:** Dashboard renders with stats. Map displays.

---

##### Step 5.4: House Management Pages

**Action:** House list, create form, detail view, map search

**Test:**
```javascript
// Tests for: list renders, pagination works, create form validates,
// search filters, map interaction, edit updates correctly
test('house list shows paginated data', async () => { ... })
test('create house form validates required fields', async () => { ... })
test('house detail shows immatriculation number', async () => { ... })
test('language switcher changes labels', async () => { ... })
```

```bash
cd frontend/admin && npm test -- --watchAll=false
# Expected: All tests pass
```

**Exit Criteria:** House CRUD works in UI. Bilingual labels switch correctly.

---

##### Step 5.5: Payment and Reports Pages

**Action:** Payment recording UI, receipt generation, reports with charts

**Test:** Similar integration tests for payment forms, receipt PDF download, chart rendering.

```bash
cd frontend/admin && npm test -- --watchAll=false
npx cypress run
# Expected: All tests pass
```

**Exit Criteria:** Payments recordable. Receipts downloadable. Reports render.

---

#### SPRINT 6: CITIZEN PORTAL - NEXT.JS (Days 31-36)

##### Step 6.1: Next.js Project Setup

**Action:** Initialize Next.js with responsive design, i18n

##### Step 6.2: Property Lookup Page

**Action:** Search by immatriculation number

##### Step 6.3: Tax Status & Payment Page

**Action:** Display tax obligations, mobile money payment form

##### Step 6.4: Certificate Download

**Action:** PDF certificate generation and download

**Test for each step:**
```bash
cd frontend/citizen
npm run build  # No errors
npm test       # All tests pass
npx cypress run  # E2E tests pass
```

**Exit Criteria per step:** Feature works. Tests pass. Responsive on mobile.

---

#### SPRINT 7: MOBILE APP - FLUTTER (Days 37-45)

##### Step 7.1: Flutter Project Setup

**Action:** Initialize Flutter, configure packages, set up i18n

**Test:**
```bash
cd mobile
flutter analyze   # No issues
flutter test      # All tests pass
```

##### Step 7.2: Authentication Screen

**Action:** Login with API integration

##### Step 7.3: House List & Map Screen

**Action:** GPS-based house listing with map

##### Step 7.4: Verification Screen

**Action:** Verification form with camera capture

##### Step 7.5: Offline Sync System

**Action:** SQLite local storage, background sync

**Test for each step:**
```bash
flutter analyze   # 0 issues
flutter test      # All tests pass
flutter run       # App runs without crash
```

**Exit Criteria per step:** Feature works. Tests pass. Works offline (Step 7.5).

---

#### SPRINT 8: INTEGRATION & PERFORMANCE (Days 46-50)

##### Step 8.1: Full Integration Testing

**Action:** Test all components working together

**Test:**
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Run ALL backend tests
cd backend && pytest --cov=app --cov-report=html -v
# Expected: coverage > 80%, 0 failures

# Run ALL frontend tests
cd frontend/admin && npm test -- --watchAll=false
cd frontend/citizen && npm test -- --watchAll=false

# Run ALL E2E tests
npx cypress run

# Run ALL mobile tests
cd mobile && flutter test
```

**Exit Criteria:** ALL tests pass across ALL components. Coverage > 80%.

---

##### Step 8.2: Cache Performance Testing

**Action:** Verify caching improves response times

**Test:**
```python
# backend/tests/performance/test_cache_performance.py
def test_dashboard_cached_vs_uncached(client, auth_headers):
    # Without cache
    invalidate_cache('dashboard')
    start = time.time()
    response1 = client.get('/api/v1/reports/dashboard', headers=auth_headers)
    uncached_time = time.time() - start
    
    # With cache
    start = time.time()
    response2 = client.get('/api/v1/reports/dashboard', headers=auth_headers)
    cached_time = time.time() - start
    
    assert cached_time < uncached_time  # Cached should be faster
    print(f"Uncached: {uncached_time:.3f}s, Cached: {cached_time:.3f}s")
    print(f"Speedup: {uncached_time/cached_time:.1f}x")
```

```bash
pytest tests/performance/test_cache_performance.py -v -s
# Expected: Cache 5-10x faster
```

**Exit Criteria:** Cache demonstrably faster. All performance tests pass.

---

##### Step 8.3: Load Testing

**Action:** Simulate concurrent users

**Test:**
```python
# backend/tests/performance/locustfile.py
from locust import HttpUser, task, between

class ImmatUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        response = self.client.post('/api/v1/auth/login', json={
            'username': 'admin', 'password': 'admin123'
        })
        self.token = response.json()['access_token']
    
    @task(3)
    def list_houses(self):
        self.client.get('/api/v1/houses', headers={'Authorization': f'Bearer {self.token}'})
    
    @task(2)
    def dashboard(self):
        self.client.get('/api/v1/reports/dashboard', headers={'Authorization': f'Bearer {self.token}'})
    
    @task(1)
    def search_house(self):
        self.client.get('/api/v1/houses/nearby?lat=3.8667&lon=11.5167&radius=500',
                       headers={'Authorization': f'Bearer {self.token}'})
```

```bash
locust -f tests/performance/locustfile.py --headless -u 50 -r 5 --run-time 2m
# Expected: < 2s average response, < 1% error rate
```

**Exit Criteria:** Handles 50 concurrent users. Response < 2s. Error rate < 1%.

---

#### SPRINT 9: PRODUCTION DEPLOYMENT (Days 51-55)

##### Step 9.1: Build Production Docker Images

**Test:**
```bash
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml ps
# Expected: All services "Up"

# Health check
curl http://localhost/api/v1/health
# Expected: {"status": "healthy"}
```

##### Step 9.2: Database Migration on Production

**Test:**
```bash
docker-compose exec api flask db upgrade
docker-compose exec db psql -U immat_user -d immatriculation -c "\dt immatriculation.*"
# Expected: All tables exist
```

##### Step 9.3: SSL and Security Verification

**Test:**
```bash
curl -I https://immatriculation.gov.cm
# Expected: HTTP/2 200, strict TLS
```

##### Step 9.4: Smoke Test on Production

**Test:**
```bash
# Test each endpoint on production
curl https://immatriculation.gov.cm/api/v1/health            # 200
curl -X POST https://immatriculation.gov.cm/api/v1/auth/login  # 200 with token
curl https://immatriculation.gov.cm/api/v1/houses              # 200 with auth
```

**Exit Criteria:** Production fully operational. All smoke tests pass. SSL valid.

---

##### Step 9.5: Backup System Verification

**Test:**
```bash
# Trigger manual backup
docker-compose exec db pg_dump -U immat_user immatriculation > test_backup.sql
# Verify backup file is valid
head -5 test_backup.sql  # Should show SQL
wc -l test_backup.sql    # Should have content
```

**Exit Criteria:** Backups created successfully. Restorable.

---

### 13.2 Development Progress Tracking

| Sprint | Days | Status | Tests | Coverage |
|--------|------|--------|-------|----------|
| 1: Foundation | 1-3 | [ ] | 0/12 | - |
| 2: Database & Models | 4-7 | [ ] | 0/8 | - |
| 3: Repositories & Services | 8-14 | [ ] | 0/24 | - |
| 4: API Endpoints | 15-21 | [ ] | 0/28 | - |
| 5: Admin Dashboard | 22-30 | [ ] | 0/20 | - |
| 6: Citizen Portal | 31-36 | [ ] | 0/12 | - |
| 7: Mobile App | 37-45 | [ ] | 0/15 | - |
| 8: Integration & Perf | 46-50 | [ ] | 0/10 | >80% |
| 9: Deployment | 51-55 | [ ] | 0/8 | - |
| **TOTAL** | **55 days** | | **0/137** | **>80%** |

### 13.3 Test Commands Quick Reference

```bash
# Backend unit tests
cd backend && pytest tests/unit/ -v

# Backend integration tests
cd backend && pytest tests/integration/ -v

# Backend ALL tests with coverage
cd backend && pytest --cov=app --cov-report=html -v

# Frontend admin tests
cd frontend/admin && npm test -- --watchAll=false

# Frontend citizen tests
cd frontend/citizen && npm test -- --watchAll=false

# E2E tests
cd frontend/admin && npx cypress run

# Mobile tests
cd mobile && flutter test

# Performance tests
cd backend && locust -f tests/performance/locustfile.py --headless -u 50 -r 5 --run-time 2m

# FULL SUITE (run before any merge/deploy)
./scripts/run_all_tests.sh
```

---
## 14. TESTING STRATEGY

### 14.1 Test Levels

| Level | Scope | Tools | When |
|-------|-------|-------|------|
| **Unit Tests** | Individual functions/methods | pytest, Jest, flutter_test | Every commit |
| **Integration Tests** | API endpoints, DB operations | pytest-flask, supertest | Every feature |
| **E2E Tests** | Full user workflows | Cypress | Every sprint |
| **Cache Tests** | Redis caching behavior | fakeredis, pytest | Every cache change |
| **Performance Tests** | Load, stress testing | Locust | Pre-deployment |
| **Security Tests** | Auth, injection, XSS | OWASP ZAP, bandit | Pre-deployment |

### 14.2 Test Coverage Requirements

| Component | Minimum Coverage | Target Coverage |
|-----------|------------------|-----------------|
| Backend Services | 80% | 90% |
| API Endpoints | 90% | 95% |
| Cache Layer | 85% | 90% |
| Frontend Components | 70% | 80% |
| Mobile App | 70% | 80% |

### 14.3 Testing Rule

> **NO CODE MOVES TO THE NEXT STEP UNTIL ALL TESTS PASS WITH ZERO ERRORS.**
> Every test must pass. Every error must be resolved. Only then proceed.

---

## 15. MAINTENANCE & OPERATIONS

### 14.1 Backup Strategy

| Data | Frequency | Retention |
|------|-----------|-----------|
| Database | Daily | 30 days |
| Files (MinIO) | Daily | 30 days |
| Full system | Weekly | 6 months |

### 14.2 Monitoring

| Metric | Alert Threshold |
|--------|-----------------|
| API Response Time | > 2s |
| Database Connections | > 80% |
| Disk Usage | > 80% |
| Error Rate | > 1% |

### 14.3 Maintenance Tasks

| Task | Frequency |
|------|-----------|
| Security patches | Monthly |
| Database optimization | Monthly |
| Log rotation | Daily |
| Backup verification | Weekly |

---

## 16. APPENDICES

### Appendix A: Flask Application Factory

```python
# backend/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_babel import Babel
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
babel = Babel()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    babel.init_app(app)
    CORS(app)
    
    # Register blueprints
    from app.api.routes import auth, houses, payments, users
    app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')
    app.register_blueprint(houses.bp, url_prefix='/api/v1/houses')
    app.register_blueprint(payments.bp, url_prefix='/api/v1/payments')
    app.register_blueprint(users.bp, url_prefix='/api/v1/users')
    
    return app
```

### Appendix B: Environment Variables

```bash
# .env.example
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/immatriculation
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-jwt-secret
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Appendix C: Region Codes

| Region | Code | Capital |
|--------|------|---------|
| Adamaoua | AD | Ngaoundéré |
| Centre | CE | Yaoundé |
| Est | ES | Bertoua |
| Extrême-Nord | EN | Maroua |
| Littoral | LT | Douala |
| Nord | NO | Garoua |
| Nord-Ouest | NW | Bamenda |
| Ouest | OU | Bafoussam |
| Sud | SU | Ebolowa |
| Sud-Ouest | SW | Buea |

### Appendix D: Commune Codes (Complete Reference)

#### CENTRE Region (CE) - Pilot Region

| Commune | Code | Department |
|---------|------|------------|
| Yaoundé I | YDE1 | Mfoundi |
| Yaoundé II | YDE2 | Mfoundi |
| Yaoundé III | YDE3 | Mfoundi |
| Yaoundé IV | YDE4 | Mfoundi |
| Yaoundé V | YDE5 | Mfoundi |
| Yaoundé VI | YDE6 | Mfoundi |
| Yaoundé VII | YDE7 | Mfoundi |
| Mbalmayo | MBY | Nyong-et-So'o |
| Obala | OBL | Lékié |
| Monatélé | MNT | Lékié |
| Nanga-Eboko | NEB | Haute-Sanaga |
| Ntui | NTI | Mbam-et-Kim |
| Bafia | BFA | Mbam |
| Ngoumou | NGM | Méfou-et-Akono |
| Mfou | MFO | Méfou-et-Afamba |
| Soa | SOA | Méfou-et-Afamba |
| Okola | OKL | Lékié |
| Esse | ESS | Mfoundi |
| Awae | AWA | Méfou-et-Afamba |
| Ebebda | EBD | Lékié |

#### LITTORAL Region (LT) - Pilot Region

| Commune | Code | Department |
|---------|------|------------|
| Douala I | DLA1 | Wouri |
| Douala II | DLA2 | Wouri |
| Douala III | DLA3 | Wouri |
| Douala IV | DLA4 | Wouri |
| Douala V | DLA5 | Wouri |
| Douala VI | DLA6 | Wouri |
| Edéa I | EDA1 | Sanaga-Maritime |
| Edéa II | EDA2 | Sanaga-Maritime |
| Nkongsamba I | NKS1 | Moungo |
| Nkongsamba II | NKS2 | Moungo |
| Nkongsamba III | NKS3 | Moungo |
| Loum | LOM | Moungo |
| Manjo | MNJ | Moungo |
| Mbanga | MBG | Moungo |
| Penja | PJA | Moungo |
| Dibombari | DBM | Moungo |
| Yabassi | YBS | Nkam |
| Ndom | NDM | Sanaga-Maritime |
| Pouma | PMA | Sanaga-Maritime |
| Dizangué | DZG | Sanaga-Maritime |

#### ADAMAOUA Region (AD)

| Commune | Code | Department |
|---------|------|------------|
| Ngaoundéré I | NGD1 | Vina |
| Ngaoundéré II | NGD2 | Vina |
| Ngaoundéré III | NGD3 | Vina |
| Meiganga | MGG | Mbéré |
| Tibati | TBT | Djerem |
| Tignère | TGN | Faro-et-Déo |
| Banyo | BNY | Mayo-Banyo |
| Djohong | DJH | Mbéré |
| Ngaoundal | NGL | Djerem |
| Belel | BEL | Vina |

#### EST Region (ES)

| Commune | Code | Department |
|---------|------|------------|
| Bertoua I | BTA1 | Lom-et-Djérem |
| Bertoua II | BTA2 | Lom-et-Djérem |
| Batouri | BTR | Kadey |
| Abong-Mbang | ABM | Haut-Nyong |
| Yokadouma | YKD | Boumba-et-Ngoko |
| Garoua-Boulaï | GRB | Lom-et-Djérem |
| Bélabo | BLB | Lom-et-Djérem |
| Moloundou | MLD | Boumba-et-Ngoko |
| Ndelele | NDL | Kadey |
| Lomié | LME | Haut-Nyong |

#### EXTRÊME-NORD Region (EN)

| Commune | Code | Department |
|---------|------|------------|
| Maroua I | MRA1 | Diamaré |
| Maroua II | MRA2 | Diamaré |
| Maroua III | MRA3 | Diamaré |
| Kousseri | KSR | Logone-et-Chari |
| Mokolo | MKL | Mayo-Tsanaga |
| Yagoua | YGA | Mayo-Danay |
| Mora | MOR | Mayo-Sava |
| Kaélé | KLE | Mayo-Kani |
| Maga | MAG | Mayo-Danay |
| Guidiguis | GDG | Mayo-Kani |

#### NORD Region (NO)

| Commune | Code | Department |
|---------|------|------------|
| Garoua I | GRA1 | Bénoué |
| Garoua II | GRA2 | Bénoué |
| Garoua III | GRA3 | Bénoué |
| Guider | GDR | Mayo-Louti |
| Poli | PLE | Faro |
| Tcholliré | TCH | Mayo-Rey |
| Lagdo | LGD | Bénoué |
| Pitoa | PTA | Bénoué |
| Figuil | FGL | Mayo-Louti |
| Rey-Bouba | RYB | Mayo-Rey |

#### NORD-OUEST Region (NW)

| Commune | Code | Department |
|---------|------|------------|
| Bamenda I | BMD1 | Mezam |
| Bamenda II | BMD2 | Mezam |
| Bamenda III | BMD3 | Mezam |
| Kumbo | KMB | Bui |
| Ndop | NDP | Ngo-Ketunjia |
| Wum | WUM | Menchum |
| Nkambe | NKB | Donga-Mantung |
| Fundong | FDG | Boyo |
| Mbengwi | MBW | Momo |
| Bali | BAL | Mezam |
| Bafut | BFT | Mezam |
| Tubah | TBH | Mezam |

#### OUEST Region (OU)

| Commune | Code | Department |
|---------|------|------------|
| Bafoussam I | BFS1 | Mifi |
| Bafoussam II | BFS2 | Mifi |
| Bafoussam III | BFS3 | Mifi |
| Dschang | DSG | Menoua |
| Mbouda | MBD | Bamboutos |
| Bangangté | BGT | Ndé |
| Foumban | FBN | Noun |
| Foumbot | FBT | Noun |
| Bandjoun | BDJ | Koung-Khi |
| Bafang | BFG | Haut-Nkam |
| Baham | BHM | Hauts-Plateaux |
| Penka-Michel | PKM | Menoua |

#### SUD Region (SU)

| Commune | Code | Department |
|---------|------|------------|
| Ebolowa I | EBL1 | Mvila |
| Ebolowa II | EBL2 | Mvila |
| Kribi I | KRB1 | Océan |
| Kribi II | KRB2 | Océan |
| Sangmélima | SGM | Dja-et-Lobo |
| Ambam | AMB | Vallée-du-Ntem |
| Lolodorf | LLF | Océan |
| Akom II | AKM | Océan |
| Mengong | MGG | Vallée-du-Ntem |
| Mvangan | MVG | Mvila |

#### SUD-OUEST Region (SW)

| Commune | Code | Department |
|---------|------|------------|
| Buea | BUA | Fako |
| Limbe I | LMB1 | Fako |
| Limbe II | LMB2 | Fako |
| Limbe III | LMB3 | Fako |
| Tiko | TKO | Fako |
| Kumba I | KBA1 | Meme |
| Kumba II | KBA2 | Meme |
| Kumba III | KBA3 | Meme |
| Mamfe | MMF | Manyu |
| Mundemba | MDB | Ndian |
| Ekondo-Titi | EKT | Ndian |
| Bangem | BGM | Kupe-Muanenguba |

### Appendix E: Immatriculation Number Examples

| Location | Immatriculation Number | Breakdown |
|----------|------------------------|-----------|
| Yaoundé Centre | CMR-CE-YDE1-0000001 | Centre > Yaoundé I > House #1 |
| Douala Akwa | CMR-LT-DLA1-0000542 | Littoral > Douala I > House #542 |
| Bamenda | CMR-NW-BMD1-0000123 | Nord-Ouest > Bamenda I > House #123 |
| Bafoussam | CMR-OU-BFS1-0000089 | Ouest > Bafoussam I > House #89 |
| Kribi | CMR-SU-KRB1-0000015 | Sud > Kribi I > House #15 |

---

## DOCUMENT APPROVAL

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Lead | _____________ | _____________ | _____________ |
| Technical Lead | _____________ | _____________ | _____________ |
| Client Representative | _____________ | _____________ | _____________ |

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-06 | Development Team | Initial release |
| 1.1 | 2026-02-06 | Development Team | Updated to 3 interfaces (removed separate citizen mobile app), added complete commune codes for all 10 regions |
| 1.2 | 2026-02-06 | Development Team | Added Redis caching architecture (Section 10), comprehensive test-driven development plan (Section 13), updated testing strategy (Section 14) |

---

*End of Document*
