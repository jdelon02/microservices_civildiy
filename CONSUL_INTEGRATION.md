# Consul Service Discovery Integration

## ✅ Status: COMPLETE

Both new microservices **automatically register themselves** with Consul on startup.

---

## How It Works

### Registration Flow

```
Service Startup
    ↓
@app.on_event("startup")
    ↓
await register_with_consul()
    ↓
PUT /v1/agent/service/register
    ↓
Consul receives registration
    ↓
Service appears in service registry
    ↓
✅ Ready for discovery
```

---

## Book Catalog Service

### Configuration
```python
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)
```

### Registration Details
```python
service_data = {
    "ID": "book-catalog-service",
    "Name": "book-catalog-service",
    "Address": "book-catalog-service",  # Docker container hostname
    "Port": 5000,
    "Check": {
        "HTTP": "http://book-catalog-service:5000/health",
        "Interval": "10s",
        "Timeout": "5s"
    },
    "Tags": ["api", "catalog", "books"]
}
```

### What This Means
- **ID**: Unique identifier for this service instance
- **Name**: Service name for discovery
- **Address**: How other services can reach it (Docker hostname)
- **Port**: Service port (5000)
- **Check**: Health check endpoint
  - Consul pings `/health` every 10 seconds
  - If unhealthy for too long, service is marked down
- **Tags**: Labels for filtering/grouping services

### Implementation (Lines 143-177)
```python
async def register_with_consul():
    try:
        service_data = { ... }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register",
                json=service_data
            )
            
            if response.status_code == 200:
                logger.info("Successfully registered service with Consul")
            else:
                logger.warning(f"Service registration returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to register with Consul: {e}")

@app.on_event("startup")
async def startup_event():
    await register_with_consul()
```

---

## Book Review Service

### Configuration
```python
CONSUL_HOST = os.getenv("CONSUL_HOST", "consul-server")
CONSUL_PORT = os.getenv("CONSUL_PORT", 8500)
```

### Registration Details
```python
service_data = {
    "ID": "book-review-service",
    "Name": "book-review-service",
    "Address": "book-review-service",  # Docker container hostname
    "Port": 5000,
    "Check": {
        "HTTP": "http://book-review-service:5000/health",
        "Interval": "10s",
        "Timeout": "5s"
    },
    "Tags": ["api", "reviews", "books"]
}
```

### Implementation (Lines 262-312)
Same pattern as Book Catalog Service:
- Registers with Consul on startup
- Health checks every 10 seconds
- Graceful error handling if Consul unavailable

---

## Health Check Endpoints

Both services expose `/health` for Consul:

### Book Catalog Service
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Book Review Service
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## Consul API Endpoints

### List All Services
```bash
curl http://localhost:8500/v1/catalog/services
```

Response:
```json
{
  "auth-service": ["api"],
  "book-catalog-service": ["api", "catalog", "books"],
  "book-review-service": ["api", "reviews", "books"],
  "feed-generator-service": ["api"],
  "posts-service": ["api"],
  "user-profile-service": ["api"]
}
```

### Get Service Details
```bash
curl http://localhost:8500/v1/catalog/service/book-catalog-service
```

Response:
```json
[
  {
    "ID": "book-catalog-service",
    "Node": "consul-1",
    "Address": "book-catalog-service",
    "Port": 5000,
    "Tags": ["api", "catalog", "books"],
    "ServiceID": "book-catalog-service",
    "ServiceName": "book-catalog-service",
    "Checks": [
      {
        "Node": "consul-1",
        "CheckID": "service:book-catalog-service",
        "Name": "Service \"book-catalog-service\" check",
        "Status": "passing",
        "Output": "",
        "ServiceName": "book-catalog-service"
      }
    ]
  }
]
```

### Query Service by Tag
```bash
# Find all "api" services
curl http://localhost:8500/v1/catalog/services?tag=api
```

---

## How Other Services Discover Them

### Via Consul DNS
```bash
# In another container, connect to service via DNS
curl http://book-catalog-service.service.consul:5000/health
```

### Via Consul API
```javascript
// In another service (e.g., frontend)
async function discoverBookCatalogService() {
    const response = await fetch(
        'http://consul:8500/v1/catalog/service/book-catalog-service'
    );
    const services = await response.json();
    return services[0]; // Get first healthy instance
}
```

### Via Traefik (Already Configured)
```yaml
# Traefik automatically discovers services from Consul
# Routes to registered services by name
```

---

## Failure Handling

### If Consul Unavailable
- Registration fails gracefully with warning log
- Service still starts and functions locally
- Will retry registration only on next startup

```python
except Exception as e:
    logger.warning(f"Failed to register with Consul: {e}")
    # Service continues to run
```

