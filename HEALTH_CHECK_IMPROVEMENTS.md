# Health Check Improvements Guide

## Current Status

Currently, all services implement **basic health checks only**:
- **Docker HEALTHCHECK**: Simple HTTP GET to `/health` endpoint
- **Consul service check**: HTTP GET to `/health` endpoint  
- **Response**: `{"status": "healthy"}`

This is a **liveness probe** but lacks **readiness and dependency checks**.

---

## Recommended Health Check Enhancements

### 1. **Enhanced Liveness Check** (Required)
Return detailed service status with version and metadata:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "book-catalog-service",
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Priority**: 🟢 **LOW** - Current implementation is sufficient

---

### 2. **Readiness Check** (RECOMMENDED)
New endpoint that verifies service can handle requests (database connected, dependencies up):

```python
@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe: Service is ready to accept traffic
    Checks all critical dependencies:
    - Database connectivity
    - Consul connectivity  
    - Cache layer (if applicable)
    """
    try:
        # Test database
        db.query(AuthorDB).limit(1).first()
        
        # Test Consul connectivity
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/status/leader",
                timeout=2.0
            )
            if response.status_code != 200:
                return {"status": "not_ready", "reason": "Consul unavailable"}, 503
        
        return {
            "status": "ready",
            "checks": {
                "database": "ok",
                "consul": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "reason": str(e)}, 503
```

**Priority**: 🟡 **HIGH** - Essential for proper K8s/orchestration integration

**Docker Compose Integration**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/ready"]
  interval: 10s
  timeout: 5s
  start_period: 30s
  retries: 3
```

---

### 3. **Startup Probe** (RECOMMENDED for K8s, optional for Docker)
Specific probe for initialization phase to avoid premature traffic:

```python
@app.get("/startup")
async def startup_check():
    """
    Startup probe: Service is still initializing
    Used by orchestrators to know when to start routing traffic
    """
    # Check if critical initialization complete
    if not app.state.initialized:
        return {"status": "initializing"}, 503
    
    return {"status": "ready_for_traffic"}
```

**Priority**: 🟢 **LOW** - Mainly needed for Kubernetes

---

### 4. **Database-Specific Checks** (RECOMMENDED)

**For book-catalog-service (PostgreSQL)**:
```python
@app.get("/health/db")
async def db_health(db: Session = Depends(get_db)):
    """Check PostgreSQL connectivity and performance"""
    try:
        # Simple connectivity test
        result = db.execute(text("SELECT 1")).scalar()
        if result != 1:
            raise Exception("Database query failed")
        
        # Check connection pool (if using)
        # Example: Ensure we have available connections
        
        return {
            "database": "healthy",
            "type": "postgresql",
            "connection_pool_size": db.engine.pool.size(),
            "checked_size": db.engine.pool.checked_in()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"database": "unhealthy", "error": str(e)}, 503
```

**For book-review-service (MongoDB + Redis)**:
```python
@app.get("/health/db")
async def db_health():
    """Check MongoDB and Redis connectivity"""
    health = {}
    
    try:
        # MongoDB check
        mongo_client.admin.command('ping')
        health["mongodb"] = "healthy"
    except Exception as e:
        health["mongodb"] = f"unhealthy: {str(e)}"
    
    try:
        # Redis check
        redis_client.ping()
        health["redis"] = "healthy"
    except Exception as e:
        health["redis"] = f"unhealthy: {str(e)}"
    
    if any("unhealthy" in v for v in health.values()):
        return health, 503
    
    return health
```

**Priority**: 🟡 **HIGH** - Critical for ops visibility

---

### 5. **Kafka Connectivity Check** (RECOMMENDED for event-publishing services)

**For posts-service and book-review-service**:
```python
@app.get("/health/kafka")
async def kafka_health():
    """Check Kafka producer connectivity"""
    try:
        # Flush pending messages and check status
        kafka_producer.flush(timeout=2)
        
        return {
            "kafka": "healthy",
            "broker": KAFKA_HOST
        }
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        return {"kafka": "unhealthy", "error": str(e)}, 503
```

**Priority**: 🟡 **MEDIUM** - Important for async operations

---

### 6. **Dependency Availability Check** (RECOMMENDED)

```python
@app.get("/health/dependencies")
async def dependencies_health():
    """Check critical external service availability"""
    dependencies = {}
    
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            # Check book-catalog from book-review-service
            response = await client.get("http://book-catalog-service:5000/health")
            dependencies["book-catalog"] = "available" if response.status_code == 200 else "unavailable"
    except Exception as e:
        dependencies["book-catalog"] = f"unreachable: {str(e)}"
    
    # Check other services similarly
    
    if any("unavailable" in v or "unreachable" in v for v in dependencies.values()):
        return dependencies, 503
    
    return dependencies
