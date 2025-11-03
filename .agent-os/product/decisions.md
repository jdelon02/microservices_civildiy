# Architectural Decisions - CivilDIY Microservices

## Decision: Event-Driven Architecture with Kafka

**Status:** Implemented ✅  
**Date:** 2024-11-01  
**Participants:** Architecture Design  

### Context
Services need to communicate without tight coupling. Posts service creates data that Feed Generator needs to process, but they should be independent.

### Decision
Use Apache Kafka as an event bus for inter-service communication.

### Rationale
- **Decoupling:** Services don't call each other directly
- **Scalability:** Can add new consumers without modifying producers
- **Reliability:** Events are persisted and replayed if needed
- **Ordering:** Per-topic ordering guarantees for event consistency

### Consequences
- ✅ Services can be deployed independently
- ✅ Easy to add new event consumers later
- ⚠️ Added complexity: Kafka cluster management
- ⚠️ Eventual consistency instead of immediate consistency
- ⚠️ Requires event versioning strategy

### Implementation
- **Topic:** `posts-events`
- **Producers:** Posts Service (on create/update/delete)
- **Consumers:** Feed Generator Service
- **Retention:** 7 days (default)
- **Partitions:** 1 (single for development, can scale later)

---

## Decision: CQRS Pattern for Activity Feeds

**Status:** Implemented ✅  
**Date:** 2024-11-01  
**Participants:** Architecture Design  

### Context
Activity feeds require fast reads but slow writes. Aggregating data on-demand from MongoDB is too slow.

### Decision
Implement Command Query Responsibility Segregation (CQRS) pattern:
- **Write Model:** MongoDB (normalized, optimized for writes)
- **Read Model:** Redis (denormalized, pre-aggregated for reads)

### Rationale
- **Performance:** O(1) feed reads from Redis vs O(n) from MongoDB
- **Scalability:** Read and write paths scale independently
- **Flexibility:** Can change read format without affecting writes

### Consequences
- ✅ Fast feed queries (2-3ms from Redis vs 100+ms from DB)
- ✅ Can scale reads and writes separately
- ⚠️ Complexity: Must keep models in sync
- ⚠️ Eventual consistency between models
- ⚠️ Cache invalidation complexity

### Implementation
- **Command Side:** Posts Service writes to MongoDB
- **Query Side:** Feed Generator consumes Kafka events and updates Redis
- **Materialized View:** Pre-aggregated activity stream in Redis
- **Storage:** Lists per user + global activity stream
- **Retention:** 1000 items global, 100 per user

---

## Decision: Microservices Architecture

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Architecture Design  

### Context
Want to explore distributed system patterns and understand service interactions.

### Decision
Implement independent microservices (Auth, Profile, Posts, Feed) instead of monolith.

### Rationale
- **Learning:** Demonstrates real distributed system patterns
- **Independence:** Each service has own database and lifecycle
- **Technology Diversity:** Can use different tech per service
- **Scalability:** Each service scales independently based on load

### Consequences
- ✅ Each service is independently deployable
- ✅ Can understand microservices patterns and challenges
- ⚠️ Operational complexity increases significantly
- ⚠️ Distributed transaction handling needed
- ⚠️ Network latency between services
- ⚠️ Debugging is harder (multiple logs, services)

### Implementation
- **Services:** Auth, Profile, Posts, Feed Generator (4 services)
- **Communication:** Kafka events + HTTP for service-to-service
- **Databases:** PostgreSQL (2 services), MongoDB (1), Redis (1)
- **Ports:** All services run on 5000, accessed via API Gateway

---

## Decision: Service Discovery with Consul

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Infrastructure Design  

### Context
Services need to find each other without hardcoded IPs/ports. Services should self-register on startup.

### Decision
Use HashiCorp Consul for service discovery and health checking.

### Rationale
- **Dynamic Registration:** Services register themselves on startup
- **Health Checks:** Automatic detection of unhealthy services
- **Key-Value Store:** Can store Traefik configuration dynamically
- **UI:** Built-in web UI for monitoring

