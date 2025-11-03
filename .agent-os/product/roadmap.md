# CivilDIY Microservices - Development Roadmap

## Phase 0: Already Completed ✅

### Core Microservices Implementation
- [x] **Auth Service** - User registration, login, JWT token generation and validation
- [x] **User Profile Service** - Complete CRUD operations for user profiles
- [x] **Posts Service** - Full post management with MongoDB backend
- [x] **Feed Generator Service** - Activity stream aggregation with Redis materialized views

### Infrastructure & Orchestration
- [x] **API Gateway (Traefik v2.10)** - Request routing, JWT validation, middleware
- [x] **Service Discovery (Consul)** - Service registration with health checks
- [x] **Docker Compose Setup** - Complete orchestration of all services
- [x] **Message Bus (Kafka)** - Event streaming for post lifecycle events
- [x] **Database Setup** - PostgreSQL, MongoDB, Redis containers

### Architecture Patterns
- [x] **Event-Driven Architecture** - Services communicate via Kafka events
- [x] **CQRS Pattern** - Separation of read (Redis) and write (MongoDB) paths
- [x] **Materialized Views** - Pre-aggregated activity streams in Redis
- [x] **Service Discovery Pattern** - Consul for dynamic service registration
- [x] **API Gateway Pattern** - Traefik for centralized routing and auth

### Testing & Documentation
- [x] **Automated Test Suite** - Shell script with core workflow tests
- [x] **Postman Collection** - API testing collection for all endpoints
- [x] **README Documentation** - Complete setup and usage guide
- [x] **TESTING.md** - Detailed manual testing instructions

---

## Phase 1: Deployment & Environment Testing 🔄 (Current)

### Local Deployment (Completed)
- [x] Runs on Docker Desktop with docker-compose
- [x] All services start and communicate correctly
- [x] Automated test suite passes locally

### Dockge LXC Deployment (In Progress)
- [ ] Services start but not communicating properly
- [ ] Networking configuration issues
- [ ] Service discovery working but routing problematic
- **Tasks:**
  - [ ] Debug network connectivity between containers
  - [ ] Resolve hostname resolution in LXC environment
  - [ ] Test Kafka event propagation in LXC
  - [ ] Verify Traefik routing in LXC bridge network
  - [ ] Document LXC-specific configuration requirements

### Documentation Updates
- [ ] Create LXC deployment guide with known issues/fixes
- [ ] Add troubleshooting section for common errors
- [ ] Document networking differences between Docker Desktop and Dockge LXC

---

## Phase 2: Robustness & Production Readiness 📋

### Error Handling & Recovery
- [ ] Implement retry logic for inter-service communication
- [ ] Add circuit breaker pattern for resilience
- [ ] Improve error messages and logging
- [ ] Add correlation IDs for request tracing

### Data Persistence
- [ ] Add volume mounts for PostgreSQL (currently ephemeral)
- [ ] Add volume mounts for MongoDB (currently ephemeral)
- [ ] Implement Redis persistence (RDB or AOF)
- [ ] Create backup/restore procedures

### Security Enhancements
- [ ] Move SECRET_KEY to environment variable
- [ ] Add authentication to Kafka (SASL)
- [ ] Add authentication to Redis
- [ ] Add authentication to MongoDB beyond basic auth
- [ ] Implement HTTPS/TLS between services
- [ ] Add rate limiting and throttling

### Monitoring & Observability
- [ ] Add Prometheus metrics collection
- [ ] Add Grafana dashboards for monitoring
- [ ] Implement centralized logging (ELK stack)
- [ ] Add distributed tracing (Jaeger)
- [ ] Monitor service health and dependencies

---

## Phase 3: Scaling & Performance 🚀

### Horizontal Scaling
- [ ] Configure multiple instances of each service
- [ ] Load balancing across service instances
- [ ] Database connection pooling optimization

### Performance Optimization
- [ ] Database query optimization and indexing
- [ ] Caching strategies for frequently accessed data
- [ ] Redis cluster configuration for high availability
- [ ] Kafka topic partitioning for parallelism

### Advanced Patterns
- [ ] Implement service-to-service authentication (mTLS)
- [ ] Add request deduplication for idempotency
- [ ] Implement saga pattern for distributed transactions
- [ ] Add bulkhead pattern for fault isolation

---

## Phase 4: Enhanced Features & Integration 🎯

### New Capabilities
- [ ] Add follow/unfollow feature
- [ ] Implement user-specific feeds
- [ ] Add like/comment system for posts
- [ ] Real-time notifications (WebSocket)
- [ ] Search functionality (Elasticsearch integration)

### External Integrations
- [ ] Third-party authentication (OAuth2)
- [ ] Social media sharing
- [ ] Email notifications
- [ ] File upload service
- [ ] Image processing pipeline

### Team Collaboration
- [ ] User roles and permissions system
- [ ] Audit logging for compliance
- [ ] Admin dashboard for monitoring
- [ ] Developer API documentation (OpenAPI/Swagger)

---

## Milestones

| Milestone | Status | Target | Notes |
|-----------|--------|--------|-------|
| Local Deployment | ✅ Complete | - | Working on Docker Desktop |
| LXC Deployment | 🔄 In Progress | This week | Debugging networking issues |
| Phase 1 Complete | ⏳ Pending | End of week | Once LXC deployment works |
| Phase 2 Start | ⏳ Pending | Next phase | Security & persistence improvements |
| Production Ready | ⏳ Planned | Q1 2025 | Estimate after Phase 2 & 3 |

---

## Known Issues

1. **LXC Networking:** Services not communicating properly when deployed on Dockge LXC
   - Container names not resolving within LXC network
   - Possible bridge network configuration issue
   - Status: **INVESTIGATING**

2. **Data Persistence:** All data lost on container restart
   - Priority: **HIGH** (needed for testing beyond basic workflows)
   - Fix: Add Docker volume mounts

3. **Security:** SECRET_KEY hardcoded
   - Risk: **MEDIUM** (not production code yet, but good practice)
   - Fix: Use environment variables

---

## Next Steps

1. **Immediate:** Fix Dockge LXC networking issues
   - Investigate container name resolution
   - Test network connectivity between services
   - Debug Traefik routing in LXC environment

2. **Short-term:** Document LXC deployment requirements

3. **Medium-term:** Implement Phase 2 (robustness improvements)

4. **Long-term:** Consider Phase 3 & 4 for production deployment
