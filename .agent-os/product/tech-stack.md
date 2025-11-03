# Technology Stack - CivilDIY Microservices

## Core Framework

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Web Framework | FastAPI | 0.104.1 | REST API development for all microservices |
| ASGI Server | Uvicorn | 0.24.0 | Production-grade server for FastAPI apps |
| Language | Python | 3.9+ | Core implementation language |

## Databases & Persistence

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| SQL Database | PostgreSQL | 15 | User authentication & profile data (Auth, Profile services) |
| NoSQL Database | MongoDB | latest | Posts data storage with flexible schema |
| Cache Layer | Redis | latest | High-speed activity feed materialized views |

## Message Streaming & Events

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Event Broker | Apache Kafka | 7.4.0 | Event propagation between services (post events) |
| Kafka Client | confluent-kafka | 2.3.0 | Producer/Consumer for microservices |
| Zookeeper | Apache Zookeeper | 7.4.0 | Kafka coordination and cluster management |

## Service Architecture

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| API Gateway | Traefik | v2.10 | Request routing, JWT validation, header forwarding |
| Service Discovery | Consul | latest | Service registration and health checks |
| Containerization | Docker | latest | Container packaging for each service |
| Orchestration | Docker Compose | 3.8+ | Local/development environment orchestration |

## Security & Authentication

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Password Hashing | bcrypt | 4.0.1 | Secure password storage |
| Password Manager | passlib | 1.7.4 | Password hashing abstraction layer |
| JWT Tokens | PyJWT | 2.6.0 | Token generation and validation |
| Token Creation | python-jose | 3.3.0 | Alternative JWT implementation |

## Utilities & Supporting Libraries

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Data Validation | Pydantic | 2.5.0 | Data model validation and serialization |
| Database Driver | psycopg2 | 2.9.9+ | PostgreSQL connection and queries |
| MongoDB Driver | pymongo | 4.6.0 | MongoDB connection and queries |
| HTTP Client | httpx | 0.25.2 | Async HTTP requests for service-to-service communication |
| Email Validation | email-validator | 2.3.0 | Validate email addresses |
| Environment Config | python-dotenv | 1.0.0 | Load environment variables from .env files |

## Service Architecture Details

### Auth Service (port 5000)
- **Database:** PostgreSQL
- **Key Features:** Registration, login, JWT generation, token validation
- **Patterns:** Direct database queries with connection pooling
- **Health Check:** GET `/health`
- **Key Endpoint:** POST `/api/auth/validate` (used by Traefik middleware)

### User Profile Service (port 5000)
- **Database:** PostgreSQL (separate namespace)
- **Key Features:** Profile CRUD operations
- **Patterns:** SQLAlchemy for ORM (listed in requirements)
- **Health Check:** GET `/health`
- **Protection:** JWT validation via Traefik middleware

### Posts Service (port 5000)
- **Database:** MongoDB
- **Key Features:** Post CRUD, Kafka event publishing
- **Patterns:** Event publishing on create/update/delete
- **Health Check:** GET `/health`
- **Protection:** JWT validation via Traefik middleware

### Feed Generator Service (port 5000)
- **Database:** Redis
- **Key Features:** Kafka consumer, activity stream aggregation
- **Patterns:** CQRS with materialized views
- **Health Check:** GET `/health`
- **Background Process:** Kafka consumer thread for event processing

## Infrastructure Components

### API Gateway (Traefik)
- Listens on ports 80 (public), 8080 (admin dashboard)
- Routes based on URL paths and hostnames
- Implements JWT validation middleware
- Forwards X-User-ID header to backend services
- Dashboard available at `http://localhost:8080`

### Service Discovery (Consul)
- UI available at `http://localhost:8500`
- Services auto-register on startup with health checks
- Traefik routing rules stored in Consul KV store
- All services configured with 10s interval health checks

### Event Bus (Kafka + Zookeeper)
- Kafka broker on port 9092
- Topic: `posts-events` for post lifecycle events
- Retention: Default (7 days)
- Partitions: 1 (for development)

## Deployment Environments

### Local Development
- Docker Compose on Docker Desktop
- All services in single compose file
- Local volume mounts for code (optional)

### Dockge LXC (Current Testing)
- Ubuntu LXC container running Dockge
- Dockge manages Docker containers within LXC
- Same docker-compose.yml as local development
- Networking through LXC bridge

## Configuration

All services use environment variables (from docker-compose.yml):
- `DATABASE_URL`: PostgreSQL connection string
- `MONGODB_URL`: MongoDB connection string
- `KAFKA_HOST`: Kafka broker address
- `REDIS_HOST/PORT/DB`: Redis connection parameters
- `CONSUL_HOST/PORT`: Consul server address
- `SECRET_KEY`: JWT signing secret (should be environment variable in production)

## Known Limitations & Future Improvements

- [ ] No persistence volumes configured (data lost on container restart)
- [ ] SECRET_KEY hardcoded in production (needs environment variable)
- [ ] No SSL/TLS encryption between services
- [ ] No authentication for Kafka, Redis, or MongoDB
- [ ] Scaling: All services have single instance
- [ ] No monitoring/metrics collection (Prometheus/Grafana)
- [ ] No centralized logging (ELK stack recommended)
- [ ] Rate limiting not implemented