### Consequences
- ✅ Services dynamically discoverable
- ✅ Health checks prevent routing to dead services
- ✅ Configuration stored centrally
- ⚠️ Additional service to run and manage
- ⚠️ Learning curve for Consul concepts

### Implementation
- **Service Registration:** Automatic on app startup
- **Health Checks:** HTTP GET every 10s
- **UI:** Available at http://localhost:8500
- **Traefik Config:** Stored in Consul KV store

---

## Decision: API Gateway with Traefik

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Infrastructure Design  

### Context
Need single entry point for all services. Must validate JWT tokens and forward user context.

### Decision
Use Traefik v2.10 as API Gateway with JWT validation middleware.

### Rationale
- **Routing:** Path-based and hostname-based routing
- **Middleware:** Built-in middleware for auth, headers, logging
- **Configuration:** Dynamic via Consul KV store or static files
- **Performance:** Lightweight and efficient
- **Dashboard:** Web UI for monitoring and debugging

### Consequences
- ✅ Single entry point for all services
- ✅ Centralized authentication
- ✅ Easy to add rate limiting and other middleware
- ⚠️ Traefik-specific configuration syntax
- ⚠️ Complexity in middleware ordering

### Implementation
- **Entry Points:** Port 80 (public), 8080 (admin)
- **Middleware:** JWT validation with forwardAuth
- **Service Registry:** Consul KV store for routing rules
- **Auth Response:** X-User-ID header forwarded to backends

---

## Decision: FastAPI for All Microservices

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Technology Selection  

### Context
Need Python-based REST API framework that's modern and high-performance.

### Decision
Use FastAPI with Uvicorn for all microservices.

### Rationale
- **Modern Python:** Async/await support for high concurrency
- **Type Hints:** Built-in validation with Pydantic
- **Performance:** Among fastest Python frameworks
- **Developer Experience:** Auto-generated API docs (Swagger UI)
- **Standards:** Follows OpenAPI/JSON Schema standards

### Consequences
- ✅ Clean, modern codebase
- ✅ Type safety with Pydantic validation
- ✅ High performance and concurrency
- ✅ Built-in API documentation
- ⚠️ Smaller ecosystem vs Django
- ⚠️ Async complexity for beginners

### Implementation
- **Framework:** FastAPI 0.104.1
- **Server:** Uvicorn 0.24.0
- **Validation:** Pydantic models
- **Documentation:** Auto-generated at /docs

---

## Decision: Database Separation by Service

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Data Architecture  

### Context
Each microservice should own its data. Need to demonstrate different database technologies.

### Decision
Each service has its own database following the database-per-service pattern:
- Auth Service → PostgreSQL
- Profile Service → PostgreSQL (separate namespace)
- Posts Service → MongoDB
- Feed Generator → Redis

### Rationale
- **Independence:** Services can't accidentally depend on each other's schema
- **Technology Fit:** Each DB optimized for service's needs
- **Learning:** Demonstrates polyglot persistence
- **Scalability:** Each database can scale independently

### Consequences
- ✅ Services are truly independent
- ✅ Can use best technology for each use case
- ⚠️ No cross-database transactions
- ⚠️ Requires eventual consistency
- ⚠️ Data duplication between services
- ⚠️ Distributed query challenges

### Implementation
- **PostgreSQL:** Users table (Auth), user_profiles table (Profile)
- **MongoDB:** posts collection with document-level TTLs
- **Redis:** Lists for activity feeds (no relational schema)

---

## Decision: Docker Compose for Local Orchestration

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** DevOps/Infrastructure  

### Context
Need to orchestrate 10+ containers (4 services, 4 databases, Traefik, Consul, Kafka, Zookeeper) for local development and testing.

### Decision
Use Docker Compose with single compose file for all services.

