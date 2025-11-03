# CivilDIY Microservices Framework

A scalable, event-driven microservices architecture built with FastAPI, Kafka, Redis, and PostgreSQL. Implements CQRS pattern with materialized views for high-performance activity feeds.

## Architecture Overview

```
Client
  ↓
Traefik (API Gateway + JWT Validation)
  ↓ X-User-ID Header
  ├─→ Auth Service (FastAPI + PostgreSQL)
  ├─→ User Profile Service (FastAPI + PostgreSQL)
  ├─→ Posts Service (FastAPI + MongoDB + Kafka Producer)
  └─→ Feed Generator Service (FastAPI + Kafka Consumer + Redis)

Infrastructure:
- Consul: Service Discovery
- PostgreSQL: Auth & Profile Data
- MongoDB: Posts Data
- Redis: Activity Feed Cache
- Kafka: Event Streaming
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|--------|
| API Gateway | Traefik v2.10 | Routing, JWT validation, header forwarding |
| Microservices | FastAPI + Uvicorn | REST API framework |
| Databases | PostgreSQL, MongoDB, Redis | Data persistence & caching |
| Event Streaming | Apache Kafka | Asynchronous event publishing |
| Service Discovery | Consul | Dynamic service registration |
| Containerization | Docker + Docker Compose | Container orchestration |

## Services

### 1. Auth Service
- **Endpoint:** `/api/auth`
- **Port:** 5000
- **Database:** PostgreSQL
- **Features:**
  - User registration (`POST /api/auth/register`)
  - User login with JWT (`POST /api/auth/login`)
  - JWT validation for gateway (`GET /api/auth/validate`)
  - Health checks (`GET /health`)

### 2. User Profile Service
- **Endpoint:** `/api/profile`
- **Port:** 5000
- **Database:** PostgreSQL
- **Features:**
  - Create profile (`POST /api/profile`)
  - Get profile (`GET /api/profile`)
  - Update profile (`PUT /api/profile`)
  - Delete profile (`DELETE /api/profile`)
  - Requires JWT authentication (X-User-ID header)

### 3. Posts Service
- **Endpoint:** `/api/posts`
- **Port:** 5000
- **Database:** MongoDB
- **Features:**
  - Create post (`POST /api/posts`)
  - Get post (`GET /api/posts/{id}`)
  - List posts (`GET /api/posts`)
  - Update post (`PUT /api/posts/{id}`)
  - Delete post (`DELETE /api/posts/{id}`)
  - Publishes Kafka events on create/update/delete
  - Requires JWT authentication (X-User-ID header)

### 4. Feed Generator Service
- **Endpoint:** `/api/activity-stream`
- **Port:** 5000
- **Database:** Redis
- **Pattern:** CQRS with Materialized Views
- **Features:**
  - Kafka consumer (subscribes to `posts-events`)
  - Pre-aggregates activity stream in Redis
  - Get global feed (`GET /api/activity-stream`)
  - Get user feed (`GET /api/activity-stream/user`)
  - Feed statistics (`GET /api/activity-stream/stats`)
  - Supports pagination (limit, skip)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git
- curl (for testing)

### Option 1: Local Development with Docker Compose

```bash
# Clone repository
git clone <repo-url>
cd microservices_civildiy

# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Access Points:**
- API Gateway: http://localhost
- Traefik Dashboard: http://localhost:8080
- Consul UI: http://localhost:8500

### Option 2: Dockge (Docker GUI)

Dockge is a self-hosted Docker GUI similar to Portainer.

```bash
# 1. Install Dockge
docker run -d \
  --name dockge \
  -p 5001:5001 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  louislam/dockge:latest

# 2. Access Dockge at http://localhost:5001

# 3. Add the compose file:
#    - Click "Add New"
#    - Paste docker-compose.yml contents
#    - Click "Deploy"

# 4. Monitor services in Dockge UI
```

**Via Docker Compose (easier):**

```bash
# Create docker-compose-dockge.yml
cat > docker-compose-dockge.yml << 'EOF'
version: '3.8'
services:
  dockge:
    image: louislam/dockge:latest
    container_name: dockge
    ports:
      - "5001:5001"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./docker-compose.yml:/opt/stacks/civildiy/docker-compose.yml:ro
    restart: always
EOF

# Run Dockge
docker-compose -f docker-compose-dockge.yml up -d

# Access at http://localhost:5001
```

## Testing

### Automated Testing (Recommended)

```bash
# Make test script executable
chmod +x test.sh

# Run all tests
./test.sh

# Expected output: ✓ test 1, ✓ test 2, ...
```

This script will:
1. Register a user
2. Login and get JWT
3. Create a profile
4. Create 3 posts
5. Verify feed generation
6. Test updates and deletes

### Manual Testing

See `TESTING.md` for detailed curl commands for each service.