```

**Priority**: 🟡 **MEDIUM** - Useful for debugging cascading failures

---

### 7. **Metrics Endpoint** (OPTIONAL but RECOMMENDED)
Export Prometheus-style metrics for monitoring:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
request_count = Counter('requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('request_duration_seconds', 'Request duration', ['method', 'endpoint'])

@app.get("/metrics")
async def metrics():
    return generate_latest()
```

**Priority**: 🟢 **LOW** - Enhancement for monitoring/alerting

---

## Implementation Priority Roadmap

### Phase 1: **CRITICAL** (Implement Immediately)
- ✅ Enhanced liveness check with version info
- ✅ Readiness check with dependency verification
- 🔴 Update docker-compose healthcheck to use `/ready` endpoint

### Phase 2: **HIGH** (Next iteration)
- 🔴 Database-specific health checks (`/health/db`)
- 🔴 Update all Dockerfiles to use enhanced checks
- 🔴 Add health checks to Consul service registration

### Phase 3: **MEDIUM** (Future)
- 🔴 Kafka connectivity checks
- 🔴 Dependency availability checks
- 🔴 Prometheus metrics export

---

## Docker Compose Configuration Template

```yaml
services:
  book-catalog-service:
    healthcheck:
      # Use readiness check during normal operation
      test: ["CMD", "curl", "-f", "http://localhost:5000/ready"]
      interval: 10s
      timeout: 5s
      start_period: 30s  # Initial startup grace period
      retries: 3
  
  book-review-service:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/ready"]
      interval: 10s
      timeout: 5s
      start_period: 30s
      retries: 3
    # Alternative: Use external health check script
    # test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/ready')"]
```

---

## Consul Health Check Integration

Update service registration to use enhanced checks:

```python
service_data = {
    "ID": "book-catalog-service",
    "Name": "book-catalog-service",
    "Address": "book-catalog-service",
    "Port": 5000,
    "Check": {
        "HTTP": "http://book-catalog-service:5000/ready",  # Use readiness endpoint
        "Interval": "10s",
        "Timeout": "5s",
        "DeregisterCriticalServiceAfter": "30s"  # Auto-deregister if unhealthy for 30s
    },
    "Tags": ["api", "catalog"]
}
```

---

## Kubernetes Health Check (if applicable)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: book-catalog
spec:
  containers:
  - name: book-catalog-service
    livenessProbe:
      httpGet:
        path: /health
        port: 5000
      initialDelaySeconds: 30
      periodSeconds: 10
    
    readinessProbe:
      httpGet:
        path: /ready
        port: 5000
      initialDelaySeconds: 30
      periodSeconds: 5
    
    startupProbe:
      httpGet:
        path: /startup
        port: 5000
      failureThreshold: 30
      periodSeconds: 10
```

---

## Testing Health Checks

```bash
# Liveness check
curl http://localhost:5000/health

# Readiness check
curl http://localhost:5000/ready

# Database health
curl http://localhost:5000/health/db

# Kafka health
curl http://localhost:5000/health/kafka

# Dependencies
curl http://localhost:5000/health/dependencies

# All in one (verbose)
curl -v http://localhost:5000/ready
```

---

## Summary Table

| Check Type | Current | Recommended | Priority | Impact |
|-----------|---------|------------|----------|--------|
| Liveness | ✅ Basic | 🟡 Enhanced | LOW | Info only |
| Readiness | ❌ Missing | ✅ Add | HIGH | **Critical for orchestration** |
| Startup | ❌ Missing | 🟡 Add | LOW | K8s only |
| Database | ❌ Missing | ✅ Add | HIGH | **Critical for ops** |
| Kafka | ❌ Missing | 🟡 Add | MEDIUM | Event-heavy services |
| Dependencies | ❌ Missing | 🟡 Add | MEDIUM | Debugging |
| Metrics | ❌ Missing | 🟢 Add | LOW | Monitoring enhancement |

---

## Next Steps

1. **Start with Phase 1**: Implement readiness check and database health endpoints
2. **Update Dockerfiles**: Change healthcheck to use `/ready` endpoint
3. **Update docker-compose.yml**: Reference new healthcheck endpoints
4. **Test**: Verify health checks work correctly on deployment
5. **Monitor**: Watch health check metrics in Consul/Prometheus