### Rationale
- **Simplicity:** Single file defines entire stack
- **Familiarity:** Most developers know Docker Compose
- **Development:** Perfect for local development
- **Reproducibility:** Same stack everywhere
- **Learning:** Good for understanding service dependencies

### Consequences
- ✅ Simple one-command startup: `docker-compose up -d`
- ✅ All services start in correct order with dependencies
- ✅ Works on any machine with Docker installed
- ⚠️ Not production-grade (use Kubernetes for prod)
- ⚠️ Single machine limitation (no clustering)
- ⚠️ Data loss on container restart (no volumes)

### Implementation
- **Version:** 3.8
- **Services:** 10 total (4 apps + 4 databases + Traefik + Consul)
- **Networking:** Docker bridge network (all services see each other by name)
- **Volumes:** Currently ephemeral (planned for Phase 2)

---

## Decision: PostgreSQL for User & Auth Data

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Data Architecture  

### Context
Auth Service needs ACID guarantees and relational schema for users table.

### Decision
Use PostgreSQL for both Auth Service and Profile Service.

### Rationale
- **ACID:** Strong consistency guarantees for user accounts
- **Relational:** Natural fit for normalized user data
- **Mature:** Battle-tested in production systems
- **Performance:** Excellent for transactional workloads

### Consequences
- ✅ Strong consistency for critical auth data
- ✅ Relational schema reduces data duplication
- ⚠️ Less flexible for unstructured data
- ⚠️ Horizontal scaling more complex

### Implementation
- **Version:** PostgreSQL 15
- **Schema:** users table with email/username uniqueness constraints
- **Connection:** Direct queries in Auth Service, ORM (SQLAlchemy) in Profile Service

---

## Decision: MongoDB for Posts Storage

**Status:** Implemented ✅  
**Date:** 2024-10-31  
**Participants:** Data Architecture  

### Context
Posts have flexible schema and varying attributes. Need horizontal scalability.

### Decision
Use MongoDB for Posts Service data storage.

### Rationale
- **Flexibility:** Schema-less documents allow flexible post structure
- **Scalability:** Built-in horizontal sharding
- **Performance:** Fast document insertion for post creation
- **JSON Native:** Natural fit for FastAPI models

### Consequences
- ✅ Flexible schema for evolving post structure
- ✅ Good write performance for creating posts
- ⚠️ Eventual consistency by default
- ⚠️ No ACID transactions (single document only)

### Implementation
- **Version:** MongoDB latest
- **Collection:** posts with _id index and user_id index
- **Driver:** pymongo with Pydantic models

---

## Decision: Redis for Activity Feed Cache

**Status:** Implemented ✅  
**Date:** 2024-11-01  
**Participants:** Data Architecture  

### Context
Activity feed queries must be extremely fast (< 10ms) and can tolerate slight staleness.

### Decision
Use Redis for storing pre-aggregated activity feed materialized view.

### Rationale
- **Speed:** In-memory access (1-2ms) vs database queries
- **Data Structure:** Lists are perfect for chronological feeds
- **TTL:** Automatic expiration of old items
- **Simplicity:** Simple key-value model for caching

### Consequences
- ✅ Very fast feed queries
- ✅ Minimal memory footprint with trimming
- ⚠️ Data loss on restart (no persistence configured)
- ⚠️ Memory limited (can't cache very large datasets)

### Implementation
- **Storage:** Redis Lists
- **Keys:** `feed:activity:global` (1000 items), `feed:activity:user:{id}` (100 items each)
- **Updates:** Via Kafka consumer (eventual consistency)

---

## Future Architectural Decisions (Planned)

### TBD: Kubernetes vs Docker Compose for Production
When moving to production, decide between Docker Compose simplicity vs Kubernetes scalability.

### TBD: Service-to-Service Authentication
Add mTLS or JWT between services for security.

### TBD: Distributed Transactions
Implement Saga pattern or similar for cross-service transactions.

### TBD: Monitoring & Observability
Choose between ELK, Prometheus/Grafana, or managed solutions.