### If Service Health Check Fails
- Consul marks service as unhealthy
- Service appears in Consul but with `status: failing`
- Other services should not route to unhealthy instances

### Recovery
- Fix the health check issue
- Service continues to report status every 10 seconds
- Consul automatically marks healthy again

---

## Service Discovery Architecture

```
┌─────────────────────────────────┐
│       Consul Registry           │
├─────────────────────────────────┤
│ • auth-service (port 5000)      │
│ • book-catalog-service (5000)   │ ← NEW
│ • book-review-service (5000)    │ ← NEW
│ • posts-service (5000)          │
│ • user-profile-service (5000)   │
│ • feed-generator-service (5000) │
└─────────────────────────────────┘
         ↑         ↑         ↑
         │         │         │
    [Health checks every 10s]
         │         │         │
    ┌────┴──┐  ┌───┴──┐  ┌───┴──┐
    │Service│  │Service│  │Service│
    │  A    │  │  B    │  │  C   │
    └───────┘  └───────┘  └───────┘
         ↑         ↑         ↑
         └─────────┼─────────┘
              |Discovery via
              |Consul API/DNS
```

---

## Docker Compose Configuration

The services register automatically when deployed. In `docker-compose.yml`:

```yaml
services:
  book-catalog-service:
    build: ./book-catalog-service
    environment:
      - CONSUL_HOST=consul-server
      - CONSUL_PORT=8500
    depends_on:
      - consul-server
    networks:
      - microservices

  book-review-service:
    build: ./book-review-service
    environment:
      - CONSUL_HOST=consul-server
      - CONSUL_PORT=8500
    depends_on:
      - consul-server
    networks:
      - microservices

  consul-server:
    image: consul:latest
    ports:
      - "8500:8500"
    command: agent -server -ui -node=consul-1 -bootstrap-expect=1 -client=0.0.0.0
    networks:
      - microservices
```

---

## Monitoring Service Health

### Via Consul UI
- Visit: `http://localhost:8500/ui/`
- View all registered services
- Check service status (passing/failing)
- See health check details

### Via Command Line
```bash
# Check all services status
curl -s http://localhost:8500/v1/catalog/services | jq

# Check specific service health
curl -s http://localhost:8500/v1/catalog/service/book-catalog-service | jq '.[] | .Checks'

# Get service instance details
curl -s http://localhost:8500/v1/catalog/service/book-review-service | jq '.[] | {Address, Port, Status}'
```

---

## Logs

### Successful Registration
```
INFO:__main__:Successfully registered service with Consul
```

### Failed Registration
```
WARNING:__main__:Failed to register with Consul: Connection refused
```

### Health Checks
```
# Consul pings every 10 seconds:
GET /health
Response: {"status": "healthy"}
```

---

## Integration Points

### Traefik Dynamic Configuration
Traefik reads from Consul and automatically creates routes for registered services:

```
Consul Registry
    ↓
Traefik discovers services
    ↓
Auto-creates routing rules
    ↓
Client → Traefik → Service (discovered via Consul)
```

### Cross-Service Communication
Book Review Service calls Book Catalog Service:

```python
# Discovery options:
# 1. Via DNS (if Consul DNS enabled)
url = "http://book-catalog-service.service.consul:5000/api/books/42"

# 2. Via Container Hostname (Docker DNS)
url = "http://book-catalog-service:5000/api/books/42"  # Uses Docker DNS

# 3. Via Consul API (programmatic discovery)
# Query Consul for service, get address, construct URL
```

---

## Production Considerations

### ✅ Already Implemented
- Automatic registration on startup
- Health checks every 10 seconds
- Graceful error handling
- Configurable via environment variables

### 🔧 To Add (Optional)
- Service deregistration on shutdown
- Custom health check logic (check dependencies)
- Service tags for filtering
- Multiple service instances with load balancing
- Service mesh features (Consul Connect)

### Example: Graceful Deregistration
```python
@app.on_event("shutdown")
async def shutdown_event():
    try:
        async with httpx.AsyncClient() as client:
            await client.put(
                f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/deregister/book-catalog-service"
            )
            logger.info("Deregistered from Consul")
    except Exception as e:
        logger.warning(f"Failed to deregister: {e}")
```

---

## Summary

✅ **Book Catalog Service**
- Self-registers with Consul on startup
- Health checks every 10s
- Tagged as: api, catalog, books
- Reachable via: `book-catalog-service:5000`

✅ **Book Review Service**
- Self-registers with Consul on startup
- Health checks every 10s
- Tagged as: api, reviews, books
- Reachable via: `book-review-service:5000`

✅ **Service Discovery**
- Other services can find them via Consul
- Traefik uses Consul for routing
- Automatic health management
- Graceful error handling

✅ **Ready for Production**
- No additional configuration needed
- Works with existing architecture
- Follows same pattern as other services