**Quick Test:**
```bash
# 1. Register
curl -X POST http://localhost/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"pass123"}'

# 2. Login (get TOKEN)
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}'

# 3. Create post (replace TOKEN)
TOKEN="<access_token>"
curl -X POST http://localhost/api/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Post","content":"Hello world","tags":["test"]}'

# 4. Get activity stream
curl http://localhost/api/activity-stream
```

### Debugging

```bash
# View service logs
docker logs auth-service
docker logs posts-service
docker logs feed-generator-service

# Monitor Kafka events
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server kafka:9092 \
  --topic posts-events \
  --from-beginning

# Check Redis data
docker exec -it read-db redis-cli
> LRANGE feed:activity:global 0 -1

# Check MongoDB
docker exec -it mongodb mongosh
> use posts_db
> db.posts.find()
```

## Directory Structure

```
.
├── api_gateway/
│   ├── traefik.yml          # Traefik static config
│   ├── dynamic.yml          # Traefik dynamic routes & middleware
│   └── README.md
├── auth_services/
│   ├── main.py              # Auth service implementation
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── user-profile-service/
│   ├── main.py              # Profile service implementation
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── posts-service/
│   ├── main.py              # Posts service with MongoDB & Kafka
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── feed-generator-service/
│   ├── main.py              # Feed generator (Kafka consumer)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── service_discovery/
│   └── README.md            # Consul documentation
├── docker-compose.yml       # Complete stack orchestration
├── TESTING.md               # Detailed testing guide
├── test.sh                  # Automated integration tests
└── README.md                # This file
```

## API Flow

### Authentication & Header Forwarding

```
1. Client sends: Authorization: Bearer <JWT>
2. Traefik intercepts and calls: /api/auth/validate
3. Auth Service validates JWT, returns X-User-ID header
4. Traefik forwards request with X-User-ID to backend service
5. Service reads X-User-ID from header (no need to parse JWT again)
```

### Event-Driven Architecture

```
1. Client creates post → POST /api/posts
2. Posts Service stores in MongoDB
3. Posts Service publishes event to Kafka: posts-events topic
4. Feed Generator subscribes to posts-events
5. Feed Generator updates Redis materialized view
6. Client requests stream → GET /api/activity-stream
7. Feed Generator serves pre-aggregated data from Redis (O(1) read)
```

## Configuration

### Environment Variables

All services use Docker Compose environment variables. Edit `docker-compose.yml`:

```yaml
env:
  DATABASE_URL: postgres://user:password@postgres-db:5432/db
  MONGODB_URL: mongodb://user:password@mongodb:27017
  KAFKA_HOST: kafka:9092
  CONSUL_HOST: consul-server
  SECRET_KEY: your-secret-key  # For JWT signing
```

### Database Separation

Each service has its own database namespace:
- **Auth Service:** PostgreSQL `microservices_db.users`
- **Profile Service:** PostgreSQL `microservices_db.user_profiles`
- **Posts Service:** MongoDB `posts_db.posts`
- **Feed Generator:** Redis `feed:activity:*`

## Performance Considerations

### CQRS Pattern Benefits
- **Write Path:** Posts → MongoDB (optimized for writes)
- **Read Path:** Pre-aggregated → Redis (optimized for reads)
- **Decoupling:** Services communicate via events, not direct calls
- **Scalability:** Can scale posts and feed generators independently

### Caching Strategy
- Global activity feed: Latest 1000 posts in Redis
- Per-user feed: Latest 100 posts per user in Redis
- Automatic refresh on new events via Kafka

## Production Checklist

- [ ] Use `SECRET_KEY` environment variable (don't hardcode)
- [ ] Enable Consul ACLs for security
- [ ] Add database persistence volumes in docker-compose.yml
- [ ] Configure SSL/TLS certificates for Traefik
- [ ] Set up proper logging (ELK stack recommended)
- [ ] Add health check monitoring
- [ ] Implement rate limiting on Traefik
- [ ] Use strong PostgreSQL password
- [ ] Enable MongoDB authentication
- [ ] Configure Redis persistence (RDB or AOF)

## Troubleshooting

**Services won't start:**
```bash
docker-compose logs  # Check for errors
docker-compose ps    # Verify all containers
```

**JWT token issues:**
- Token expires after 24 hours
- Always use `access_token` from login response
- Include `Authorization: Bearer <token>` header

**Posts not appearing in feed:**
- Wait 2-3 seconds for Kafka event propagation
- Check: `docker logs feed-generator-service`
- Verify Kafka: `docker logs kafka`

**Database connection errors:**
- Verify credentials in docker-compose.yml
- Check container health: `docker ps`
- Test connection: `docker exec -it postgres-db psql -U user -d microservices_db -c "SELECT 1"`

## Contributing

When adding new services:
1. Follow the same FastAPI + Docker pattern
2. Self-register with Consul in startup
3. Add Traefik labels for routing
4. Document in this README
5. Add tests to test.sh

## License

MIT
